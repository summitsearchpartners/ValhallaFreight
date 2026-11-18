from datetime import datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from fastapi.responses import FileResponse
from pathlib import Path
import uuid
from app.db.session import get_db
from app.models import Quote, Shipment, TrackingEvent, Customer, Carrier, ShipmentDocument, CarrierSubmission, OperationalNotification
from app.domains.customers.models import CustomerLocation, CustomerActivity
from app.schemas.entities import ShipmentCreate, ShipmentOut, TrackingEventCreate, DirectShipmentCreate, QuoteRequest, ShipmentUpdate
from app.domains.shipments.import_service import import_shipments
from app.domains.shipments.service import update_shipment
from app.services.rating import RatingEngine
from app.core.config import settings
from app.integrations.shipment_booking import submit_shipment_to_carrier

router = APIRouter(prefix="/shipments", tags=["Shipments"])


def _normalize_postal(value) -> str:
    """Normalize postal codes for lane matching.

    US ZIP+4 values (66061-3554 / 660613554) are intentionally reduced to the
    five-digit rated ZIP because they are the same rating geography. Canadian
    and other postal codes keep their complete normalized value.
    """
    raw = "".join(str(value or "").strip().upper().split())
    digits = raw.replace("-", "")
    if len(digits) in (5, 9) and digits.isdigit():
        return digits[:5]
    return raw


def _normalize_locality(value) -> str:
    return " ".join(str(value or "").strip().upper().split())


def _validate_confirmed_lane(db: Session, q: Quote, payload: ShipmentCreate) -> None:
    """Prevent a rated ZIP from being silently paired with a facility in another ZIP.

    Saved customer locations are validated from the database. One-off addresses must
    carry the original ZIP returned by Google Places or an explicit manual confirmation. The UI
    keeps the rated ZIP locked for display, so this second value is intentionally
    preserved for approval-time validation.
    """
    rated_origin = _normalize_postal((q.origin or {}).get("postal_code"))
    rated_destination = _normalize_postal((q.destination or {}).get("postal_code"))

    def validate_side(label: str, address, location_id, rated_zip: str):
        if not address:
            raise HTTPException(status_code=400, detail=f"{label} address is required before shipment approval.")
        for field in ("address1", "city", "state", "postal_code"):
            if not str(getattr(address, field, "") or "").strip():
                raise HTTPException(422, f"{label} requires a complete street address, city, state and ZIP for the BOL and carrier booking.")
        actual_zip = ""
        if location_id:
            loc = db.get(CustomerLocation, location_id)
            if not loc or loc.customer_id != q.customer_id:
                raise HTTPException(status_code=400, detail=f"{label} saved customer location is invalid for this quote.")
            actual_zip = _normalize_postal(loc.postal_code)
        else:
            verified_postal_raw = getattr(address, "verified_postal_code", None)
            actual_zip = _normalize_postal(verified_postal_raw)
            if not actual_zip and address.manual_confirmation:
                actual_zip = _normalize_postal(address.postal_code)
            if not actual_zip:
                raise HTTPException(
                    status_code=400,
                    detail=f"{label} requires a saved location, an address suggestion, or manual address confirmation.",
                )
            verified_city = getattr(address, "verified_city", None)
            verified_state = getattr(address, "verified_state", None)
            if verified_city and verified_state:
                if (_normalize_locality(address.city) != _normalize_locality(verified_city) or
                        _normalize_locality(address.state) != _normalize_locality(verified_state)):
                    raise HTTPException(
                        status_code=400,
                        detail=f"{label} city/state must remain {verified_city}, {verified_state} for the selected Google-verified address.",
                    )
        if _normalize_postal(address.postal_code) != rated_zip:
            raise HTTPException(400, f"{label} ZIP must match rated ZIP {rated_zip}. Re-rate the quote to change the lane.")
        if actual_zip != rated_zip:
            display_zip = getattr(address, "verified_postal_code", None) if not location_id else getattr(loc, "postal_code", actual_zip)
            raise HTTPException(
                status_code=400,
                detail=f"{label} was verified as {address.city}, {address.state} {display_zip}, but this quote was rated for ZIP {rated_zip}. Select a facility in the rated ZIP or re-rate the quote.",
            )

    validate_side("Ship From", payload.origin, payload.origin_location_id, rated_origin)
    validate_side("Ship To", payload.destination, payload.destination_location_id, rated_destination)


def _shipment_number():
    return f"VFS-{datetime.utcnow():%y%m%d%H%M%S%f}"


def _quote_number():
    return f"VFQ-{datetime.utcnow():%y%m%d%H%M%S%f}"


def _assign_bol_number(db: Session, shipment: Shipment) -> str:
    """Assign a human-friendly numeric BOL exactly once.

    New Valhalla-created shipments use an eight-digit number beginning at 10000001.
    The value is derived from the internal shipment id and checked for collisions
    with imported/external BOL values before assignment.
    """
    candidate = 10000000 + int(shipment.id)
    while db.query(Shipment).filter(Shipment.bol_number == str(candidate), Shipment.id != shipment.id).first():
        candidate += 1
    return str(candidate)


def _instruction_flags(text: str | None) -> dict:
    value = " ".join(str(text or "").lower().replace('-', ' ').split())
    def has(*terms):
        return any(term in value for term in terms)
    return {
        'appointment_required': has('appointment', 'call before', 'call ahead', 'schedule delivery', 'schedule pickup', 'delivery appointment', 'pickup appointment'),
        'liftgate_default': has('liftgate', 'lift gate'),
        'residential': has('residential', 'residence', 'home delivery', 'home pickup'),
        'limited_access': has('limited access', 'school', 'university', 'church', 'military', 'correctional', 'prison', 'construction site', 'farm', 'ranch', 'mine', 'mining', 'quarry', 'self storage', 'storage facility', 'power plant', 'utility plant', 'mill site'),
    }


def _save_confirmed_location_if_new(db: Session, customer_id: int, address: dict, side: str, existing_location_id=None, accessorials=None):
    if existing_location_id or not address or not address.get('address1'):
        return existing_location_id
    address1=str(address.get('address1') or '').strip(); city=str(address.get('city') or '').strip(); state=str(address.get('state') or '').strip(); postal=str(address.get('postal_code') or '').strip()
    existing=db.query(CustomerLocation).filter(CustomerLocation.customer_id==customer_id,CustomerLocation.address1.ilike(address1),CustomerLocation.city.ilike(city),CustomerLocation.state.ilike(state),CustomerLocation.postal_code==postal).first()
    if existing: return existing.id
    name=str(address.get('name') or '').strip() or f"{city or 'Customer'} {'Ship From' if side=='pickup' else 'Ship To'} - {address1}"
    flags=_instruction_flags(address.get('instructions'))
    selected=set(accessorials or [])
    flags['appointment_required'] = flags['appointment_required'] or f'appointment_{side}' in selected
    flags['liftgate_default'] = flags['liftgate_default'] or f'liftgate_{side}' in selected
    flags['residential'] = flags['residential'] or f'residential_{side}' in selected
    flags['limited_access'] = flags['limited_access'] or f'limited_access_{side}' in selected
    loc=CustomerLocation(customer_id=customer_id,name=name[:180],location_type='shipping',address1=address1,address2=address.get('address2') or None,city=city,state=state,postal_code=postal,country=address.get('country') or 'USA',contact_name=address.get('contact_name') or None,phone=address.get('phone') or None,email=address.get('email') or None,dock_hours=address.get('dock_hours') or None,instructions=address.get('instructions') or None,appointment_required=flags['appointment_required'],liftgate_default=flags['liftgate_default'],residential=flags['residential'],limited_access=flags['limited_access'],active=True)
    db.add(loc); db.flush()
    inferred=[label for key,label in [('appointment_required','Appointment'),('liftgate_default','Liftgate'),('residential','Residential'),('limited_access','Limited Access')] if flags[key]]
    inference_text=', '.join(inferred) if inferred else 'No defaults detected from the shipment instructions/accessorials'
    db.add(CustomerActivity(customer_id=customer_id,activity_type='location',subject='Shipment facility saved automatically',body=f'{name} was added to Customer 360 from an approved shipment. {inference_text}. Review the location defaults for future quotes.',created_by='Valhalla Freight'))
    db.add(OperationalNotification(audience='internal',notification_type='customer_location_review',severity='warning',customer_id=customer_id,location_id=loc.id,target_path=f'/customers/{customer_id}?tab=locations&location={loc.id}',title='Review new customer shipping location',body=f'{name} was saved from an approved shipment. {inference_text}. Review Appointment, Liftgate, Residential and Limited Access defaults in Customer 360 so future quotes auto-populate correctly.'))
    return loc.id

def _create_from_quote(db: Session, q: Quote, carrier_id: int, pickup_date=None, scheduled_pickup_at=None, requested_delivery_at=None, origin=None, destination=None, origin_location_id=None, destination_location_id=None, accessorials=None, po_number=None, customer_reference=None, package_count=None, package_type=None, commodity_description=None, nmfc_number=None, hazmat_emergency_contact=None, hazmat_emergency_phone=None, declared_value=None, muse_revision=None):
    q=db.query(Quote).filter_by(id=q.id).with_for_update().populate_existing().first()
    if q.status=="booked":raise HTTPException(409,"This quote has already been booked")
    if muse_revision:
        from app.services import muse_enrollment as access
        from app.models import MuseQuoteRate
        access.require_enabled(db,q.customer_id,approved=True,lock=True)
        offer=db.get(MuseQuoteRate,q.id)
        if not offer or offer.revision!=muse_revision or offer.carrier_id!=carrier_id:
            raise HTTPException(409,"This Muse offer changed. Refresh and select the current Muse rate.")
        if q.expires_at and q.expires_at<=datetime.utcnow():raise HTTPException(409,"This quote expired. Request a new Muse quote.")
        matches=[o for o in q.options or [] if o.get("selected") and o.get("provider")=="muse_freight" and o.get("muse_revision")==muse_revision]
    else:
        matches = [o for o in (q.options or []) if o.get("provider")!="muse_freight" and int(o.get("carrier_id", 0)) == carrier_id]
    if not matches:
        raise HTTPException(status_code=400, detail="Carrier option not found on quote")
    opt = matches[0]
    from app.services.freight_totals import confirmed_package_count
    package_count = confirmed_package_count(q.handling_units, package_count)
    schedule_at = scheduled_pickup_at or q.requested_pickup_at
    legacy_pickup = schedule_at.date() if schedule_at else pickup_date
    delivery_target = requested_delivery_at or q.requested_delivery_at
    carrier_eta = (legacy_pickup + timedelta(days=int(opt["transit_days"]))) if legacy_pickup else None
    final_origin = origin.model_dump() if hasattr(origin, "model_dump") else (origin or q.origin)
    final_destination = destination.model_dump() if hasattr(destination, "model_dump") else (destination or q.destination)
    final_accessorials = list(accessorials if accessorials is not None else (q.accessorials or []))
    if 'hazmat' in final_accessorials and (not (hazmat_emergency_contact or '').strip() or not (hazmat_emergency_phone or '').strip()):raise HTTPException(422,'Hazardous-materials shipments require an emergency contact and phone')
    # Confirmed one-off facilities are promoted into Customer 360 automatically after approval.
    origin_location_id = _save_confirmed_location_if_new(db,q.customer_id,final_origin,'pickup',origin_location_id,final_accessorials)
    destination_location_id = _save_confirmed_location_if_new(db,q.customer_id,final_destination,'delivery',destination_location_id,final_accessorials)

    # Saved customer locations are the source of truth for default accessorials once the
    # actual shipping/receiving facility is confirmed after quote approval.
    def apply_location_defaults(location_id, side):
        if not location_id:
            return
        loc = db.get(CustomerLocation, location_id)
        if not loc or loc.customer_id != q.customer_id:
            return
        mapping = {
            "appointment_required": f"appointment_{side}",
            "liftgate_default": f"liftgate_{side}",
            "residential": f"residential_{side}",
            "limited_access": f"limited_access_{side}",
        }
        for attr, code in mapping.items():
            if getattr(loc, attr, False) and code not in final_accessorials:
                final_accessorials.append(code)

    apply_location_defaults(origin_location_id, "pickup")
    apply_location_defaults(destination_location_id, "delivery")

    s = Shipment(
        shipment_number=_shipment_number(),
        customer_id=q.customer_id,
        carrier_id=carrier_id,
        quote_id=q.id,
        origin=final_origin,
        destination=final_destination,
        handling_units=q.handling_units,
        accessorials=final_accessorials,
        carrier_cost=Decimal(str(opt["carrier_cost"])),
        customer_charge=Decimal(str(opt["customer_price"])),
        pickup_date=legacy_pickup,
        estimated_delivery=carrier_eta,
        scheduled_pickup_at=schedule_at,
        requested_delivery_at=delivery_target,
        po_number=(str(po_number).strip() if po_number else None),
        customer_reference=(str(customer_reference).strip() if customer_reference else None),
        package_count=package_count, package_type=package_type, commodity_description=commodity_description, nmfc_number=nmfc_number,
        hazmat_emergency_contact=hazmat_emergency_contact, hazmat_emergency_phone=hazmat_emergency_phone, declared_value=declared_value,
        payment_terms=q.payment_terms or "Prepaid",
    )
    db.add(s)
    db.flush()
    if not s.bol_number:
        s.bol_number = _assign_bol_number(db, s)
    if muse_revision:
        from app.models import MuseBooking
        from app.services import muse_enrollment as access
        root=access.manufacturer(db,q.customer_id)
        s.status="pickup_requested"
        booking=MuseBooking(customer_id=root.id,shipment_id=s.id,status="requested")
        db.add(booking);db.flush()
        access.notify_muse(db,root,"New Muse shipment booking",
            f"{root.name} requested booking for {s.shipment_number}. Review the BOL in the Muse Portal.","muse_booking",booking.id)
    q.status = "booked"
    db.commit()
    db.refresh(s)
    return s


@router.get("", response_model=list[ShipmentOut])
def list_shipments(db: Session = Depends(get_db)):
    return db.query(Shipment).order_by(Shipment.created_at.desc()).all()


@router.post("", response_model=ShipmentOut)
async def book(payload: ShipmentCreate, db: Session = Depends(get_db)):
    q = db.query(Quote).filter(Quote.quote_number == payload.quote_number).first()
    if not q:
        raise HTTPException(status_code=404, detail="Quote not found")
    _validate_confirmed_lane(db, q, payload)
    shipment=_create_from_quote(db, q, payload.carrier_id, payload.pickup_date, payload.scheduled_pickup_at, payload.requested_delivery_at, payload.origin, payload.destination, payload.origin_location_id, payload.destination_location_id, payload.accessorials, payload.po_number, payload.customer_reference, payload.package_count, payload.package_type, payload.commodity_description, payload.nmfc_number, payload.hazmat_emergency_contact, payload.hazmat_emergency_phone, payload.declared_value, payload.muse_revision)
    await submit_shipment_to_carrier(db,shipment)
    db.refresh(shipment)
    return shipment


@router.post("/direct", response_model=ShipmentOut)
async def direct_shipment(payload: DirectShipmentCreate, db: Session = Depends(get_db)):
    request = QuoteRequest(
        customer_id=payload.customer_id,
        origin=payload.origin,
        destination=payload.destination,
        handling_units=payload.handling_units,
        accessorials=payload.accessorials,
        requested_pickup_at=payload.requested_pickup_at,
        requested_delivery_at=payload.requested_delivery_at,
        payment_terms=payload.payment_terms,
    )
    try:
        options = await RatingEngine(db).get_rates(request)
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
        requested_pickup_at=payload.requested_pickup_at,
        requested_delivery_at=payload.requested_delivery_at,
        payment_terms=payload.payment_terms,
    )
    db.add(q)
    db.flush()
    shipment=_create_from_quote(db, q, payload.carrier_id, payload.pickup_date, payload.requested_pickup_at, payload.requested_delivery_at)
    await submit_shipment_to_carrier(db,shipment)
    db.refresh(shipment)
    return shipment


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
    documents=db.query(ShipmentDocument).filter(ShipmentDocument.shipment_id==shipment_id).order_by(ShipmentDocument.created_at.desc()).all()
    submissions=db.query(CarrierSubmission).filter(CarrierSubmission.shipment_id==shipment_id).order_by(CarrierSubmission.created_at.desc()).all()
    from app.models import Invoice,TruckloadOrder
    transport_mode="truckload" if db.query(TruckloadOrder.id).filter(TruckloadOrder.shipment_id==shipment_id).first() else "ltl"
    invoice = db.query(Invoice).filter(Invoice.shipment_id == shipment_id).first()
    return {
        "transport_mode": transport_mode,
        "invoice_issued": bool(invoice and invoice.status in {"issued","sent","paid","overdue","partially_paid"}),
        "customer_invoice": {"invoice_number":invoice.invoice_number,"amount":invoice.amount,"status":invoice.status,"due_date":invoice.due_date} if invoice else None,
        "id":s.id,"shipment_number":s.shipment_number,"status":s.status,"pro_number":s.pro_number,"bol_number":s.bol_number,
        "po_number":s.po_number,"customer_reference":s.customer_reference,"package_count":s.package_count,"package_type":s.package_type,
        "commodity_description":s.commodity_description,"nmfc_number":s.nmfc_number,
        "hazmat_emergency_contact":s.hazmat_emergency_contact,"hazmat_emergency_phone":s.hazmat_emergency_phone,
        "declared_value":s.declared_value,"payment_terms":s.payment_terms or "Prepaid",
        "quote_id":s.quote_id,"customer_id":s.customer_id,"customer_name":customer.name if customer else None,
        "carrier_id":s.carrier_id,"carrier_name":carrier.name if carrier else None,"carrier_scac":carrier.scac if carrier else None,
        "origin":s.origin,"destination":s.destination,"handling_units":s.handling_units,"accessorials":s.accessorials,
        "carrier_cost":s.carrier_cost,"final_carrier_cost":s.final_carrier_cost,"customer_charge":s.customer_charge,
        "pickup_date":s.pickup_date,"estimated_delivery":s.estimated_delivery,
        "scheduled_pickup_at":s.scheduled_pickup_at,"requested_delivery_at":s.requested_delivery_at,
        "actual_pickup_at":s.actual_pickup_at,"delivered_at":s.delivered_at,"created_at":s.created_at,
        "tracking_events":[{"id":e.id,"code":e.code,"status":e.status,"description":e.description,"location":e.location,"event_time":e.event_time,"source":e.source} for e in events],
        "documents":[{"id":d.id,"document_type":d.document_type,"name":d.original_name,"content_type":d.content_type,"size_bytes":d.size_bytes,"uploaded_by_role":d.uploaded_by_role,"uploaded_by":d.uploaded_by,"created_at":d.created_at,"url":f"/api/v1/shipments/{shipment_id}/documents/{d.id}"} for d in documents],
        "carrier_submissions":[{"id":x.id,"provider":(x.request_summary or {}).get("provider"),"status":x.status,"provider_reference":x.provider_reference,"pro_number":x.pro_number,"error":x.error,"is_test":bool((x.response_summary or {}).get("is_test")),"created_at":x.created_at} for x in submissions]
    }


@router.post("/{shipment_id}/customer-invoice")
def issue_customer_invoice(shipment_id: int, db: Session = Depends(get_db)):
    request = db.info.get("request")
    user = getattr(request.state, "auth_user", None) if request else None
    if not user or user.role not in {"admin", "broker", "broker_admin"} or getattr(request.state,"support_company_id",None) is not None:
        raise HTTPException(403,"Customer invoices are issued by your broker")
    from app.models import Invoice
    from app.domains.customers.models import CustomerProfile
    s = db.query(Shipment).filter(Shipment.id == shipment_id).with_for_update().first()
    if not s: raise HTTPException(404,"Shipment not found")
    if Decimal(str(s.customer_charge or 0)) <= 0:
        raise HTTPException(422,"Confirm the customer freight charge before issuing an invoice")
    invoice = db.query(Invoice).filter(Invoice.shipment_id == shipment_id).first()
    if not invoice:
        import re
        profile=db.query(CustomerProfile).filter(CustomerProfile.customer_id==s.customer_id).first()
        terms=profile.payment_terms if profile else "Net 30"
        match=re.fullmatch(r"Net\s+(\d{1,3})", str(terms or ""), re.IGNORECASE)
        if not match: raise HTTPException(422,"Set the customer's payment terms to Net days before issuing an invoice")
        invoice=Invoice(invoice_number=f"VFI-{s.id:08d}",customer_id=s.customer_id,shipment_id=s.id,
                        amount=s.customer_charge,status="issued",due_date=datetime.utcnow().date()+timedelta(days=int(match.group(1))))
        db.add(invoice)
    elif invoice.status == "draft":
        invoice.status="issued"
    db.commit()
    return shipment_detail(shipment_id,db)


@router.patch("/{shipment_id}")
def edit_shipment(shipment_id: int, payload: ShipmentUpdate, db: Session = Depends(get_db)):
    shipment = db.get(Shipment, shipment_id)
    if not shipment:
        raise HTTPException(status_code=404, detail="Shipment not found")
    update_shipment(db, shipment, payload)
    return shipment_detail(shipment_id, db)


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


@router.post("/{shipment_id}/documents")
async def upload_shipment_document(shipment_id:int, file:UploadFile=File(...), document_type:str=Form('Other'), uploaded_by_role:str=Form('broker'), uploaded_by:str=Form('Valhalla Freight'), db:Session=Depends(get_db)):
    if not db.get(Shipment,shipment_id): raise HTTPException(404,'Shipment not found')
    allowed={'application/pdf','image/jpeg','image/png','image/webp','application/msword','application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
    content=await file.read()
    if file.content_type not in allowed: raise HTTPException(400,'Supported files: PDF, JPG, PNG, WEBP, DOC, DOCX')
    if len(content)>20*1024*1024: raise HTTPException(400,'Shipment documents are limited to 20 MB')
    folder=Path(settings.document_storage_path).resolve()/f'shipments/{shipment_id}'; folder.mkdir(parents=True,exist_ok=True)
    ext=Path(file.filename or '').suffix.lower(); stored=f'{uuid.uuid4().hex}{ext}'; (folder/stored).write_bytes(content)
    row=ShipmentDocument(shipment_id=shipment_id,document_type=document_type,original_name=file.filename or 'document',stored_name=stored,content_type=file.content_type,size_bytes=len(content),uploaded_by_role=uploaded_by_role,uploaded_by=uploaded_by)
    db.add(row);db.commit();db.refresh(row);return {'id':row.id,'name':row.original_name,'url':f'/api/v1/shipments/{shipment_id}/documents/{row.id}'}

@router.get("/{shipment_id}/documents/{document_id}")
def get_shipment_document(shipment_id:int,document_id:int,db:Session=Depends(get_db)):
    row=db.query(ShipmentDocument).filter(ShipmentDocument.id==document_id,ShipmentDocument.shipment_id==shipment_id).first()
    if not row: raise HTTPException(404,'Shipment document not found')
    path=Path(settings.document_storage_path).resolve()/f'shipments/{shipment_id}'/row.stored_name
    if not path.exists(): raise HTTPException(404,'Stored file unavailable')
    return FileResponse(path,media_type=row.content_type or 'application/octet-stream',filename=row.original_name)

@router.delete("/{shipment_id}/documents/{document_id}")
def delete_shipment_document(shipment_id:int,document_id:int,db:Session=Depends(get_db)):
    row=db.query(ShipmentDocument).filter(ShipmentDocument.id==document_id,ShipmentDocument.shipment_id==shipment_id).first()
    if not row: raise HTTPException(404,'Shipment document not found')
    path=Path(settings.document_storage_path).resolve()/f'shipments/{shipment_id}'/row.stored_name
    if path.exists(): path.unlink()
    db.delete(row);db.commit();return {'ok':True}
