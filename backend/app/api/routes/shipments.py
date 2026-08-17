from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Quote, Shipment, TrackingEvent, Customer, Carrier
from app.schemas.entities import ShipmentCreate, ShipmentOut, TrackingEventCreate, DirectShipmentCreate, QuoteRequest
from app.domains.shipments.import_service import import_shipments
from app.services.rating import RatingEngine

router = APIRouter(prefix="/shipments", tags=["Shipments"])


def _shipment_number():
    return f"VFS-{datetime.utcnow():%y%m%d%H%M%S%f}"


def _quote_number():
    return f"VFQ-{datetime.utcnow():%y%m%d%H%M%S%f}"


def _create_from_quote(db: Session, q: Quote, carrier_id: int, pickup_date=None):
    matches = [o for o in (q.options or []) if int(o.get("carrier_id", 0)) == carrier_id]
    if not matches:
        raise HTTPException(status_code=400, detail="Carrier option not found on quote")
    opt = matches[0]
    s = Shipment(
        shipment_number=_shipment_number(),
        customer_id=q.customer_id,
        carrier_id=carrier_id,
        quote_id=q.id,
        origin=q.origin,
        destination=q.destination,
        handling_units=q.handling_units,
        accessorials=q.accessorials,
        carrier_cost=Decimal(str(opt["carrier_cost"])),
        customer_charge=Decimal(str(opt["customer_price"])),
        pickup_date=pickup_date,
        estimated_delivery=(pickup_date + timedelta(days=int(opt["transit_days"]))) if pickup_date else None,
    )
    db.add(s)
    q.status = "booked"
    db.commit()
    db.refresh(s)
    return s


@router.get("", response_model=list[ShipmentOut])
def list_shipments(db: Session = Depends(get_db)):
    return db.query(Shipment).order_by(Shipment.created_at.desc()).all()


@router.post("", response_model=ShipmentOut)
def book(payload: ShipmentCreate, db: Session = Depends(get_db)):
    q = db.query(Quote).filter(Quote.quote_number == payload.quote_number).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return _create_from_quote(db, q, payload.carrier_id, payload.pickup_date)


@router.post("/direct", response_model=ShipmentOut)
def direct_shipment(payload: DirectShipmentCreate, db: Session = Depends(get_db)):
    request = QuoteRequest(
        customer_id=payload.customer_id,
        origin=payload.origin,
        destination=payload.destination,
        handling_units=payload.handling_units,
        accessorials=payload.accessorials,
    )
    try:
        options = RatingEngine(db).get_rates(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    selected = next((o for o in options if o.carrier_id == payload.carrier_id), None)
    if not selected:
        raise HTTPException(status_code=400, detail="Selected carrier is not available for this shipment")
    selected_options=[]
    for option in options:
        data=option.model_dump(mode="json")
        data["selected"] = option.carrier_id == payload.carrier_id
        if data["selected"]:
            data["selected_at"] = datetime.utcnow().isoformat()
        selected_options.append(data)
    q = Quote(
        quote_number=_quote_number(),
        customer_id=payload.customer_id,
        status="selected",
        origin=payload.origin.model_dump(),
        destination=payload.destination.model_dump(),
        handling_units=[u.model_dump() for u in payload.handling_units],
        accessorials=payload.accessorials,
        options=selected_options,
        expires_at=datetime.utcnow()+timedelta(hours=24),
    )
    db.add(q)
    db.flush()
    return _create_from_quote(db, q, payload.carrier_id, payload.pickup_date)


@router.post("/import")
async def import_freight(file: UploadFile = File(...), db: Session = Depends(get_db)):
    content = await file.read()
    try:
        return import_shipments(db, file.filename or "freight.csv", content)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/{shipment_id}")
def shipment_detail(shipment_id: int, db: Session = Depends(get_db)):
    s = db.query(Shipment).filter(Shipment.id == shipment_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Shipment not found")
    customer = db.query(Customer).filter(Customer.id == s.customer_id).first()
    carrier = db.query(Carrier).filter(Carrier.id == s.carrier_id).first() if s.carrier_id else None
    events = db.query(TrackingEvent).filter(TrackingEvent.shipment_id == shipment_id).order_by(TrackingEvent.event_time.desc()).all()
    return {
        "id":s.id,"shipment_number":s.shipment_number,"status":s.status,"pro_number":s.pro_number,"bol_number":s.bol_number,
        "customer_id":s.customer_id,"customer_name":customer.name if customer else None,
        "carrier_id":s.carrier_id,"carrier_name":carrier.name if carrier else None,"carrier_scac":carrier.scac if carrier else None,
        "origin":s.origin,"destination":s.destination,"handling_units":s.handling_units,"accessorials":s.accessorials,
        "carrier_cost":s.carrier_cost,"final_carrier_cost":s.final_carrier_cost,"customer_charge":s.customer_charge,
        "pickup_date":s.pickup_date,"estimated_delivery":s.estimated_delivery,"delivered_at":s.delivered_at,"created_at":s.created_at,
        "tracking_events":[{"id":e.id,"code":e.code,"status":e.status,"description":e.description,"location":e.location,"event_time":e.event_time,"source":e.source} for e in events]
    }


@router.get("/{shipment_id}/tracking")
def tracking(shipment_id: int, db: Session = Depends(get_db)):
    return db.query(TrackingEvent).filter(TrackingEvent.shipment_id==shipment_id).order_by(TrackingEvent.event_time.desc()).all()


@router.post("/{shipment_id}/tracking")
def add_tracking(shipment_id: int, payload: TrackingEventCreate, db: Session = Depends(get_db)):
    if not db.get(Shipment, shipment_id):
        raise HTTPException(status_code=404, detail="Shipment not found")
    e=TrackingEvent(shipment_id=shipment_id, **payload.model_dump())
    db.add(e)
    db.commit()
    db.refresh(e)
    return e
