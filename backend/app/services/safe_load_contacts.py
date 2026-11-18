"""Resolve a shipment's broker call contact from shared profile settings."""
from sqlalchemy import select
from app.models import Customer,User,SafeLoadCallProfile,SafeLoadBrokerContact,BrokerCustomerAssignment,MuseBooking,MusePartnerCompany

def responsible_company(db,row):
    c=Customer.__table__.c;u=User.__table__.c;a=BrokerCustomerAssignment.__table__.c
    parent=db.execute(select(c.manufacturer_id).where(c.id==row.customer_id)).scalar()
    root=parent or row.customer_id
    # A real Muse booking belongs to the designated Muse partner; a generic opt-in does not.
    muse=db.execute(select(MuseBooking.__table__.c.shipment_id).where(MuseBooking.__table__.c.shipment_id==row.shipment_id)).first()
    if muse:
        partner=db.execute(select(MusePartnerCompany.__table__.c.company_id).where(MusePartnerCompany.__table__.c.id==1)).scalar()
        if partner:return partner
    linked=db.execute(select(a.broker_company_id).where(a.customer_id.in_([row.customer_id,root]))).first()
    if linked:return linked[0]
    # Broker-created children and the company's own broker/manufacturer workspace retain their owner.
    if db.execute(select(u.id).where(u.customer_id==root,u.role.in_(['broker','broker_admin']))).first():return root
    # Super Admin may explicitly configure a contact for an otherwise independent company.
    p=SafeLoadCallProfile.__table__.c
    if db.execute(select(p.scope_key).where(p.customer_id==root)).first():return root
    return None

def contact_for(db,row):
    p=SafeLoadCallProfile.__table__.c
    company=responsible_company(db,row)
    profile=db.execute(select(p).where(p.scope_key==f'company:{company}')).mappings().first() if company else None
    if profile is not None:
        return {'name':profile['contact_name'],'phone':profile['phone'],'source':'broker_profile','company_id':company} if profile['phone'] and profile['contact_name'] else None
    legacy=db.get(SafeLoadBrokerContact,row.shipment_id)
    if legacy:return {'name':legacy.broker_name,'phone':legacy.phone,'source':'legacy_shipment','company_id':company}
    platform=db.execute(select(p).where(p.scope_key=='platform')).mappings().first()
    return {'name':platform['contact_name'],'phone':platform['phone'],'source':'platform_profile','company_id':None} if platform and platform['phone'] and platform['contact_name'] else None
