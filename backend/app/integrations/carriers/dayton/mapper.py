from __future__ import annotations
from decimal import Decimal
from app.integrations.base.models import NormalizedRate, NormalizedTrackingEvent

ACCESSORIAL_MAP = {
    'appointment_delivery':'NOT','appointment_pickup':'NOT','liftgate_delivery':'LIFT',
    'residential_delivery':'RESID','residential_pickup':'RESIP','limited_access_delivery':'LIMIT',
    'airport_delivery':'AIRDEL','trade_show_delivery':'CVD','chicago_trade_show_delivery':'CCVD',
}
TRACKING_MAP = {
    'ADD':'PICKED_UP','ATD':'DELIVERY_ATTEMPT','DLV':'DELIVERED','OK':'DELIVERED','DSC':'AT_DESTINATION_TERMINAL',
    'LOA':'LOADED','OFD':'OUT_FOR_DELIVERY','OTR':'IN_TRANSIT','PWD':'WEATHER_DELAY','RP':'CONSOLIDATED',
    'SBR':'SHIPMENT_INFORMATION_RECEIVED','SAD':'TRAILER_DROPPED','TPC':'PARTNER_TRANSFER','UNL':'UNLOADED'
}

def map_accessorials(values: list[str]) -> list[str]:
    result=[]
    for value in values or []:
        normalized=value.strip().lower().replace(' ','_').replace('/','_')
        code=ACCESSORIAL_MAP.get(normalized)
        if code and code not in result: result.append(code)
        elif value.isupper() and len(value)<=10 and value not in result: result.append(value)
    return result

def build_rate_payload(request, account: str, direct_only: bool=False, terms: str='ThirdPartyPrepaid') -> dict:
    items=[]; handling=[]
    for idx,u in enumerate(request.handling_units):
        pair=f'VF-HU-{idx+1}'
        items.append({'class':float(u.freight_class),'weight':int(round(u.weight_lbs*u.quantity)),'userHandlingUnitPairingId':pair})
        handling.append({'quantity':u.quantity,'length':u.length_in,'width':u.width_in,'height':u.height_in,'stackable':None,'userHandlingUnitPairingId':pair})
    return {
        'accessorials':map_accessorials(request.accessorials),
        'account':account,
        'destination':request.destination.postal_code,
        'directOnly':direct_only,
        'handlingUnits':handling,
        'items':items,
        'origin':request.origin.postal_code,
        'serviceOptions':'None',
        'shipmentDate':request.requested_pickup_at.isoformat() if request.requested_pickup_at else None,
        'skids':sum(u.quantity for u in request.handling_units),
        'terms':terms,
    }

def _movement_type(payload: dict) -> str:
    """Normalize the carrier's lane result to Direct / Indirect / Unknown.

    Dayton's Rates response exposes movementType. Partner terminal fields are retained as a
    defensive signal for interline/partner service when movementType is absent. The carrier
    response remains the source of truth; Valhalla does not infer geography on its own.
    """
    raw=str(payload.get('movementType') or '').strip()
    if raw:
        key=raw.lower()
        if key == 'direct': return 'Direct'
        if key in {'indirect','interline','partner','partnered'} or 'interline' in key or 'partner' in key:
            return 'Indirect'
        return raw
    service=payload.get('serviceEligibility') or {}
    if service.get('originPartner') or service.get('destinationPartner'):
        return 'Indirect'
    return 'Unknown'

def normalize_rate(payload: dict) -> NormalizedRate:
    service=payload.get('serviceEligibility') or {}
    movement=_movement_type(payload)
    accessorials=Decimal(str(payload.get('additionalCharges') or 0))
    fuel=Decimal(str(payload.get('fuelSurchargeAmount') or 0))
    total=Decimal(str(payload.get('total') or 0))
    gross=Decimal(str(payload.get('gross') or 0))
    base=max(Decimal('0'), total-fuel-accessorials)
    return NormalizedRate(
        carrier_code='DAFG', carrier_name='Dayton Freight Lines', service='Standard LTL',
        transit_days=int(service.get('serviceDays') or 0), carrier_cost=total, base_charge=base,
        fuel=fuel, accessorials=accessorials, provider_quote_id=str(payload.get('id')) if payload.get('id') is not None else None,
        movement_type=movement, warnings=payload.get('warnings') or [],
        metadata={'gross':str(gross),'discount':str(payload.get('discount') or 0),'discount_percent':str(payload.get('discountPercent') or 0),
                  'service_eligibility':service,'upgrade_options':payload.get('upgradeOptions') or [],'disclaimer':payload.get('disclaimer'),'trace_id':payload.get('traceId')}
    )

def normalize_tracking(payload: dict) -> list[NormalizedTrackingEvent]:
    events=[]
    rows=payload.get('results') or []
    for result in rows:
        statuses=result.get('status') or result.get('statuses') or []
        if isinstance(statuses, dict): statuses=[statuses]
        for row in statuses:
            code=str(row.get('code') or row.get('activityCode') or '').upper()
            events.append(NormalizedTrackingEvent(code=code,status=TRACKING_MAP.get(code,code or 'UNKNOWN'),description=row.get('description') or row.get('activityDescription'),location=row.get('location') or row.get('city'),event_time=row.get('time') or row.get('date')))
    return events
