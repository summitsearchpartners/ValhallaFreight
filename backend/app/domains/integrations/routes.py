from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import IntegrationConnection, Shipment, TrackingEvent, Carrier
from app.integrations.service import get_dayton_connection, public_connection, audit, analyze_openapi
from app.integrations.carriers.dayton import DaytonAdapter
from app.integrations.carriers.dayton.client import DaytonClient
from app.integrations.carriers.dayton.mapper import build_rate_payload, normalize_rate
from app.integrations.carriers.dayton.tracking import track as dayton_track
from app.integrations.carriers.dayton.pickup import create as dayton_create_pickup, build_test_pickup_payload
from app.integrations.base.exceptions import CarrierIntegrationError, CarrierCredentialsMissing, CarrierRemoteError

router=APIRouter(prefix='/integrations',tags=['Integration Hub'])

class IntegrationUpdate(BaseModel):
    status:str|None=None
    environment:str|None=None
    settings:dict|None=None

class DaytonConfig(BaseModel):
    environment: str = 'sandbox'
    base_url: str = 'https://api.daytonfreight.com'
    account: str | None = None
    terms: str = 'ThirdPartyPrepaid'
    direct_only: bool = False

class DaytonRateTest(BaseModel):
    origin_zip: str
    destination_zip: str
    freight_class: str = '70'
    weight_lbs: int = Field(default=500, ge=1)
    quantity: int = Field(default=1, ge=1)
    length_in: float = 48
    width_in: float = 40
    height_in: float = 48
    accessorials: list[str] = []

class TrackingTest(BaseModel):
    number: str
    type: str = 'Pro'

class ServiceLane(BaseModel):
    origin_zip: str
    destination_zip: str
    date: str | None = None

class OpenApiImport(BaseModel):
    specification: dict
    provider_name: str | None = None
    category: str = 'Carrier Connectivity'

@router.get('')
def list_integrations(db:Session=Depends(get_db)):
    # Ensure the Dayton adapter exists even on databases created before v0.8.0.
    get_dayton_connection(db)
    rows=db.query(IntegrationConnection).order_by(IntegrationConnection.category,IntegrationConnection.provider).all()
    return [public_connection(x) for x in rows]

@router.patch('/connection/{integration_id}')
def update(integration_id:int,payload:IntegrationUpdate,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(row,k,v)
    db.commit();return {'ok':True}

@router.post('/connection/{integration_id}/test')
async def test(integration_id:int,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    if row.provider == 'Dayton Freight':
        return await test_dayton(db)
    row.last_sync_at=datetime.utcnow(); row.last_error=None
    if row.status=='available': row.status='configured'
    db.commit();return {'ok':True,'status':row.status,'message':'Configuration health check completed. Live vendor calls require provider credentials and enabled adapters.'}

@router.get('/dayton')
def dayton_status(db:Session=Depends(get_db)):
    row=get_dayton_connection(db); client=DaytonClient(); adapter=DaytonAdapter()
    settings=row.settings or {}
    return {
        **public_connection(row),
        'scac':'DAFG','adapter_installed':True,'credentials_configured':adapter.configured(),
        'credential_source':'Environment (.env)','username_hint':(client.username[:3]+'••••') if client.username else None,
        'account':client.account or settings.get('account'),
        'base_url':client.base_url,
        'auth_type':'Basic Authentication','username_limit_note':'Dayton API uses the first 10 characters of the web username.',
        'capability_details':[
          {'key':'rating','label':'Live LTL Rating','status':'ready'}, {'key':'pickup','label':'Pickup Create / Update / Cancel','status':'ready'},
          {'key':'tracking','label':'Tracking + History','status':'ready'}, {'key':'bol','label':'Electronic BOL + PDF','status':'ready'},
          {'key':'documents','label':'Shipment Images / Documents','status':'ready'}, {'key':'service','label':'Service Eligibility / Transit','status':'ready'},
          {'key':'metadata','label':'Accessorials / Classes / Packaging / Terminals','status':'ready'}]
    }

@router.patch('/dayton/config')
def configure_dayton(payload:DaytonConfig,db:Session=Depends(get_db)):
    row=get_dayton_connection(db)
    row.environment=payload.environment
    row.settings={**(row.settings or {}),'base_url':payload.base_url,'account':payload.account,'terms':payload.terms,'direct_only':payload.direct_only}
    row.status='configured'
    db.commit(); audit(db,'dayton_configuration_updated',{'environment':payload.environment,'account':payload.account,'terms':payload.terms,'direct_only':payload.direct_only})
    return public_connection(row)

@router.post('/dayton/test')
async def test_dayton(db:Session=Depends(get_db)):
    row=get_dayton_connection(db); adapter=DaytonAdapter()
    try:
        result=await adapter.test_connection()
        row.last_sync_at=datetime.utcnow(); row.last_error=None
        row.status='connected' if result.get('ok') else 'configured'
        db.commit(); audit(db,'dayton_connection_test',{'ok':result.get('ok'),'message':result.get('message')})
        return {**result,'status':row.status}
    except CarrierIntegrationError as exc:
        row.last_sync_at=datetime.utcnow(); row.last_error=str(exc); row.status='error'; db.commit()
        audit(db,'dayton_connection_test',{'ok':False,'error':str(exc)})
        raise HTTPException(502,str(exc))

@router.get('/dayton/accounts')
async def dayton_accounts():
    try: return await DaytonClient().request('GET','/api/Accounts')
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.get('/dayton/accessorials')
async def dayton_accessorials():
    try: return await DaytonClient().request('GET','/api/Shipping/Accessorials')
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.get('/dayton/classes')
async def dayton_classes():
    try: return await DaytonClient().request('GET','/api/Shipping/classes')
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.get('/dayton/service-centers')
async def dayton_service_centers():
    try: return await DaytonClient().request('GET','/api/ServiceCenters')
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.post('/dayton/service-eligibility')
async def dayton_service_eligibility(payload:ServiceLane):
    params={'origin':payload.origin_zip,'destination':payload.destination_zip}
    if payload.date: params['date']=payload.date
    try: return await DaytonClient().request('GET','/api/Shipping/ServiceEligibility',params=params)
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.post('/dayton/rate-test')
async def dayton_rate_test(payload:DaytonRateTest,db:Session=Depends(get_db)):
    row=get_dayton_connection(db); cfg=row.settings or {}; client=DaytonClient(); account=client.account or cfg.get('account')
    if not account: raise HTTPException(400,'Dayton account code is required. Add DAYTON_API_ACCOUNT to .env or set the account in Integration Hub.')
    class U:
        def __init__(self,p):
            self.quantity=p.quantity;self.weight_lbs=p.weight_lbs;self.length_in=p.length_in;self.width_in=p.width_in;self.height_in=p.height_in;self.freight_class=p.freight_class
    class A:
        def __init__(self,z): self.postal_code=z
    class R: pass
    req=R(); req.origin=A(payload.origin_zip); req.destination=A(payload.destination_zip); req.handling_units=[U(payload)]; req.accessorials=payload.accessorials; req.requested_pickup_at=None
    request=build_rate_payload(req,account,bool(cfg.get('direct_only',False)),cfg.get('terms','ThirdPartyPrepaid'))
    try:
        response=await client.request('POST','/api/Rates',json=request); normalized=normalize_rate(response)
        audit(db,'dayton_rate_test',{'origin':payload.origin_zip,'destination':payload.destination_zip,'quote_id':normalized.provider_quote_id})
        return {'request':request,'normalized':normalized.__dict__,'raw_response':response}
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.post('/dayton/tracking-test')
async def dayton_tracking_test(payload:TrackingTest,db:Session=Depends(get_db)):
    try:
        normalized,raw=await dayton_track(payload.number,payload.type); audit(db,'dayton_tracking_test',{'number_type':payload.type,'event_count':len(normalized)})
        return {'normalized':[x.__dict__ for x in normalized],'raw_response':raw}
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.post('/dayton/pickup-test')
async def dayton_pickup_test(db:Session=Depends(get_db)):
    # Dayton documents a TESTING reference that prevents a real pickup from being created.
    payload=build_test_pickup_payload()
    try:
        response=await dayton_create_pickup(payload); audit(db,'dayton_pickup_test',{'pickup_number':response.get('pickupNumber') if isinstance(response,dict) else None})
        return {'request':payload,'response':response,'safe_test':True}
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))


@router.post('/dayton/shipments/{shipment_id}/sync-tracking')
async def dayton_sync_shipment_tracking(shipment_id:int,db:Session=Depends(get_db)):
    shipment=db.get(Shipment,shipment_id)
    if not shipment: raise HTTPException(404,'Shipment not found')
    carrier=db.get(Carrier,shipment.carrier_id) if shipment.carrier_id else None
    if not carrier or carrier.scac!='DAFG': raise HTTPException(400,'This shipment is not assigned to Dayton Freight')
    number=shipment.pro_number or shipment.bol_number
    number_type='Pro' if shipment.pro_number else 'BillOfLading'
    if not number: raise HTTPException(400,'A PRO or BOL number is required before Dayton tracking can be synchronized')
    try:
        normalized,raw=await dayton_track(number,number_type)
    except CarrierIntegrationError as exc:
        raise HTTPException(400,str(exc))
    created=0
    for event in normalized:
        # Keep carrier synchronization idempotent enough for repeated manual refreshes.
        exists=db.query(TrackingEvent).filter(TrackingEvent.shipment_id==shipment.id,TrackingEvent.code==event.code,TrackingEvent.source=='dayton_api').first()
        if exists: continue
        event_time=datetime.utcnow()
        if event.event_time:
            try: event_time=datetime.fromisoformat(str(event.event_time).replace('Z','+00:00')).replace(tzinfo=None)
            except Exception: pass
        db.add(TrackingEvent(shipment_id=shipment.id,code=event.code or 'DFL',status=event.status,description=event.description,location=event.location,event_time=event_time,source='dayton_api'))
        created+=1
        if event.status=='DELIVERED' and not shipment.delivered_at: shipment.delivered_at=event_time; shipment.status='delivered'
        elif event.status=='PICKED_UP' and not shipment.actual_pickup_at: shipment.actual_pickup_at=event_time; shipment.status='picked_up'
        elif event.status in {'IN_TRANSIT','OUT_FOR_DELIVERY'} and shipment.status not in {'delivered'}: shipment.status=event.status.lower()
    db.commit(); audit(db,'dayton_tracking_sync',{'shipment_id':shipment_id,'number_type':number_type,'created_events':created})
    return {'ok':True,'created_events':created,'carrier':'Dayton Freight','raw_response':raw}

@router.post('/openapi/analyze')
def openapi_analyze(payload:OpenApiImport):
    return analyze_openapi(payload.specification)

@router.post('/openapi/import')
def openapi_import(payload:OpenApiImport,db:Session=Depends(get_db)):
    analysis=analyze_openapi(payload.specification); provider=payload.provider_name or analysis['title']
    row=db.query(IntegrationConnection).filter(IntegrationConnection.provider==provider).first()
    caps=sorted({str(tag).lower().replace(' ','_') for tag in analysis['tags']})
    settings={'openapi_title':analysis['title'],'openapi_version':analysis['version'],'endpoint_count':analysis['endpoint_count'],'tags':analysis['tags']}
    if not row:
        row=IntegrationConnection(provider=provider,category=payload.category,status='imported',environment='sandbox',capabilities=caps,settings=settings);db.add(row)
    else:
        row.status='imported';row.capabilities=caps;row.settings={**(row.settings or {}),**settings}
    db.commit();db.refresh(row);audit(db,'openapi_imported',{'provider':provider,'endpoint_count':analysis['endpoint_count']})
    return {'connection':public_connection(row),'analysis':analysis}
