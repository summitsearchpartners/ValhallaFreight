from __future__ import annotations
from app.services.operations import live_check,record_run,connection_state
from datetime import datetime, timezone
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import IntegrationConnection, IntegrationCredential, Shipment, TrackingEvent, Carrier
from app.integrations.service import get_dayton_connection, public_connection, audit, analyze_openapi, public_credentials, save_credentials, delete_credentials, credential_payload
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

class IntegrationCredentialUpdate(BaseModel):
    auth_type: str = 'none'
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    bearer_token: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    headers: dict[str,str] | None = None

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
    return [{**public_connection(x),**connection_state(db,x)} for x in rows]

@router.patch('/connection/{integration_id}')
def update(integration_id:int,payload:IntegrationUpdate,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(row,k,v)
    row.settings={k:v for k,v in (row.settings or {}).items() if k!='live_check'}
    db.commit();return {'ok':True}

@router.get('/connection/{integration_id}/manage')
def manage_connection(integration_id:int,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    return {'connection':public_connection(row),'credentials':public_credentials(db,row)}

@router.get('/connection/{integration_id}/credentials')
def get_credentials(integration_id:int,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    return public_credentials(db,row)

@router.put('/connection/{integration_id}/credentials')
def put_credentials(integration_id:int,payload:IntegrationCredentialUpdate,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    values=payload.model_dump(exclude_unset=True,exclude={'auth_type'})
    save_credentials(db,row,payload.auth_type,values,merge=True)
    audit(db,'integration_credentials_saved',{'provider':row.provider,'auth_type':payload.auth_type},entity_id=str(row.id))
    return public_credentials(db,row)

@router.delete('/connection/{integration_id}/credentials')
def remove_credentials(integration_id:int,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    delete_credentials(db,row)
    audit(db,'integration_credentials_removed',{'provider':row.provider},entity_id=str(row.id))
    return {'ok':True,'credentials':public_credentials(db,row)}

@router.delete('/connection/{integration_id}')
def delete_connection(integration_id:int,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    request=db.info.get('request')
    if row.provider == 'Dayton Freight' and getattr(getattr(request.state,'auth_user',None),'role',None) != 'admin':
        raise HTTPException(409,'Dayton Freight is a built-in Valhalla carrier adapter and cannot be deleted. Remove its credentials instead.')
    provider=row.provider
    credential=db.query(IntegrationCredential).filter(IntegrationCredential.integration_id==row.id).first()
    if credential: db.delete(credential)
    db.delete(row)
    db.commit()
    audit(db,'integration_adapter_deleted',{'provider':provider},entity_id=str(integration_id))
    return {'ok':True,'deleted_provider':provider}

@router.post('/connection/{integration_id}/test')
async def test(integration_id:int,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    if row.provider == 'Dayton Freight':
        request=db.info.get('request')
        if request and request.state.auth_user.role=='admin': request.state.integration_company_id=row.customer_id
        return await test_dayton(db)
    record_run(db,kind='configuration_review',status='review',summary=f'{row.provider}: configuration inspected; live vendor verification is not implemented',company=row.customer_id,integration=row.id)
    return {'ok':False,'status':'not_verified','message':'Configuration review only. No live vendor connection was tested; use a supported provider adapter.'}

@router.get('/dayton')
def dayton_status(db:Session=Depends(get_db)):
    row=get_dayton_connection(db); client=DaytonClient.from_db(db); adapter=DaytonAdapter(db); creds=public_credentials(db,row)
    settings_row=row.settings or {}
    env_fallback=bool(client.has_credentials and not creds.get('configured'))
    credential_source='Integration Hub secure store' if creds.get('configured') else ('Environment (.env)' if env_fallback else 'Not configured')
    username_hint=creds.get('username_hint') or ((client.username[:3]+'••••') if client.username else None)
    return {
        **public_connection(row),**connection_state(db,row),
        'scac':'DAFG','adapter_installed':True,'credentials_configured':adapter.configured(),
        'credential_source':credential_source,'username_hint':username_hint,
        'account':client.account or settings_row.get('account'),
        'base_url':client.base_url,
        'auth_type':'Basic Authentication','auth_type_key':'basic_auth','username_limit_note':'Dayton API uses the first 10 characters of the web username.',
        'credential_status':creds,
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
    row.settings={k:v for k,v in (row.settings or {}).items() if k!='live_check'}
    row.status='configured'
    db.commit(); audit(db,'dayton_configuration_updated',{'environment':payload.environment,'account':payload.account,'terms':payload.terms,'direct_only':payload.direct_only})
    return public_connection(row)

@router.post('/dayton/test')
async def test_dayton(db:Session=Depends(get_db)):
    row=get_dayton_connection(db); adapter=DaytonAdapter(db)
    try:
        result=await adapter.test_connection()
        row.last_sync_at=datetime.utcnow(); row.last_error=None
        row.status='connected' if result.get('ok') else 'configured'
        db.commit(); audit(db,'dayton_connection_test',{'ok':result.get('ok'),'message':result.get('message')})
        live_check(db,row,result.get('ok'))
        return {**result,'status':row.status}
    except CarrierIntegrationError as exc:
        row.last_sync_at=datetime.utcnow(); row.last_error=str(exc); row.status='error'; db.commit()
        live_check(db,row,False)
        audit(db,'dayton_connection_test',{'ok':False,'error':str(exc)})
        raise HTTPException(502,str(exc))

@router.get('/dayton/accounts')
async def dayton_accounts(db:Session=Depends(get_db)):
    try: return await DaytonClient.from_db(db).request('GET','/api/Accounts')
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.get('/dayton/accessorials')
async def dayton_accessorials(db:Session=Depends(get_db)):
    try: return await DaytonClient.from_db(db).request('GET','/api/Shipping/Accessorials')
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.get('/dayton/classes')
async def dayton_classes(db:Session=Depends(get_db)):
    try: return await DaytonClient.from_db(db).request('GET','/api/Shipping/classes')
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.get('/dayton/service-centers')
async def dayton_service_centers(db:Session=Depends(get_db)):
    try: return await DaytonClient.from_db(db).request('GET','/api/ServiceCenters')
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.post('/dayton/service-eligibility')
async def dayton_service_eligibility(payload:ServiceLane,db:Session=Depends(get_db)):
    params={'origin':payload.origin_zip,'destination':payload.destination_zip}
    if payload.date: params['date']=payload.date
    try: return await DaytonClient.from_db(db).request('GET','/api/Shipping/ServiceEligibility',params=params)
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.post('/dayton/rate-test')
async def dayton_rate_test(payload:DaytonRateTest,db:Session=Depends(get_db)):
    row=get_dayton_connection(db); cfg=row.settings or {}; client=DaytonClient.from_db(db); account=client.account or cfg.get('account')
    if not account: raise HTTPException(400,'Dayton account code is required. Set the account in Integration Hub → Dayton Freight.')
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
    connection=get_dayton_connection(db)
    try:
        normalized,raw=await dayton_track(payload.number,payload.type,client=DaytonClient.from_db(db)); audit(db,'dayton_tracking_test',{'number_type':payload.type,'event_count':len(normalized)})
        return {'normalized':[x.__dict__ for x in normalized],'raw_response':raw}
    except CarrierIntegrationError as exc: raise HTTPException(400,str(exc))

@router.post('/dayton/pickup-test')
async def dayton_pickup_test(db:Session=Depends(get_db)):
    # Dayton documents a TESTING reference that prevents a real pickup from being created.
    payload=build_test_pickup_payload()
    try:
        response=await dayton_create_pickup(payload,client=DaytonClient.from_db(db)); audit(db,'dayton_pickup_test',{'pickup_number':response.get('pickupNumber') if isinstance(response,dict) else None})
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
    connection=get_dayton_connection(db)
    try:
        normalized,raw=await dayton_track(number,number_type,client=DaytonClient.from_db(db))
    except CarrierIntegrationError as exc:
        record_run(db,kind='tracking_sync',status='failed',summary='Dayton tracking refresh failed; review shipment references and connection settings',company=shipment.customer_id,integration=connection.id,shipment=shipment.id,retryable=True)
        raise HTTPException(400,str(exc))
    created=0
    for event in normalized:
        # A retry must not duplicate an event, while repeated status codes at
        # different carrier timestamps must remain distinct observations.
        event_time=datetime.utcnow()
        provided_time=False
        if event.event_time:
            try:
                parsed=datetime.fromisoformat(str(event.event_time).replace('Z','+00:00'))
                event_time=parsed.astimezone(timezone.utc).replace(tzinfo=None) if parsed.tzinfo else parsed
                provided_time=True
            except (ValueError,TypeError):pass
        query=db.query(TrackingEvent).filter(TrackingEvent.shipment_id==shipment.id,TrackingEvent.code==(event.code or 'DFL'),TrackingEvent.status==event.status,TrackingEvent.description==event.description,TrackingEvent.source=='dayton_api')
        if provided_time:query=query.filter(TrackingEvent.event_time==event_time)
        if query.first():continue
        db.add(TrackingEvent(shipment_id=shipment.id,code=event.code or 'DFL',status=event.status,description=event.description,location=event.location,event_time=event_time,source='dayton_api'))
        created+=1
        if event.status=='DELIVERED' and not shipment.delivered_at: shipment.delivered_at=event_time; shipment.status='delivered'
        elif event.status=='PICKED_UP' and not shipment.actual_pickup_at: shipment.actual_pickup_at=event_time; shipment.status='picked_up'
        elif event.status in {'IN_TRANSIT','OUT_FOR_DELIVERY'} and shipment.status not in {'delivered'}: shipment.status=event.status.lower()
    db.commit(); audit(db,'dayton_tracking_sync',{'shipment_id':shipment_id,'number_type':number_type,'created_events':created})
    record_run(db,kind='tracking_sync',status='succeeded',summary=f'Dayton tracking refreshed: {created} new event(s)',company=shipment.customer_id,integration=connection.id,shipment=shipment.id)
    return {'ok':True,'created_events':created,'carrier':'Dayton Freight','raw_response':raw}

@router.post('/openapi/analyze')
def openapi_analyze(payload:OpenApiImport):
    return analyze_openapi(payload.specification)

@router.post('/openapi/import')
def openapi_import(payload:OpenApiImport,db:Session=Depends(get_db)):
    analysis=analyze_openapi(payload.specification); provider=payload.provider_name or analysis['title']
    if 'dayton' in str(provider).lower():
        provider='Dayton Freight'
        analysis['detected_auth_type']='basic_auth'
    from app.db.tenant_scope import integration_company
    company=integration_company(db)
    row=db.query(IntegrationConnection).filter(IntegrationConnection.provider==provider, IntegrationConnection.customer_id==company).first()
    caps=sorted({str(tag).lower().replace(' ','_') for tag in analysis['tags']})
    settings={'openapi_title':analysis['title'],'openapi_version':analysis['version'],'endpoint_count':analysis['endpoint_count'],'tags':analysis['tags'],'detected_auth_type':analysis.get('detected_auth_type','none'),'auth_schemes':analysis.get('auth_schemes',[]),'base_url':(analysis.get('base_urls') or [None])[0]}
    if not row:
        row=IntegrationConnection(customer_id=company,provider=provider,category=payload.category,status='imported',environment='sandbox',capabilities=caps,settings=settings);db.add(row)
    else:
        row.status='imported';row.capabilities=caps;row.settings={**{k:v for k,v in (row.settings or {}).items() if k!='live_check'},**settings}
    db.commit();db.refresh(row);audit(db,'openapi_imported',{'provider':provider,'endpoint_count':analysis['endpoint_count']})
    return {'connection':public_connection(row),'analysis':analysis}
