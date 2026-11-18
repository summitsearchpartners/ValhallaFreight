from __future__ import annotations
from app.models import Carrier, CarrierSubmission
from app.integrations.base import get_carrier

async def submit_shipment_to_carrier(db, shipment):
    from app.models import MuseBooking
    muse_booking=db.query(MuseBooking).filter_by(shipment_id=shipment.id).first()
    if muse_booking:
        existing=db.query(CarrierSubmission).filter_by(shipment_id=shipment.id).first()
        if existing:return existing
        submission=CarrierSubmission(shipment_id=shipment.id,carrier_id=shipment.carrier_id,status="pending_muse_confirmation",
            request_summary={"provider":"muse_freight","shipment_number":shipment.shipment_number,"bol_number":shipment.bol_number})
        db.add(submission);db.commit()
        return submission
    carrier=db.get(Carrier,shipment.carrier_id) if shipment.carrier_id else None
    submission=CarrierSubmission(shipment_id=shipment.id,carrier_id=shipment.carrier_id,status='pending',request_summary={'shipment_number':shipment.shipment_number,'bol_number':shipment.bol_number})
    db.add(submission); db.flush()
    if not carrier or not carrier.api_enabled:
        submission.status='not_configured'; submission.error='Carrier API booking is not enabled. PRO can be entered manually when assigned.'; db.commit(); return submission
    try:
        adapter=get_carrier(carrier.scac)
        if adapter is not None and hasattr(adapter,'db'): adapter.db=db
    except Exception:
        adapter=None
    if not adapter:
        submission.status='adapter_unavailable'; submission.error=f'No booking adapter registered for {carrier.scac}.'; db.commit(); return submission
    try:
        result=await adapter.book_shipment(shipment,db=db)
        result=result or {}
        pro=str(result.get('pro_number') or result.get('pro') or '').strip() or None
        ref=str(result.get('provider_reference') or result.get('pickup_number') or result.get('id') or '').strip() or None
        submission.status='test_submitted' if result.get('is_test') else 'submitted'; submission.pro_number=pro; submission.provider_reference=ref; submission.response_summary={k:v for k,v in result.items() if k not in {'raw'}}
        if pro: shipment.pro_number=pro
    except NotImplementedError:
        submission.status='capability_unavailable'; submission.error='Carrier adapter is connected but automated booking is not yet implemented for this carrier.'
    except Exception as exc:
        submission.status='error'; submission.error=str(exc)
    db.commit(); db.refresh(submission); return submission
