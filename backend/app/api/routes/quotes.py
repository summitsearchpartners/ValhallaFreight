from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Quote, Customer, Shipment
from app.schemas.entities import QuoteRequest, QuoteResponse
from app.services.rating import RatingEngine

router = APIRouter(prefix="/quotes", tags=["Quotes"])


def _quote_number():
    return f"VFQ-{datetime.utcnow():%y%m%d%H%M%S%f}"


def _serialize_quote(q: Quote, db: Session):
    customer = db.get(Customer, q.customer_id)
    selected = next((o for o in (q.options or []) if o.get("selected")), None)
    shipment = db.query(Shipment).filter(Shipment.quote_id == q.id).order_by(Shipment.created_at.desc()).first()
    return {
        "id": q.id,
        "quote_number": q.quote_number,
        "customer_id": q.customer_id,
        "customer_name": customer.name if customer else None,
        "status": q.status,
        "origin": q.origin,
        "destination": q.destination,
        "handling_units": q.handling_units or [],
        "accessorials": q.accessorials or [],
        "options": q.options or [],
        "selected_option": selected,
        "created_at": q.created_at,
        "expires_at": q.expires_at,
        "requested_pickup_at": q.requested_pickup_at,
        "requested_delivery_at": q.requested_delivery_at,
        "shipment_id": shipment.id if shipment else None,
        "shipment_number": shipment.shipment_number if shipment else None,
    }


def _find_quote(ref: str, db: Session):
    q = None
    if ref.isdigit():
        q = db.get(Quote, int(ref))
    if not q:
        q = db.query(Quote).filter(Quote.quote_number == ref).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    return q


class QuoteSelect(BaseModel):
    carrier_id: int


@router.post("/rate", response_model=QuoteResponse)
def rate(payload: QuoteRequest, db: Session = Depends(get_db)):
    try:
        options = RatingEngine(db).get_rates(payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    number = _quote_number()
    expires = datetime.utcnow() + timedelta(hours=24)
    q = Quote(
        quote_number=number,
        customer_id=payload.customer_id,
        origin=payload.origin.model_dump(),
        destination=payload.destination.model_dump(),
        handling_units=[u.model_dump() for u in payload.handling_units],
        accessorials=payload.accessorials,
        options=[o.model_dump(mode="json") for o in options],
        expires_at=expires,
        requested_pickup_at=payload.requested_pickup_at,
        requested_delivery_at=payload.requested_delivery_at,
    )
    db.add(q)
    db.commit()
    return QuoteResponse(quote_number=number, options=options, expires_at=expires)


@router.get("")
def list_quotes(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Quote).order_by(Quote.created_at.desc())
    if status:
        query = query.filter(Quote.status == status)
    return [_serialize_quote(q, db) for q in query.limit(250).all()]


@router.get("/{quote_ref}")
def quote_detail(quote_ref: str, db: Session = Depends(get_db)):
    return _serialize_quote(_find_quote(quote_ref, db), db)


@router.post("/{quote_ref}/select")
def select_rate(quote_ref: str, payload: QuoteSelect, db: Session = Depends(get_db)):
    q = _find_quote(quote_ref, db)
    if q.status == "booked":
        raise HTTPException(status_code=400, detail="This quote has already been converted to a shipment")
    found = False
    selected_at = datetime.utcnow().isoformat()
    next_options = []
    for option in q.options or []:
        copy = dict(option)
        is_selected = int(copy.get("carrier_id", 0)) == payload.carrier_id
        copy["selected"] = is_selected
        if is_selected:
            copy["selected_at"] = selected_at
            found = True
        else:
            copy.pop("selected_at", None)
        next_options.append(copy)
    if not found:
        raise HTTPException(status_code=400, detail="Carrier option not found on quote")
    q.options = next_options
    q.status = "selected"
    db.commit()
    db.refresh(q)
    return _serialize_quote(q, db)
