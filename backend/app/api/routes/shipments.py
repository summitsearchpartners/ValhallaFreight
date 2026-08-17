from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Quote, Shipment, TrackingEvent
from app.schemas.entities import ShipmentCreate, ShipmentOut, TrackingEventCreate
router = APIRouter(prefix="/shipments", tags=["Shipments"])
@router.get("", response_model=list[ShipmentOut])
def list_shipments(db: Session = Depends(get_db)): return db.query(Shipment).order_by(Shipment.created_at.desc()).all()
@router.post("", response_model=ShipmentOut)
def book(payload: ShipmentCreate, db: Session = Depends(get_db)):
    q = db.query(Quote).filter(Quote.quote_number == payload.quote_number).first()
    if not q: raise HTTPException(404,"Quote not found")
    matches = [o for o in q.options if int(o["carrier_id"]) == payload.carrier_id]
    if not matches: raise HTTPException(400,"Carrier option not found on quote")
    opt = matches[min(payload.option_index, len(matches)-1)]
    number = f"FFS-{datetime.utcnow():%y%m%d%H%M%S%f}"[-22:]
    s = Shipment(shipment_number=number, customer_id=q.customer_id, carrier_id=payload.carrier_id, quote_id=q.id,
                 origin=q.origin, destination=q.destination, handling_units=q.handling_units, accessorials=q.accessorials,
                 carrier_cost=Decimal(str(opt["carrier_cost"])), customer_charge=Decimal(str(opt["customer_price"])),
                 pickup_date=payload.pickup_date, estimated_delivery=(payload.pickup_date + timedelta(days=int(opt["transit_days"]))) if payload.pickup_date else None)
    db.add(s); q.status="booked"; db.commit(); db.refresh(s); return s
@router.get("/{shipment_id}/tracking")
def tracking(shipment_id: int, db: Session = Depends(get_db)):
    return db.query(TrackingEvent).filter(TrackingEvent.shipment_id==shipment_id).order_by(TrackingEvent.event_time.desc()).all()
@router.post("/{shipment_id}/tracking")
def add_tracking(shipment_id: int, payload: TrackingEventCreate, db: Session = Depends(get_db)):
    if not db.get(Shipment, shipment_id): raise HTTPException(404,"Shipment not found")
    e=TrackingEvent(shipment_id=shipment_id, **payload.model_dump()); db.add(e); db.commit(); db.refresh(e); return e
