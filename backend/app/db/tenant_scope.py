"""Company scoping covers reads, aggregates, direct lookups and ORM writes.

Both database dependencies attach the same request. Super Admin and
startup migrations/seeding retain platform access.
"""
from fastapi import HTTPException
from sqlalchemy import event, select, or_
from sqlalchemy.orm import Session, with_loader_criteria
from app.db.base import Base
from app.core.roles import BROKER_ROLES, COMPANY_ROLES
from app.models import BrokerCustomerAssignment, Carrier, CapacityLoad, CapacityOffer, CarrierRateControl, Customer, Shipment, Quote, PricingRule, IntegrationConnection, IntegrationCredential, AuditEvent


def tenant(session):
    # Set only by the authenticated Muse partner dependency, within /muse routes.
    # Normal broker operational requests retain their original company scope.
    if session.info.get('muse_partner_request'):return None
    request = session.info.get('request')
    user = getattr(request.state, 'auth_user', None) if request else None
    support_company=getattr(request.state,'support_company_id',None) if request else None
    if user and user.role=='admin' and support_company is not None:return support_company
    if user and user.role in COMPANY_ROLES:
        if not user.customer_id:
            raise HTTPException(403, 'Account must be linked to a company')
        return user.customer_id
    return None


def integration_company(session):
    company = tenant(session)
    if company is not None: return company
    request=session.info.get('request')
    return getattr(request.state, 'integration_company_id', None) if request else None


def owned_ids(company, broker=False):
    customers=Customer.__table__.c
    rule=or_(customers.id==company,customers.manufacturer_id==company)
    if broker:
        assignments=BrokerCustomerAssignment.__table__.c
        linked=select(assignments.customer_id).where(assignments.broker_company_id==company)
        rule=or_(rule,customers.id.in_(linked),customers.manufacturer_id.in_(linked))
    return select(customers.id).where(rule)


def owns(session,customer_id,company):
    if customer_id==company:return True
    row=session.get(Customer,customer_id) if customer_id is not None else None
    if row is None:return False
    if row.manufacturer_id==company:return True
    if broker_workspace(session):
        a=BrokerCustomerAssignment.__table__.c
        return session.execute(select(a.customer_id).where(a.broker_company_id==company,a.customer_id.in_([row.id,row.manufacturer_id]))).first() is not None
    return False


def broker_workspace(session):
    request = session.info.get('request')
    user = getattr(request.state, 'auth_user', None) if request else None
    return bool(user and user.role in BROKER_ROLES)


def safe_partner_owns(session,obj):
    from app.models import SafeLoadCase,SafeLoadEvent,TrackingEvent,SafeLoadBrokerContact,SafeLoadPhotoAttempt,SafeLoadCustodySnapshot,SafeLoadPhotoExtraction,SafeLoadBackPhoto,SafeLoadReleaseReceipt,MuseBooking
    if not session.info.get('safe_load_partner_request') or not isinstance(obj,(Shipment,SafeLoadCase,SafeLoadEvent,TrackingEvent,SafeLoadBrokerContact,SafeLoadPhotoAttempt,SafeLoadCustodySnapshot,SafeLoadPhotoExtraction,SafeLoadBackPhoto,SafeLoadReleaseReceipt)):return False
    if isinstance(obj,(SafeLoadPhotoExtraction,SafeLoadBackPhoto)):
        from app.models import SafeLoadPhotoAttempt
        a=SafeLoadPhotoAttempt.__table__.c
        sid=session.execute(select(a.shipment_id).where(a.id==obj.attempt_id)).scalar()
    else:sid=obj.id if isinstance(obj,Shipment) else obj.shipment_id
    if not sid:return False
    return session.execute(select(MuseBooking.__table__.c.shipment_id).where(MuseBooking.__table__.c.shipment_id==sid)).first() is not None


def criterion(cls, company, broker=False, safe_partner=False):
    if cls is BrokerCustomerAssignment:return cls.broker_company_id==company if broker else cls.customer_id<0
    if safe_partner:
        from app.models import SafeLoadCase,SafeLoadEvent,TrackingEvent,SafeLoadBrokerContact,SafeLoadPhotoAttempt,SafeLoadCustodySnapshot,SafeLoadPhotoExtraction,SafeLoadBackPhoto,SafeLoadReleaseReceipt,MuseBooking
        if cls in (SafeLoadPhotoExtraction,SafeLoadBackPhoto):
            from app.models import SafeLoadPhotoAttempt
            a=SafeLoadPhotoAttempt.__table__.c;m=MuseBooking.__table__.c
            return or_(cls.customer_id.in_(owned_ids(company,broker)),cls.attempt_id.in_(select(a.id).where(a.shipment_id.in_(select(m.shipment_id)))))
        if cls in (Shipment,SafeLoadCase,SafeLoadEvent,TrackingEvent,SafeLoadBrokerContact,SafeLoadPhotoAttempt,SafeLoadCustodySnapshot,SafeLoadReleaseReceipt):
            column=cls.id if cls is Shipment else cls.shipment_id
            related=column.in_(select(MuseBooking.__table__.c.shipment_id))
            own=cls.customer_id.in_(owned_ids(company, broker)) if hasattr(cls,'customer_id') else cls.shipment_id.in_(select(Shipment.id).where(Shipment.customer_id.in_(owned_ids(company, broker))))
            return or_(own,related)

    if cls is Carrier:
        return or_(cls.customer_id.is_(None), cls.customer_id.in_(owned_ids(company, True))) if broker else or_(cls.customer_id.is_(None), cls.customer_id==company)
    if cls is CapacityLoad:
        return or_(cls.customer_id.in_(owned_ids(company, broker)),
                   cls.customer_id.is_(None) & cls.shipment_id.in_(select(Shipment.id).where(Shipment.customer_id.in_(owned_ids(company, broker)))))
    if cls is CapacityOffer:
        return cls.load_id.in_(select(CapacityLoad.id))
    if cls.__tablename__.startswith('carrier_') and hasattr(cls, 'carrier_id') and not hasattr(cls, 'shipment_id'):
        owner = Carrier.customer_id.in_(owned_ids(company, True)) if broker and cls is CarrierRateControl else Carrier.customer_id==company
        # Shared rate controls still apply to rating, but shared commercial records
        # and documents aren't part of a broker company's private carrier workspace.
        if not broker or cls is CarrierRateControl:
            owner = or_(owner, Carrier.customer_id.is_(None))
        return cls.carrier_id.in_(select(Carrier.id).where(owner))
    if cls is IntegrationConnection:return cls.customer_id==company
    if cls is IntegrationCredential:
        return cls.integration_id.in_(select(IntegrationConnection.id).where(IntegrationConnection.customer_id == company))
    if cls is AuditEvent:
        return cls.id < 0  # Internal audit details are visible only to Valhalla administrators.
    if cls is Customer:
        return cls.id.in_(owned_ids(company, broker))
    if hasattr(cls, 'customer_id') and cls.__tablename__ != 'users':
        if cls is PricingRule:
            return cls.customer_id.in_(owned_ids(company, broker)) if broker else or_(cls.customer_id.in_(owned_ids(company, broker)), cls.customer_id.is_(None))
        return cls.customer_id.in_(owned_ids(company, broker))
    if hasattr(cls, 'shipment_id'):
        return cls.shipment_id.in_(select(Shipment.id).where(Shipment.customer_id.in_(owned_ids(company, broker))))
    return None


@event.listens_for(Session, 'do_orm_execute')
def scope_reads(state):
    company = tenant(state.session)
    integration_scope = integration_company(state.session)
    if company is None:
        if state.is_select and integration_scope is not None:
            for cls in (IntegrationConnection, IntegrationCredential):
                state.statement = state.statement.options(with_loader_criteria(cls, criterion(cls, integration_scope), include_aliases=True))
        return
    if state.is_update or state.is_delete:
        raise HTTPException(403, 'Bulk changes are unavailable for company accounts')
    if state.is_select:
        broker = broker_workspace(state.session)
        for mapper in Base.registry.mappers:
            rule = criterion(mapper.class_, company, broker, bool(state.session.info.get('safe_load_partner_request')))
            if rule is not None:
                state.statement = state.statement.options(with_loader_criteria(mapper.class_, rule, include_aliases=True))


@event.listens_for(Session, 'before_flush')
def scope_writes(session, context, instances):
    company = tenant(session)
    integration_scope = integration_company(session)
    for obj in session.new | session.dirty | session.deleted:
        if isinstance(obj, IntegrationConnection) and integration_scope is not None:
            if obj in session.new: obj.customer_id = integration_scope
            if obj.customer_id != integration_scope: raise HTTPException(403, 'Integration belongs to another company')
        if isinstance(obj, IntegrationCredential) and integration_scope is not None:
            parent=session.get(IntegrationConnection, obj.integration_id)
            if parent is None or parent.customer_id != integration_scope: raise HTTPException(403, 'Integration access denied')
        if company is None: continue
        if isinstance(obj,BrokerCustomerAssignment):raise HTTPException(403,'Only Valhalla Freight Admin can assign broker customers')
        if safe_partner_owns(session,obj):continue
        from app.models import OperationalNotification
        if isinstance(obj,OperationalNotification) and obj.notification_type=='safe_load':
            if obj.customer_id in session.info.get('safe_load_notice_targets',set()):continue
            from sqlalchemy import inspect
            changed={a.key for a in inspect(obj).attrs if a.history.has_changes()}
            if obj not in session.new and owns(session,obj.customer_id,company) and changed<={'status','read_at'}:continue
        if isinstance(obj, (IntegrationConnection, IntegrationCredential)): continue
        if isinstance(obj, Carrier):
            if obj.customer_id != company:
                raise HTTPException(403, 'Carrier belongs to another workspace')
        elif isinstance(obj, CapacityOffer):
            if session.get(CapacityLoad, obj.load_id) is None:
                raise HTTPException(403, 'Capacity load belongs to another workspace')
        elif isinstance(obj, CapacityLoad):
            if not owns(session,obj.customer_id,company) and not (obj.customer_id is None and obj.shipment_id is not None):
                raise HTTPException(403, 'Capacity load belongs to another workspace')
        elif isinstance(obj, PricingRule):
            if obj in session.new and obj.customer_id is None:
                obj.customer_id = company
            if not owns(session,obj.customer_id,company):
                raise HTTPException(403, 'Global pricing rules are managed by your broker')
        elif isinstance(obj, Customer):
            from sqlalchemy import inspect
            changed={a.key for a in inspect(obj).attrs if a.history.has_changes()}
            if obj in session.new:
                if obj.manufacturer_id!=company:raise HTTPException(403,'New customers must belong to your company')
            elif obj.manufacturer_id==company or (broker_workspace(session) and obj.id!=company and owns(session,obj.id,company)):
                if 'manufacturer_id' in changed:raise HTTPException(403,'Customer ownership cannot be reassigned here')
            else:raise HTTPException(403,'Parent company records are managed by Valhalla Freight')
        elif hasattr(obj, 'customer_id') and obj.__tablename__ != 'users':
            if not owns(session,obj.customer_id,company):raise HTTPException(403,'Company access denied')
        carrier_id = getattr(obj, 'carrier_id', None)
        if carrier_id is not None:
            carrier = session.get(Carrier, carrier_id)
            allowed_carrier=carrier is not None and (carrier.customer_id in (None,company) or (broker_workspace(session) and owns(session,carrier.customer_id,company)))
            # A manufacturer may release its existing broker-booked shipment;
            # this grants no access to the broker's private carrier directory.
            if not allowed_carrier and isinstance(obj,Shipment) and obj not in session.new:
                from sqlalchemy import inspect
                if not inspect(obj).attrs.carrier_id.history.has_changes() and owns(session,obj.customer_id,company):
                    carriers=Carrier.__table__.c
                    allowed_carrier=session.execute(select(carriers.id).where(carriers.id==carrier_id)).first() is not None
            if not allowed_carrier:raise HTTPException(403, 'Carrier belongs to another workspace')
            if broker_workspace(session) and obj.__tablename__.startswith('carrier_') and not hasattr(obj, 'shipment_id') and carrier.customer_id != company:
                raise HTTPException(403, 'Shared carriers are managed by Valhalla Freight')
        for field, model in [('shipment_id', Shipment), ('quote_id', Quote)]:
            ref = getattr(obj, field, None)
            if ref is not None:
                target = session.get(model, ref)
                if target is None or not owns(session,target.customer_id,company):
                    raise HTTPException(403, 'Related record belongs to another company')
