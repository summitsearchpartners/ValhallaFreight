from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Quote, Customer, Shipment, CustomerContact
from app.schemas.entities import QuoteRequest, QuoteResponse
from app.services.rating import RatingEngine
from app.services.email import queue_email
from app.api.permissions import require_muse_admin
from app.schemas.muse import MusePreview, MusePreviewSelection, MuseRateInput, MuseRateSelect
from app.services import muse

router = APIRouter(prefix="/quotes", tags=["Quotes"])


def _quote_number():
    return f"VFQ-{datetime.utcnow():%y%m%d%H%M%S%f}"


def _serialize_quote(q: Quote, db: Session, *, include_preview: bool = False):
    customer = db.get(Customer, q.customer_id)
    options=q.options or []
    if q.status!="booked":
        from app.services.muse_enrollment import enrollment
        _,enrolled=enrollment(db,q.customer_id)
        if not enrolled or not enrolled.enabled:options=[o for o in options if o.get("provider")!="muse_freight"]
    selected = next((o for o in options if o.get("selected")), None)
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
        "options": options,
        **({"muse_preview": muse.available_preview(q, db)} if include_preview else {}),
        "selected_option": selected,
        "created_at": q.created_at,
        "expires_at": q.expires_at,
        "requested_pickup_at": q.requested_pickup_at,
        "requested_delivery_at": q.requested_delivery_at,
        "payment_terms": q.payment_terms or "Prepaid",
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
async def rate(payload: QuoteRequest, db: Session = Depends(get_db)):
    from app.services.commercial_privacy import protect_pricing_request
    protect_pricing_request(db,payload)
    try:
        options = await RatingEngine(db).get_rates(payload)
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
        payment_terms=payload.payment_terms,
    )
    db.add(q)
    db.commit()
    return QuoteResponse(quote_number=number, options=options, expires_at=expires, muse_preview=muse.available_preview(q, db))


@router.get("")
def list_quotes(status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Quote).order_by(Quote.created_at.desc())
    if status:
        query = query.filter(Quote.status == status)
    return [_serialize_quote(q, db) for q in query.limit(250).all()]


@router.get("/{quote_ref}")
def quote_detail(quote_ref: str, db: Session = Depends(get_db)):
    return _serialize_quote(_find_quote(quote_ref, db), db, include_preview=True)


@router.get("/{quote_ref}/muse-rate", response_model=MusePreview | None)
def get_muse_rate(quote_ref: str, db: Session = Depends(get_db)):
    return muse.available_preview(_find_quote(quote_ref, db), db)


@router.put("/{quote_ref}/muse-rate", response_model=MusePreview, dependencies=[Depends(require_muse_admin)])
def put_muse_rate(quote_ref: str, payload: MuseRateInput, db: Session = Depends(get_db)):
    return muse.save_rate(db, _find_quote(quote_ref, db).id, payload)


@router.delete("/{quote_ref}/muse-rate", response_model=MusePreview, dependencies=[Depends(require_muse_admin)])
def remove_muse_rate(quote_ref: str, db: Session = Depends(get_db)):
    return muse.save_rate(db, _find_quote(quote_ref, db).id, None)


@router.post("/{quote_ref}/muse-rate/select", response_model=MusePreviewSelection)
def select_muse_rate(quote_ref: str, payload: MuseRateSelect, db: Session = Depends(get_db)):
    return muse.select_rate(db, _find_quote(quote_ref, db).id, str(payload.revision))


class QuoteEmailRequest(BaseModel):
    to_email: str | None = None


def _quote_email_body(q: Quote, customer: Customer, selected: dict) -> str:
    units=q.handling_units or []
    freight_lines=[]
    for u in units:
        freight_lines.append(f"{u.get('quantity',1)} {u.get('type','Pallet')} · {u.get('weight_lbs',0)} lb · Class {u.get('freight_class','—')} · {u.get('length_in','—')} x {u.get('width_in','—')} x {u.get('height_in','—')} in")
    accessorials=', '.join(str(x).replace('_',' ').title() for x in (q.accessorials or [])) or 'None'
    pickup=q.requested_pickup_at.strftime('%m/%d/%Y') if q.requested_pickup_at else 'Not specified'
    return f"""Valhalla TMS Quote

Quote: {q.quote_number}
Customer: {customer.name}
Lane: {q.origin.get('postal_code','—')} → {q.destination.get('postal_code','—')}
Requested pickup: {pickup}
Freight payment terms: {q.payment_terms or 'Prepaid'}

Carrier: {selected.get('carrier_name','—')}{' · Muse Rate' if selected.get('provider')=='muse_freight' else ''}
Service: {selected.get('service','Standard LTL')}
Transit: {selected.get('transit_days','—')} business day(s)
Quoted price: ${float(selected.get('customer_price') or 0):,.2f}

Freight:
{chr(10).join(freight_lines) if freight_lines else 'Not specified'}

Special services / accessorials: {accessorials}

This quote reflects the customer-facing transportation price only. Carrier buy cost, internal markup, and gross-profit information are not included.

Valhalla TMS
Built for the long haul.
"""


@router.post("/{quote_ref}/email")
def email_quote(quote_ref: str, payload: QuoteEmailRequest, db: Session = Depends(get_db)):
    q=_find_quote(quote_ref,db)
    customer=db.get(Customer,q.customer_id)
    if not customer:
        raise HTTPException(status_code=404,detail='Customer not found')
    selected=next((o for o in (q.options or []) if o.get('selected')),None)
    if not selected:
        raise HTTPException(status_code=400,detail='Select a carrier rate before emailing the quote')
    if selected.get('provider')=='muse_freight':
        from app.services.muse_enrollment import require_enabled
        require_enabled(db,q.customer_id,approved=True)
    target=(payload.to_email or customer.billing_email or '').strip()
    if not target:
        contact=db.query(CustomerContact).filter(CustomerContact.customer_id==customer.id,CustomerContact.active.is_(True),CustomerContact.quote_contact.is_(True)).order_by(CustomerContact.primary.desc()).first()
        target=(contact.email or '').strip() if contact else ''
    if not target or '@' not in target:
        raise HTTPException(status_code=400,detail='No valid customer quote email is available. Enter an email address or add one in Customer 360.')
    row=queue_email(db,to_addresses=[target],subject=f'Valhalla TMS Quote {q.quote_number}',body=_quote_email_body(q,customer,selected),recipient_type='customer',related_type='quote',related_id=str(q.id),customer_id=q.customer_id)
    db.commit()
    return {'ok':True,'to':target,'status':row.status if row else 'queued'}


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
        is_selected = copy.get("provider")!="muse_freight" and int(copy.get("carrier_id", 0)) == payload.carrier_id
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
    return _serialize_quote(q, db, include_preview=True)
