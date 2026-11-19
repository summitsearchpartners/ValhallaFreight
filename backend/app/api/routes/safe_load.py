import asyncio,json,secrets,re,io
from pathlib import Path
from datetime import datetime,timedelta
from fastapi import APIRouter,Depends,HTTPException,Request,Header,UploadFile,File,Form
from fastapi.responses import Response,StreamingResponse
from sqlalchemy.orm import Session,sessionmaker
from pydantic import BaseModel,Field
from app.api.deps import get_current_user,get_db
from app.models import Customer,Shipment,SafeLoadCase,SafeLoadEvent,TrackingEvent,SafeLoadBrokerContact,SafeLoadPhotoAttempt,SafeLoadCustodySnapshot,SafeLoadPhotoExtraction,SafeLoadBackPhoto,SafeLoadReleaseReceipt
from app.services import safe_load as service
from app.core.config import settings
from app.integrations.secrets import _fernet

router=APIRouter(prefix='/safe-load',tags=['Safe Load'])
ROLES={'admin','broker','broker_admin','manufacturer','manufacturer_admin','warehouse'}

def warehouse_company_ids(db, user):
    if user.role != 'warehouse':
        return None
    if not user.customer_id:
        raise HTTPException(403, 'Warehouse account has no manufacturer assignment')
    company = db.get(Customer, user.customer_id)
    if not company or company.manufacturer_id is not None:
        raise HTTPException(403, 'Warehouse must be linked to a parent manufacturer')
    return [company.id] + [child.id for child in db.query(Customer.id).filter(Customer.manufacturer_id == company.id).all()]

def access(request:Request,user=Depends(get_current_user),db:Session=Depends(get_db)):
    if user.role not in ROLES:raise HTTPException(403,'Safe Load workspace account required')
    if user.role == 'warehouse':
        allowed = warehouse_company_ids(db, user)
        sid = request.path_params.get('sid')
        if sid is not None:
            row = db.get(SafeLoadCase, int(sid))
            if row is None or row.customer_id not in allowed:
                raise HTTPException(404, 'Safe Load shipment not found')
        # The warehouse can perform arrival verification, not dispatch setup,
        # broker approvals, contact edits, evidence export or broker overrides.
        suffix = request.url.path.removeprefix('/api/v1/safe-load')
        blocked = ('/enable','/invite','/approve-assignment','/broker-contact',
                   '/broker-release','/custody/export','/extraction')
        if any(suffix.endswith(part) for part in blocked) or (
            '/custody/' in suffix and '/dispatcher-photo' in suffix
        ) or (suffix.endswith('/custody/export')):
            raise HTTPException(403, 'Warehouse cannot administer or override Safe Load')
    from app.services.muse_partner import has_access
    if user.role=='broker_admin' and has_access(db,user):db.info['safe_load_partner_request']=True
    return user

def broker(user,request):
    if user.role not in {'admin','broker','broker_admin'} or getattr(request.state,'support_company_id',None) is not None:
        raise HTTPException(403,'Broker approval required')

def view(db,row):
    ship=db.get(Shipment,row.shipment_id)
    from app.models import Carrier
    from sqlalchemy import select
    carrier_name=db.execute(select(Carrier.__table__.c.name).where(Carrier.__table__.c.id==ship.carrier_id)).scalar() if ship.carrier_id else None
    from app.services.safe_load_contacts import contact_for
    contact=contact_for(db,row)
    attempt=db.query(SafeLoadPhotoAttempt).filter_by(shipment_id=row.shipment_id).order_by(SafeLoadPhotoAttempt.id.desc()).first()
    extracted=db.get(SafeLoadPhotoExtraction,attempt.id) if attempt else None
    events=db.query(SafeLoadEvent).filter_by(shipment_id=row.shipment_id).order_by(SafeLoadEvent.id.desc()).limit(100).all()
    rejected=db.query(SafeLoadEvent).filter(SafeLoadEvent.shipment_id==row.shipment_id,SafeLoadEvent.action.in_(['scan_rejected','photo_review_rejected','visual_comparison_rejected','arrival_photo_unreadable'])).order_by(SafeLoadEvent.id.desc()).first()
    released=db.query(SafeLoadEvent).filter(SafeLoadEvent.shipment_id==row.shipment_id,SafeLoadEvent.action.in_(['broker_authorized_release','freight_released'])).order_by(SafeLoadEvent.id.desc()).first()
    receipt=db.get(SafeLoadReleaseReceipt,row.shipment_id)
    return {'confirmation_number':receipt.confirmation_number if receipt else None,'shipment_status':ship.status,'rejection_id':rejected.id if rejected else None,'release_method':'broker_authorized' if released and released.action=='broker_authorized_release' else 'warehouse_verified','release_actor':released.actor if released else None,'can_photo_submit':bool(row.photo_path and row.status in {'pending_broker_review','awaiting_verification','verified','rejected'}),'shipment_id':row.shipment_id,'shipment_number':ship.shipment_number,'customer_id':row.customer_id,
        'carrier_name':carrier_name,'origin':ship.origin,'destination':ship.destination,'status':('pending_broker_review' if row.status in {'awaiting_verification','verified'} and not row.approved_by else 'awaiting_verification' if row.status=='verified' and row.verified_until and row.verified_until<datetime.utcnow() else row.status),'revision':row.revision,
        'driver_name':row.driver_name,'license_expires':row.license_expires.date().isoformat() if row.license_expires else None,'license_last4':row.license_last4,'issuing_state':row.issuing_state,'vin':row.vin,
        'rejection_reason':rejected.detail if rejected and row.status=='rejected' else None,'broker_contact':contact,'photo_review':{'id':attempt.id,'status':attempt.status,'reasons':attempt.reasons,'revision':attempt.revision,'extraction':extracted.summary if extracted else None} if attempt else None,'has_photo':bool(row.photo_path),'approved_by':row.approved_by,'verified_until':row.verified_until,'released_at':row.released_at,'released_by':row.released_by,
        'events':[{'id':e.id,'action':e.action,'actor':e.actor,'detail':e.detail,'created_at':e.created_at} for e in events]}

@router.get('')
def queue(user=Depends(access),db:Session=Depends(get_db)):
    q=db.query(SafeLoadCase)
    if user.role=='warehouse':q=q.filter(SafeLoadCase.customer_id.in_(warehouse_company_ids(db,user)))
    return [view(db,row) for row in q.order_by(SafeLoadCase.updated_at.desc()).limit(300)]

@router.get('/events')
async def events(request:Request,user=Depends(access),db:Session=Depends(get_db)):
    factory=sessionmaker(bind=db.get_bind())
    async def stream():
        last=None
        for _ in range(55):
            if await request.is_disconnected():break
            with factory() as current:
                current.info['request']=request
                current.info['safe_load_partner_request']=db.info.get('safe_load_partner_request',False)
                q=current.query(SafeLoadCase)
                if user.role=='warehouse':q=q.filter(SafeLoadCase.customer_id.in_(warehouse_company_ids(current,user)))
                rows=q.order_by(SafeLoadCase.shipment_id).all()
                data=json.dumps([(r.shipment_id,r.status,r.revision,str(r.updated_at),bool(r.verified_until and r.verified_until<datetime.utcnow()),r.approved_by,r.verified_by) for r in rows])
            if data!=last:
                yield 'data: '+json.dumps({'changed':True})+'\n\n';last=data
            else:yield ': heartbeat\n\n'
            await asyncio.sleep(1)
    return StreamingResponse(stream(),media_type='text/event-stream',headers={'Cache-Control':'no-store','X-Accel-Buffering':'no'})

@router.post('/shipments/{sid}/enable')
def enable(sid:int,user=Depends(access),db:Session=Depends(get_db)):
    ship=db.get(Shipment,sid)
    if not ship:raise HTTPException(404,'Shipment not found')
    if ship.actual_pickup_at or ship.delivered_at or service.normalized(ship.status) not in service.PREFLIGHT:raise HTTPException(409,'Safe Load can be enabled only before pickup')
    row=db.get(SafeLoadCase,sid)
    if not row:
        row=SafeLoadCase(shipment_id=sid,customer_id=ship.customer_id,status='awaiting_assignment',revision=0);db.add(row);db.flush()
        service.log(db,row,'enabled',user.email,'Warehouse release hold enabled.');db.commit()
    return view(db,row)

@router.post('/shipments/{sid}/invite')
def invite(sid:int,request:Request,user=Depends(access),db:Session=Depends(get_db)):
    broker(user,request);row=service.case(db,sid,True)
    token=service.new_invite(db,row,user.email)
    return {'token':token,'expires_at':row.invite_expires,'path':'/safe-load/carrier#token='+token}

def carrier(db,token):
    if not token:raise HTTPException(401,'Carrier invitation required')
    row=db.query(SafeLoadCase).filter_by(invite_digest=service.digest(token)).with_for_update().first()
    if not row or not row.invite_expires or row.invite_expires<datetime.utcnow() or row.released_at or row.status=='cancelled':raise HTTPException(403,'Invitation expired or revoked')
    return row

@router.get('/carrier')
def carrier_info(x_safe_load_token:str|None=Header(None),db:Session=Depends(get_db)):
    row=carrier(db,x_safe_load_token);s=db.get(Shipment,row.shipment_id)
    return {'shipment_number':s.shipment_number,'origin_zip':s.origin.get('postal_code'),'destination_zip':s.destination.get('postal_code'),'status':row.status}

@router.post('/carrier/license-preview')
async def carrier_license_preview(photo:UploadFile=File(...),license_back_photo:UploadFile|None=File(None),x_safe_load_token:str|None=Header(None),db:Session=Depends(get_db)):
    # A valid, unexpired load-specific invitation is required; never persist
    # the uploaded image or extracted identity data during preview.
    carrier(db,x_safe_load_token)
    # The authorization lookup begins a SQLAlchemy transaction. Release its
    # connection before CPU-intensive OCR so parallel scans cannot exhaust
    # the production connection pool or leave idle-in-transaction sessions.
    db.rollback()
    db.close()
    raw=await photo.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise HTTPException(413,'License photo must be under 8 MB')
    from app.services.safe_load_images import normalize,license_evidence
    try:
        normalized=await asyncio.to_thread(normalize,raw)
        evidence=await asyncio.to_thread(license_evidence,normalized)
    except ValueError as e:raise HTTPException(422,str(e))
    # Use the same AAMVA PDF417 decoder as onsite ID-back verification.
    # Never combine identity fields from two different cards or from an
    # unverified barcode with conflicting front-image barcode evidence.
    if license_back_photo is not None:
        from app.services.safe_load_images import barcodes
        from app.services.safe_load import decode_license
        back=await license_back_photo.read(8*1024*1024+1)
        if len(back)>8*1024*1024:raise HTTPException(413,'License back photo must be under 8 MB')
        try:
            decoded=[]
            for code in await asyncio.to_thread(barcodes,back,True):
                try:decoded.append(decode_license(code))
                except ValueError:continue
            if not decoded:
                evidence={'fields':{},'source':'id_back_pdf417','errors':['License back PDF417 barcode could not be read. Retake the back photo or enter details manually.']}
            elif any(item!=decoded[0] for item in decoded):
                evidence={'fields':{},'source':'id_back_pdf417','errors':['Multiple different license barcodes detected. Review required.']}
            elif evidence['source']=='pdf417' and any(evidence['fields'].get(k)!=decoded[0].get(k) for k in ('DAQ','DAJ','DAC','DCS','DBA')):
                evidence={'fields':{},'source':'id_back_pdf417','errors':['Front and back license barcodes disagree. Review required.']}
            else:
                evidence={'fields':decoded[0],'source':'id_back_pdf417','errors':[]}
        except ValueError:
            evidence={'fields':{},'source':'id_back_pdf417','errors':['License back barcode could not be decoded. Review required.']}
    fields=evidence['fields']
    def expiration(value):
        if not value:return ''
        for fmt in ('%Y%m%d','%m%d%Y','%m/%d/%Y','%Y-%m-%d'):
            try:return datetime.strptime(value,fmt).date().isoformat()
            except ValueError:pass
        return ''
    name=' '.join(part for part in (fields.get('DAC',''),fields.get('DAD',''),fields.get('DCS','')) if part and part.upper() not in {'NONE','NMN','UNKNOWN','UNK'})
    return Response(json.dumps({'driver_name':name,'license_number':fields.get('DAQ',''),'issuing_state':fields.get('DAJ',''),'license_expires':expiration(fields.get('DBA','')),'source':evidence['source'],'warnings':evidence['errors'],'rotation_degrees':evidence.get('rotation_degrees',0)}),media_type='application/json',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@router.post('/carrier')
async def assignment(driver_name:str=Form(...),license_number:str=Form(...),issuing_state:str=Form(...),license_expires:str=Form(...),truck_vin:str=Form(...),photo:UploadFile=File(...),x_safe_load_token:str|None=Header(None),db:Session=Depends(get_db)):
    row=carrier(db,x_safe_load_token)
    try:
        name=driver_name.strip();state=issuing_state.strip().upper()
        if not 2<=len(name)<=180 or not re.fullmatch('[A-Z]{2}',state) or not re.fullmatch('[A-Z0-9 -]{3,40}',license_number.upper()):raise ValueError('Enter a driver name, license number and two-letter issuing state')
        expires=datetime.strptime(license_expires,'%Y-%m-%d')
        if expires.date()<datetime.utcnow().date():raise ValueError('Driver license is expired')
        vehicle=service.vin(truck_vin)
    except ValueError as e:raise HTTPException(422,str(e))
    raw=await photo.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise HTTPException(413,'License photo must be under 8 MB')
    from app.services.safe_load_orientation import normalize_license
    try:raw=await asyncio.to_thread(normalize_license,raw)
    except ValueError as e:raise HTTPException(422,str(e))
    root=Path(settings.document_storage_path)/'safe-load';root.mkdir(parents=True,exist_ok=True)
    path=root/(secrets.token_hex(24)+'.enc');path.write_bytes(_fernet().encrypt(raw))
    previous=row.photo_path
    row.driver_name=name;row.issuing_state=state;row.license_digest=service.license_key(license_number,state);row.license_last4=re.sub('[^A-Z0-9]','',license_number.upper())[-4:]
    row.license_expires=expires;row.vin=vehicle;row.photo_path=str(path);row.photo_type='image/jpeg'
    row.revision+=1;row.status='pending_broker_review';row.approved_by=None;row.verified_by=None;row.verified_until=None
    service.log(db,row,'assignment_submitted','Carrier dispatcher',f'Driver {name}; truck VIN {vehicle}. Broker review required.');db.commit()
    if previous:Path(previous).unlink(missing_ok=True)
    return {'status':row.status,'revision':row.revision}

@router.get('/shipments/{sid}/photo')
def photo(sid:int,user=Depends(access),db:Session=Depends(get_db)):
    row=service.case(db,sid)
    if not row.photo_path:raise HTTPException(404,'No license photo submitted')
    service.log(db,row,'photo_viewed',user.email,'Authorized user viewed the submitted license photo.');db.commit()
    from app.services.safe_load_orientation import normalize_license
    try:raw=normalize_license(_fernet().decrypt(Path(row.photo_path).read_bytes()))
    except Exception:raise HTTPException(422,'Stored license image cannot be displayed. Ask the dispatcher to upload a new clear photo.')
    return Response(raw,media_type='image/jpeg',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

class Revision(BaseModel):
    revision:int=Field(ge=0)
class Review(Revision):
    broker_phone:str=Field(default='',max_length=60)
    reason:str=Field(min_length=10,max_length=1000)
class Scan(Revision):
    license_barcode:str=Field(max_length=12000)
    vin_barcode:str=Field(max_length=200)
    physical_id_matches_photo:bool=False

@router.post('/shipments/{sid}/approve-assignment')
def approve(sid:int,p:Review,request:Request,user=Depends(access),db:Session=Depends(get_db)):
    broker(user,request);row=service.case(db,sid,True)
    if len(p.reason.strip())<10:raise HTTPException(422,'Record how the driver was independently verified')
    if row.revision!=p.revision or (row.status not in {'pending_broker_review','rejected'} and (row.approved_by or row.status not in {'awaiting_verification','verified'})) or not row.photo_path:raise HTTPException(409,'Refresh the current driver assignment before approval')
    if p.broker_phone:save_contact(db,row,user,p.broker_phone)
    row.status='awaiting_verification';row.approved_by=user.id;row.verified_by=None;row.verified_until=None
    service.log(db,row,'broker_approved',user.email,p.reason.strip());db.commit();return view(db,row)

@router.post('/shipments/{sid}/scan')
def scan(sid:int,p:Scan,user=Depends(access),db:Session=Depends(get_db)):
    row=service.case(db,sid,True)
    if row.revision!=p.revision or (not db.info.get('safe_load_initial_photo_match') and (row.status not in {'awaiting_verification','verified','rejected'} or not row.approved_by)):raise HTTPException(409,'A current broker-approved driver assignment is required')
    reasons=[]
    try:
        decoded=service.decode_license(p.license_barcode)
        if not hmac_compare(service.license_key(decoded['DAQ'],decoded['DAJ']),row.license_digest):reasons.append('Driver license does not match the approved assignment')
        first=decoded.get('DAC','');last=decoded.get('DCS','')
        norm=lambda s:re.sub('[^A-Z]','',s.upper())
        name_tokens=re.findall('[A-Z]+',row.driver_name.upper());first_tokens=re.findall('[A-Z]+',first.upper())
        if not first or not last or name_tokens[:len(first_tokens)]!=first_tokens or not norm(row.driver_name).endswith(norm(last)):reasons.append('Driver name in the license scan does not match')
        if not decoded.get('DBA'):raise ValueError('Expiration missing')
        if decoded.get('DBA'):
            expiry=datetime.strptime(decoded['DBA'],'%Y%m%d' if decoded['DBA'].startswith(('19','20')) else '%m%d%Y')
            if expiry.date()<datetime.utcnow().date():reasons.append('Scanned driver license is expired')
            if row.license_expires and expiry.date()!=row.license_expires.date():reasons.append('License expiration does not match the approved document')
    except ValueError:reasons.append('License barcode is unreadable or unsupported')
    try:
        if service.vin(p.vin_barcode)!=row.vin:reasons.append('Truck VIN does not match the approved assignment')
    except ValueError:reasons.append('VIN barcode is invalid')
    if not row.license_expires or row.license_expires.date()<datetime.utcnow().date():reasons.append('Submitted license is expired')
    if not p.physical_id_matches_photo:reasons.append('Warehouse physical ID and photo comparison is required')
    if reasons:
        row.status='rejected';row.approved_by=None;row.verified_by=None;row.verified_until=None
        text='; '.join(reasons)+'. Freight release remains blocked.'
        db.info['safe_load_scan_reasons']=reasons
        service.log(db,row,'scan_rejected',user.email,text);service.notify(db,row,text)
    else:
        row.status='verified';row.verified_by=user.id;row.verified_until=datetime.utcnow()+timedelta(minutes=10)
        service.log(db,row,'scan_matched',user.email,'License and VIN matched; physical ID/photo comparison attested. Release is available for 10 minutes to this operator.')
    if not db.info.get('safe_load_photo_transaction'):db.commit()
    return view(db,row)

def hmac_compare(a,b):
    import hmac
    return hmac.compare_digest(a,b or '')

@router.post('/shipments/{sid}/release')
def release(sid:int,p:Revision,user=Depends(access),db:Session=Depends(get_db)):
    row=service.case(db,sid,True)
    if row.status=='released':return view(db,row)
    if row.revision!=p.revision or row.status!='verified' or row.verified_by!=user.id or not row.verified_until or row.verified_until<datetime.utcnow():raise HTTPException(409,'Release blocked. This operator must rescan the current driver license and VIN.')
    if db.get(Shipment,sid).status in {'cancelled','canceled'}:raise HTTPException(409,'Cancelled freight cannot be released')
    row.status='released';row.released_at=datetime.utcnow();row.released_by=user.id;row.invite_digest=None
    ship=db.get(Shipment,sid);ship.status='picked_up';ship.actual_pickup_at=datetime.utcnow();db.info['safe_load_release']=sid
    db.add(TrackingEvent(shipment_id=sid,code='SAFELOAD_RELEASED',status='PICKED_UP',description='Warehouse Safe Load identity/VIN check completed and freight released.',event_time=datetime.utcnow(),source='safe_load'))
    service.release_receipt(db,row,user,'automatic_photo_qa' if db.info.get('safe_load_photo_transaction') else 'barcode_check')
    service.log(db,row,'freight_released',user.email,f'Warehouse released freight to {row.driver_name}, truck VIN {row.vin}.')
    if not db.info.get('safe_load_photo_transaction'):db.commit()
    return view(db,row)

class BrokerContactIn(BaseModel):
    phone:str=Field(min_length=7,max_length=60)

def save_contact(db,row,user,phone):
    if not re.fullmatch(r'[+0-9(). xX-]{7,60}',phone) or len(re.sub(r'\D','',phone))<7:raise HTTPException(422,'Enter a callable broker phone number, including area code')
    from app.services.safe_load_contacts import contact_for
    contact=contact_for(db,row)
    if not contact:
        contact=SafeLoadBrokerContact(shipment_id=row.shipment_id,customer_id=row.customer_id,broker_name=user.full_name,phone=phone.strip());db.add(contact)
    else:contact.phone=phone.strip();contact.broker_name=user.full_name
    service.log(db,row,'broker_contact_updated',user.email,'Warehouse escalation contact updated.')

@router.put('/shipments/{sid}/broker-contact',deprecated=True)
def broker_contact(sid:int,p:BrokerContactIn,request:Request,user=Depends(access),db:Session=Depends(get_db)):
    broker(user,request);row=service.case(db,sid,True);save_contact(db,row,user,p.phone);db.commit();return view(db,row)

@router.get('/shipments/{sid}/photo-data')
def photo_data(sid:int,user=Depends(access),db:Session=Depends(get_db)):
    import base64
    result=photo(sid,user,db)
    return Response(json.dumps({'data_uri':'data:image/jpeg;base64,'+base64.b64encode(result.body).decode()}),media_type='application/json',headers={'Cache-Control':'no-store'})

@router.post('/shipments/{sid}/photo-review')
async def photo_review(sid:int,revision:int=Form(...),physical_id_matches_photo:bool=Form(False),license_photo:UploadFile=File(...),vin_photo:UploadFile=File(...),capture_source:str=Form('desktop_upload',max_length=40),license_captured_at:str=Form('',max_length=60),vin_captured_at:str=Form('',max_length=60),license_back_photo:UploadFile|None=File(None),license_barcode:str=Form('',max_length=8192),vin_barcode:str=Form('',max_length=200),upload_id:str=Form('',pattern='^([a-f0-9]{32})?$'),user=Depends(access),db:Session=Depends(get_db)):
    from app.services import safe_load_images as images
    from app.services.safe_load_progress import update
    progress=lambda n,label:update(user.id,sid,upload_id,n,label)
    row=service.case(db,sid,True)
    progress(10,'Photos received; checking assignment and image files')
    if row.status=='released':return view(db,row)
    if row.revision!=revision or row.status not in {'pending_broker_review','awaiting_verification','verified','rejected'} or not row.photo_path:raise HTTPException(409,'Wait for a complete dispatcher assignment and refresh before submitting onsite photos')
    awaiting_broker=row.status=='rejected'
    if capture_source not in {'native_camera','desktop_upload'}:raise HTTPException(422,'Unsupported capture source')
    for value in (license_captured_at,vin_captured_at):
        if value:
            try:datetime.fromisoformat(value.replace('Z','+00:00'))
            except ValueError:raise HTTPException(422,'Invalid declared capture time')
    db.info['safe_load_capture_times']={'source_declared':capture_source,'license_device_time':license_captured_at or None,'vin_device_time':vin_captured_at or None}
    from app.services.safe_load_contacts import contact_for
    from app.services.safe_load_assessment import assess
    import json
    contact=contact_for(db,row)
    files=[]
    for upload in [license_photo,vin_photo]:
        raw=await upload.read(8*1024*1024+1)
        if len(raw)>8*1024*1024:raise HTTPException(413,'Each onsite photo must be under 8 MB')
        try:
            from app.services.safe_load_orientation import normalize_license
            files.append(await asyncio.to_thread(normalize_license,raw,True) if upload is license_photo else images.normalize(raw,allow_blank=True))
        except ValueError as e:
            row.status='rejected';row.approved_by=None;row.verified_by=None;row.verified_until=None
            detail=str(e)+' Freight remains held; submit a supported onsite photo for broker review.'
            service.log(db,row,'arrival_photo_unreadable',user.email,detail);service.notify(db,row,detail);db.commit()
            return view(db,row)
    back_raw=None
    if license_back_photo is not None:
        raw=await license_back_photo.read(8*1024*1024+1)
        if len(raw)>8*1024*1024:raise HTTPException(413,'ID back photo must be under 8 MB')
        try:back_raw=await asyncio.to_thread(normalize_license,raw,True)
        except ValueError as e:raise HTTPException(422,'ID back photo: '+str(e))
    progress(25,'Image checks complete; extracting driver license data')
    if license_barcode:
        # Live scan supplies structured data. Only decode the photo's barcode to
        # detect conflicting cards; do not spend time guessing its printed layout.
        try:
            codes=await asyncio.to_thread(images.barcodes,files[0],True)
            parsed=[service.decode_license(code) for code in codes]
            evidence={'fields':parsed[0] if parsed else {},'source':'pdf417' if parsed else 'photo_evidence','errors':[]}
            if parsed and any(item!=parsed[0] for item in parsed):evidence['errors'].append('Multiple different licenses found in the onsite photo')
        except ValueError as e:evidence={'fields':{},'source':'photo_evidence','errors':[str(e)]}
    else:
        try:evidence=await asyncio.to_thread(images.license_evidence,files[0])
        except ValueError as e:evidence={'fields':{},'source':'local_reader','errors':[str(e)]}
    if license_barcode:
        try:
            scanned=service.decode_license(license_barcode)
            required=['DAQ','DAJ','DAC','DCS','DBA']
            missing=[k for k in required if not scanned.get(k)]
            conflict=evidence['source']=='pdf417' and any(evidence['fields'].get(k)!=scanned.get(k) for k in required)
            evidence={'fields':scanned,'source':'onsite_pdf417_scan','errors':evidence['errors']+(['Photo barcode and live ID scan disagree'] if conflict else [])+(['Scanned ID barcode is missing required identity fields'] if missing else [])}
        except ValueError as e:evidence['errors'].append(str(e))
    if back_raw is not None:
        errors=[];decoded=[]
        for code in await asyncio.to_thread(images.barcodes,back_raw,True):
            try:decoded.append(service.decode_license(code))
            except ValueError:continue
        if not decoded:errors.append('ID back barcode could not be read. Retake the back photo with the full barcode in focus and without glare.')
        elif any(v!=decoded[0] for v in decoded):errors.append('Multiple different ID barcodes were found in the back photo')
        else:
            fields=decoded[0]
            if not all(fields.get(k) for k in ['DAQ','DAJ','DAC','DCS','DBA']):errors.append('ID back barcode is missing required identity fields')
            if evidence['source'] in {'pdf417','onsite_pdf417_scan'} and any(evidence['fields'].get(k)!=fields.get(k) for k in ['DAQ','DAJ','DAC','DCS','DBA']):errors.append('Front/scan and back ID barcode data disagree')
            evidence={'fields':fields,'source':'id_back_pdf417','errors':errors}
        if errors:evidence['errors']=list(dict.fromkeys(evidence['errors']+errors))
    progress(55,'License extraction complete; reading truck VIN')
    vehicle='';vin_errors=[];vin_reader='photo_unreadable'
    try:
        vin_evidence=await asyncio.to_thread(images.vehicle_evidence,files[1]);vehicle=vin_evidence['vin'];vin_reader=vin_evidence['reader']
    except ValueError as e:vin_errors.append(str(e))
    if vin_barcode:
        try:
            scanned_vin=service.vin(vin_barcode)
            # A legible image/scan contradiction remains a rejection.
            if vehicle and vehicle!=scanned_vin:vin_errors.append('Truck VIN photo and onsite barcode scan disagree')
            else:vehicle=scanned_vin;vin_errors=[];vin_reader='onsite_barcode_scan'
        except ValueError as e:vin_errors.append(str(e))
    progress(75,'Extraction complete; comparing assignment, identity, expiry and VIN')
    reasons,summary=assess(row,evidence,vehicle,vin_errors)
    summary['has_back_photo']=back_raw is not None
    summary['vin_reader']=vin_reader
    summary['scan_data_client_declared']=bool(license_barcode or vin_barcode)
    if not contact:reasons.append('Broker Admin must configure the shared Safe Load call contact in My Profile before release')
    if awaiting_broker and not reasons:reasons.append('An earlier rejection requires broker verification and authorization. Current onsite photos are retained for review.')
    summary['decision']='broker_review' if reasons else 'matched'
    root=Path(settings.document_storage_path)/'safe-load';root.mkdir(parents=True,exist_ok=True)
    paths=[]
    progress(90,'Saving evidence, decision and chain of custody')
    try:
        for raw in files+([back_raw] if back_raw is not None else []):
            path=root/(secrets.token_hex(24)+'.enc');path.write_bytes(_fernet().encrypt(raw));paths.append(path)
        attempt=SafeLoadPhotoAttempt(shipment_id=sid,customer_id=row.customer_id,revision=revision,operator_id=user.id,license_path=str(paths[0]),vin_path=str(paths[1]),status='reviewing',reasons=reasons)
        db.add(attempt);db.flush()
        if back_raw is not None:db.add(SafeLoadBackPhoto(attempt_id=attempt.id,customer_id=row.customer_id,path=str(paths[2])));db.flush()
        fields=evidence['fields']
        full={'license_number':fields.get('DAQ',''),'first_name':fields.get('DAC',''),'last_name':fields.get('DCS',''),'issuing_state':fields.get('DAJ',''),'expires_at':summary['expires_at'],'vin':vehicle,'reader':evidence['source']}
        db.add(SafeLoadPhotoExtraction(attempt_id=attempt.id,customer_id=row.customer_id,summary=summary,encrypted_data=_fernet().encrypt(json.dumps(full).encode()).decode()));db.flush()
        db.info['safe_load_photo_transaction']=True
        db.info['safe_load_verification_mode']='automated_photo_qa'
        if reasons:
            row.status='rejected';row.approved_by=None;row.verified_by=None;row.verified_until=None
            detail='; '.join(reasons)+'. Freight release blocked. Broker review required.'
            service.log(db,row,'photo_review_rejected',user.email,detail);service.notify(db,row,detail)
        else:
            row.status='verified';row.verified_by=user.id;row.verified_until=datetime.utcnow()+timedelta(minutes=10)
            detail='Server automatically matched extracted onsite license identity, driver name, valid expiration and VIN. No warehouse visual attestation was requested or recorded.'
            if summary['renewal_accepted']:detail+=' Valid renewed expiration accepted with unchanged license identity and driver name.'
            service.log(db,row,'scan_matched',user.email,detail)
            release(sid,Revision(revision=revision),user,db)
            ship=db.get(Shipment,sid);ship.status='in_transit'
            db.add(TrackingEvent(shipment_id=sid,code='SAFELOAD_TRANSIT',status='IN_TRANSIT',description='Automated onsite photo data checks passed; released for transit.',event_time=datetime.utcnow(),source='safe_load'))
            service.log(db,row,'in_transit',user.email,'Automated onsite ID/VIN data verification passed; freight released for transit.')
        attempt.status='confirmed' if row.status=='released' else 'rejected'
        db.flush()
        service.log(db,row,'photo_review_completed',user.email,f'Onsite photo attempt {attempt.id}: {attempt.status}. Server OCR/barcode field QA; no warehouse identity-comparison checkbox.')
        db.commit();progress(100,'QA complete: clear for transit' if row.status=='released' else 'QA complete: rejected / hold remains');return view(db,row)
    except Exception:
        db.rollback()
        for path in paths:path.unlink(missing_ok=True)
        raise
    finally:
        db.info.pop('safe_load_photo_transaction',None)
        db.info.pop('safe_load_verification_mode',None)
        db.info.pop('safe_load_initial_photo_match',None)

@router.post('/shipments/{sid}/reject-arrival')
def reject_arrival(sid:int,p:Revision,user=Depends(access),db:Session=Depends(get_db)):
    row=service.case(db,sid,True)
    if row.revision!=p.revision or row.status in {'released','cancelled'}:raise HTTPException(409,'Refresh the current unreleased shipment')
    row.status='rejected';row.approved_by=None;row.verified_by=None;row.verified_until=None
    detail='Warehouse reports the arriving person or physical ID does not match the dispatcher photo. Do not release; call the broker.'
    service.log(db,row,'visual_comparison_rejected',user.email,detail);service.notify(db,row,detail);db.commit();return view(db,row)

class BrokerRelease(Revision):
    rejection_id:int=Field(gt=0)
    reason:str=Field(min_length=20,max_length=2000)
    driver_confirmed:bool=False
    vehicle_confirmed:bool=False
    evidence_reviewed:bool=False
    reissued_license_reviewed:bool=False

@router.post('/shipments/{sid}/broker-release')
def broker_release(sid:int,p:BrokerRelease,request:Request,user=Depends(access),db:Session=Depends(get_db)):
    broker(user,request);row=service.case(db,sid,True)
    if row.status!='rejected' or row.revision!=p.revision:raise HTTPException(409,'Only the current rejected assignment can be authorized. Refresh this shipment.')
    current=view(db,row)
    if current['rejection_id']!=p.rejection_id:raise HTTPException(409,'A newer rejection was recorded. Review the latest evidence first.')
    if not all([p.driver_confirmed,p.vehicle_confirmed,p.evidence_reviewed]) or len(p.reason.strip())<20:raise HTTPException(422,'Confirm the driver, truck VIN and reviewed evidence; record how you independently verified them')
    attempt=db.query(SafeLoadPhotoAttempt).filter_by(shipment_id=sid,revision=row.revision).order_by(SafeLoadPhotoAttempt.id.desc()).first()
    if not attempt or not Path(attempt.license_path).is_file() or not Path(attempt.vin_path).is_file():raise HTTPException(409,'Both onsite arrival photos must be submitted for the current assignment before broker authorization')
    extraction=db.get(SafeLoadPhotoExtraction,attempt.id)
    if extraction and extraction.summary.get('requires_license_review') and not p.reissued_license_reviewed:raise HTTPException(422,'Acknowledge that you reviewed the renewed/reissued license before authorizing release')
    from app.services.safe_load_contacts import contact_for
    if not contact_for(db,row):raise HTTPException(409,'Configure the shared Safe Load contact in Broker Admin My Profile first')
    ship=db.get(Shipment,sid)
    if service.normalized(ship.status) in {'cancelled','canceled','delivered'}:raise HTTPException(409,'This shipment cannot be released')
    row.status='released';row.approved_by=user.id;row.released_by=user.id;row.released_at=datetime.utcnow();row.verified_by=None;row.verified_until=None;row.invite_digest=None
    db.info['safe_load_release']=sid;ship.status='in_transit';ship.actual_pickup_at=ship.actual_pickup_at or datetime.utcnow()
    db.add(TrackingEvent(shipment_id=sid,code='SAFELOAD_BROKER_AUTHORIZED',status='IN_TRANSIT',description='Broker independently verified the rejected arrival and authorized release; see Safe Load custody record.',event_time=datetime.utcnow(),source='safe_load'))
    service.release_receipt(db,row,user,'broker_authorized')
    service.log(db,row,'broker_authorized_release',user.email,f'Manual broker authorization after rejection {p.rejection_id}, evidence attempt {attempt.id}. Renewed/reissued license reviewed: {p.reissued_license_reviewed}. Independent verification: {p.reason.strip()}')
    from app.models import OperationalNotification
    for n in db.query(OperationalNotification).filter_by(shipment_id=sid,notification_type='safe_load').all():n.status='read';n.read_at=datetime.utcnow()
    db.commit();return view(db,row)

@router.get('/shipments/{sid}/custody')
def custody(sid:int,user=Depends(access),db:Session=Depends(get_db)):
    from app.services.safe_load_custody import public,verify
    service.case(db,sid)
    rows=db.query(SafeLoadCustodySnapshot).filter_by(shipment_id=sid).order_by(SafeLoadCustodySnapshot.id).all()
    return {'shipment_id':sid,'integrity':verify(rows),'snapshots':[public(s) for s in rows],'history_note':'Snapshots begin with v0.19.5. Earlier activity remains in the event log; historical snapshots are not fabricated.'}

@router.get('/shipments/{sid}/custody/export')
def custody_export(sid:int,user=Depends(access),db:Session=Depends(get_db)):
    result=custody(sid,user,db)
    service.log(db,service.case(db,sid),'custody_exported',user.email,'Authorized export of the custody chain.');db.commit()
    return Response(json.dumps(result,indent=2),media_type='application/json',headers={'Content-Disposition':f'attachment; filename=SafeLoad-{sid}-custody.json','Cache-Control':'no-store'})

@router.get('/shipments/{sid}/custody/{snapshot_id}/dispatcher-photo')
def custody_dispatcher_photo(sid:int,snapshot_id:int,user=Depends(access),db:Session=Depends(get_db)):
    service.case(db,sid)
    record=db.query(SafeLoadCustodySnapshot).filter_by(id=snapshot_id,shipment_id=sid).first()
    item=record.payload.get('dispatcher_photo') if record else None
    if not item:raise HTTPException(404,'No dispatcher image in this snapshot')
    from app.services.safe_load_images import normalize
    raw=normalize(_fernet().decrypt(Path(item['path']).read_bytes()))
    service.log(db,service.case(db,sid),'custody_photo_viewed',user.email,f'Viewed dispatcher evidence snapshot {snapshot_id}.');db.commit()
    return Response(raw,media_type='image/jpeg',headers={'Cache-Control':'no-store'})

class OnsiteCapture(Revision):
    kind:str=Field(pattern='^(license|license_back|vin)$')
    captured_at:datetime

@router.post('/shipments/{sid}/capture-event')
def capture_event(sid:int,p:OnsiteCapture,user=Depends(access),db:Session=Depends(get_db)):
    row=service.case(db,sid,True)
    if row.revision!=p.revision or row.status in {'released','cancelled'}:raise HTTPException(409,'The assignment changed; refresh and retake the onsite photo')
    db.info['safe_load_capture_times']={'source_declared':'native_camera','kind':p.kind,'device_time':p.captured_at.isoformat()}
    service.log(db,row,'onsite_photo_captured',user.email,f'Operator reported onsite {p.kind} camera capture. Device-declared time: {p.captured_at.isoformat()}. Image evidence is attached on submission.')
    db.commit();return {'ok':True}

@router.get('/shipments/{sid}/attempts')
def photo_attempts(sid:int,user=Depends(access),db:Session=Depends(get_db)):
    service.case(db,sid)
    result=[]
    for attempt in db.query(SafeLoadPhotoAttempt).filter_by(shipment_id=sid).order_by(SafeLoadPhotoAttempt.id.desc()).all():
        extracted=db.get(SafeLoadPhotoExtraction,attempt.id)
        result.append({'id':attempt.id,'revision':attempt.revision,'status':attempt.status,'reasons':attempt.reasons,'operator_id':attempt.operator_id,'created_at':attempt.created_at,'has_back_photo':bool(db.get(SafeLoadBackPhoto,attempt.id)),'extraction':extracted.summary if extracted else None})
    return result

@router.get('/shipments/{sid}/attempts/{attempt_id}/extraction')
def extraction_details(sid:int,attempt_id:int,request:Request,user=Depends(access),db:Session=Depends(get_db)):
    broker(user,request);row=service.case(db,sid)
    attempt=db.query(SafeLoadPhotoAttempt).filter_by(shipment_id=sid,id=attempt_id).first()
    if not attempt:raise HTTPException(404,'Onsite evidence not found')
    extracted=db.get(SafeLoadPhotoExtraction,attempt.id)
    if not extracted:raise HTTPException(404,'This earlier attempt has no saved extraction data; review its photos')
    service.log(db,row,'extraction_viewed',user.email,f'Authorized broker viewed extracted identity fields for onsite attempt {attempt_id}.');db.commit()
    return Response(_fernet().decrypt(extracted.encrypted_data.encode()),media_type='application/json',headers={'Cache-Control':'no-store'})

@router.get('/shipments/{sid}/attempts/{attempt_id}/{kind}')
def arrival_photo(sid:int,attempt_id:int,kind:str,user=Depends(access),db:Session=Depends(get_db),upright:bool=False):
    service.case(db,sid)
    attempt=db.query(SafeLoadPhotoAttempt).filter_by(id=attempt_id,shipment_id=sid).first()
    if not attempt or kind not in {'license','vin','license-back'}:raise HTTPException(404,'Photo not found')
    back=db.get(SafeLoadBackPhoto,attempt.id) if kind=='license-back' else None
    if kind=='license-back' and not back:raise HTTPException(404,'ID back photo not found')
    path=back.path if back else attempt.license_path if kind=='license' else attempt.vin_path
    service.log(db,service.case(db,sid),'arrival_photo_viewed',user.email,f'Authorized review of arrival {kind} photo, attempt {attempt_id}.');db.commit()
    raw=_fernet().decrypt(Path(path).read_bytes())
    if upright and kind in {'license','license-back'}:
        from app.services.safe_load_orientation import upright as orient
        raw=orient(raw)
    return Response(raw,media_type='image/jpeg',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})

@router.get('/shipments/{sid}/attempts/{attempt_id}/{kind}/photo-data')
def arrival_photo_data(sid:int,attempt_id:int,kind:str,user=Depends(access),db:Session=Depends(get_db)):
    import base64
    # Reuse exactly the binary endpoint's tenant authorization, encrypted read
    # and custody-view event. The existing broker image endpoint is unchanged.
    result=arrival_photo(sid,attempt_id,kind,user,db,upright=True)
    attempt=db.get(SafeLoadPhotoAttempt,attempt_id)
    body={'shipment_id':sid,'attempt_id':attempt_id,'revision':attempt.revision,'kind':kind,'data_uri':'data:image/jpeg;base64,'+base64.b64encode(result.body).decode('ascii')}
    return Response(json.dumps(body),media_type='application/json',headers={'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'})




class BarcodePreview(BaseModel):
    revision:int
    barcode:str=Field(min_length=1,max_length=8192)

@router.post('/shipments/{sid}/license-barcode/preview')
def license_preview(sid:int,p:BarcodePreview,user=Depends(access),db:Session=Depends(get_db)):
    row=service.case(db,sid)
    if row.revision!=p.revision or row.status in {'released','cancelled'}:raise HTTPException(409,'Assignment changed or closed; refresh before scanning')
    try:fields=service.decode_license(p.barcode)
    except ValueError as e:raise HTTPException(422,str(e))
    def date(value):
        if not value:return None
        try:return datetime.strptime(value,'%Y%m%d' if value.startswith(('19','20')) else '%m%d%Y').date().isoformat()
        except ValueError:return None
    # DOB and raw barcode are preview-only; never logged or stored in evidence summaries.
    return Response(json.dumps({'first_name':fields.get('DAC',''),'last_name':fields.get('DCS',''),'middle_name':fields.get('DAD','') if fields.get('DAD','').upper() not in {'NONE','NMN','UNKNOWN','UNK'} else '','license_last4':fields['DAQ'][-4:],'issuing_state':fields['DAJ'],'expires_at':date(fields.get('DBA','')),'date_of_birth':date(fields.get('DBB','')),'complete':all(fields.get(k) for k in ['DAQ','DAJ','DAC','DCS','DBA'])}),media_type='application/json',headers={'Cache-Control':'no-store'})

@router.get('/shipments/{sid}/photo-progress/{upload_id}')
def photo_progress(sid:int,upload_id:str,user=Depends(access),db:Session=Depends(get_db)):
    service.case(db,sid)
    if not re.fullmatch('[a-f0-9]{32}',upload_id):raise HTTPException(422,'Invalid upload identifier')
    from app.services.safe_load_progress import read
    return Response(json.dumps(read(user.id,sid,upload_id)),media_type='application/json',headers={'Cache-Control':'no-store'})

async def camera_frame(sid,revision,frame,user,db):
    row=service.case(db,sid)
    if row.revision!=revision or row.status in {'released','cancelled'}:raise HTTPException(409,'Assignment changed or closed. Refresh and reopen the camera.')
    raw=await frame.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise HTTPException(413,'Camera frame exceeds 8 MB; choose a smaller camera resolution')
    from app.services.safe_load_images import normalize
    try:return normalize(raw,allow_blank=True)
    except ValueError as e:raise HTTPException(422,str(e))

@router.post('/shipments/{sid}/capture-readiness')
async def capture_readiness(sid:int,revision:int=Form(...),frame:UploadFile=File(...),user=Depends(access),db:Session=Depends(get_db)):
    raw=await camera_frame(sid,revision,frame,user,db)
    from app.services.safe_load_camera import document_readiness
    try:result=await asyncio.to_thread(document_readiness,raw)
    except ImportError:raise HTTPException(503,'Auto-capture checker unavailable. Use Take Photo; ask the administrator to rebuild the backend image.')
    except ValueError as e:raise HTTPException(422,str(e))
    return Response(json.dumps(result),media_type='application/json',headers={'Cache-Control':'no-store'})

@router.post('/shipments/{sid}/barcode-frame')
async def barcode_frame(sid:int,revision:int=Form(...),kind:str=Form(...,pattern='^(license|license_back|vin)$'),frame:UploadFile=File(...),user=Depends(access),db:Session=Depends(get_db)):
    raw=await camera_frame(sid,revision,frame,user,db)
    from app.services.safe_load_images import barcodes
    codes=await asyncio.to_thread(barcodes,raw,kind=='license')
    valid={}
    for code in codes:
        try:
            value=service.decode_license(code) if kind=='license' else service.vin(code)
            key=json.dumps(value,sort_keys=True)
            valid[key]=(code,value)
        except ValueError:continue
    if not valid:raise HTTPException(422,'No readable PDF417 ID barcode' if kind=='license' else 'No readable 17-character VIN barcode. Fill the guide, focus and remove glare.')
    if len(valid)!=1:raise HTTPException(422,'Multiple different barcodes detected. Show only the current ID or VIN label.')
    code,value=next(iter(valid.values()))
    if kind=='license':
        result=license_preview(sid,BarcodePreview(revision=revision,barcode=code),user,db)
        data=json.loads(result.body)
        if not data['complete']:raise HTTPException(422,'ID barcode is incomplete; scan the full PDF417 on the current license')
        data['barcode']=code
    else:data={'barcode':value,'vin':value}
    return Response(json.dumps(data),media_type='application/json',headers={'Cache-Control':'no-store'})

@router.post('/shipments/{sid}/vin-barcode/preview')
def vin_preview(sid:int,p:BarcodePreview,user=Depends(access),db:Session=Depends(get_db)):
    row=service.case(db,sid)
    if row.revision!=p.revision or row.status in {'released','cancelled'}:raise HTTPException(409,'Assignment changed or closed; refresh before scanning')
    try:value=service.vin(p.barcode)
    except ValueError as e:raise HTTPException(422,str(e))
    return Response(json.dumps({'barcode':value,'vin':value}),media_type='application/json',headers={'Cache-Control':'no-store'})

@router.get('/capture-features')
def capture_features(user=Depends(access)):
    return {'id_back_photo':True,'version':'0.19.16'}
