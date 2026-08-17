from decimal import Decimal
from uuid import uuid4
from sqlalchemy import func
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models import Customer, Shipment
from app.domains.customers.models import CustomerProfile, CustomerLocation, CustomerContact, CustomerActivity
from app.domains.customers.schemas import CustomerCreate, CustomerUpdate, LocationCreate, ContactCreate, ActivityCreate

ACTIVE_SHIPMENT_STATUSES = ["booked", "pickup_requested", "dispatched", "in_transit", "out_for_delivery"]


def _customer_or_404(db: Session, customer_id: int) -> Customer:
    item = db.query(Customer).filter(Customer.id == customer_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Customer not found")
    return item


def _summary(db: Session, customer: Customer) -> dict:
    shipment_count = db.query(func.count(Shipment.id)).filter(Shipment.customer_id == customer.id).scalar() or 0
    active_shipments = db.query(func.count(Shipment.id)).filter(Shipment.customer_id == customer.id, Shipment.status.in_(ACTIVE_SHIPMENT_STATUSES)).scalar() or 0
    revenue = db.query(func.coalesce(func.sum(Shipment.customer_charge), 0)).filter(Shipment.customer_id == customer.id).scalar() or Decimal("0")
    return {
        "id": customer.id,
        "code": customer.code,
        "name": customer.name,
        "status": customer.status,
        "industry": customer.industry,
        "billing_email": customer.billing_email,
        "default_markup_pct": customer.default_markup_pct,
        "credit_limit": customer.credit_limit,
        "location_count": db.query(func.count(CustomerLocation.id)).filter(CustomerLocation.customer_id == customer.id, CustomerLocation.active.is_(True)).scalar() or 0,
        "contact_count": db.query(func.count(CustomerContact.id)).filter(CustomerContact.customer_id == customer.id, CustomerContact.active.is_(True)).scalar() or 0,
        "shipment_count": shipment_count,
        "active_shipment_count": active_shipments,
        "revenue_total": revenue,
    }


def list_customers(db: Session) -> list[dict]:
    return [_summary(db, c) for c in db.query(Customer).order_by(Customer.name).all()]


def create_customer(db: Session, payload: CustomerCreate) -> dict:
    # Use a temporary unique value to obtain the database ID, then replace it with
    # a stable system-owned code. This keeps customer code generation out of the UI.
    supplied_code = payload.code.strip().upper() if payload.code else None
    if supplied_code and db.query(Customer).filter(Customer.code == supplied_code).first():
        raise HTTPException(status_code=409, detail="Customer code already exists")
    base = payload.model_dump(exclude={"profile", "code"})
    item = Customer(code=supplied_code or f"PENDING-{uuid4().hex[:12].upper()}", **base)
    db.add(item)
    db.flush()
    if not supplied_code:
        item.code = f"VFC-{item.id:06d}"
    if payload.profile:
        db.add(CustomerProfile(customer_id=item.id, **payload.profile.model_dump()))
    else:
        db.add(CustomerProfile(customer_id=item.id))
    db.commit()
    db.refresh(item)
    return _summary(db, item)


def update_customer(db: Session, customer_id: int, payload: CustomerUpdate) -> dict:
    item = _customer_or_404(db, customer_id)
    data = payload.model_dump(exclude_unset=True)
    profile_data = data.pop("profile", None)
    for field, value in data.items():
        setattr(item, field, value)
    if profile_data is not None:
        profile = db.query(CustomerProfile).filter(CustomerProfile.customer_id == customer_id).first()
        if not profile:
            profile = CustomerProfile(customer_id=customer_id)
            db.add(profile)
        for field, value in profile_data.items():
            setattr(profile, field, value)
    db.commit()
    db.refresh(item)
    return _summary(db, item)


def get_customer_360(db: Session, customer_id: int) -> dict:
    item = _customer_or_404(db, customer_id)
    shipments = db.query(Shipment).filter(Shipment.customer_id == customer_id).order_by(Shipment.created_at.desc()).limit(12).all()
    return {
        "customer": _summary(db, item),
        "profile": db.query(CustomerProfile).filter(CustomerProfile.customer_id == customer_id).first(),
        "locations": db.query(CustomerLocation).filter(CustomerLocation.customer_id == customer_id, CustomerLocation.active.is_(True)).order_by(CustomerLocation.name).all(),
        "contacts": db.query(CustomerContact).filter(CustomerContact.customer_id == customer_id, CustomerContact.active.is_(True)).order_by(CustomerContact.primary.desc(), CustomerContact.last_name).all(),
        "activities": db.query(CustomerActivity).filter(CustomerActivity.customer_id == customer_id).order_by(CustomerActivity.created_at.desc()).limit(30).all(),
        "shipments": [{
            "id": s.id,
            "shipment_number": s.shipment_number,
            "status": s.status,
            "origin": s.origin,
            "destination": s.destination,
            "carrier_id": s.carrier_id,
            "customer_charge": s.customer_charge,
            "pickup_date": s.pickup_date.isoformat() if s.pickup_date else None,
        } for s in shipments],
    }


def add_location(db: Session, customer_id: int, payload: LocationCreate):
    _customer_or_404(db, customer_id)
    item = CustomerLocation(customer_id=customer_id, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item); return item


def add_contact(db: Session, customer_id: int, payload: ContactCreate):
    _customer_or_404(db, customer_id)
    if payload.primary:
        db.query(CustomerContact).filter(CustomerContact.customer_id == customer_id).update({"primary": False})
    item = CustomerContact(customer_id=customer_id, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item); return item


def add_activity(db: Session, customer_id: int, payload: ActivityCreate, user_name: str | None):
    _customer_or_404(db, customer_id)
    item = CustomerActivity(customer_id=customer_id, created_by=user_name, **payload.model_dump())
    db.add(item); db.commit(); db.refresh(item); return item
