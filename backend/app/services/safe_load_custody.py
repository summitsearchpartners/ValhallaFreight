"""Append-only custody state snapshots and retained dispatcher evidence versions."""
import hashlib,json,secrets
from pathlib import Path
from datetime import datetime
from sqlalchemy import event
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.safe_load_custody import SafeLoadCustodySnapshot
from app.core.config import settings
PHASE_ACTIONS={'broker_profile_contact_updated','onsite_photo_captured','hold_created','enabled','invitation_created','assignment_submitted','broker_approved','broker_contact_updated','scan_rejected','scan_matched','freight_released','photo_review_rejected','photo_review_completed','visual_comparison_rejected','arrival_photo_unreadable','cancelled','broker_authorized_release','in_transit'}
def digest(payload,previous):
    visible=json.loads(json.dumps(payload))
    for item in [visible.get('dispatcher_photo')]+list(visible.get('arrival_photos',{}).values()):
        if item:item.pop('path',None)
    canonical=json.dumps(visible,sort_keys=True,separators=(',',':'),ensure_ascii=True)
    return hashlib.sha256((previous+'\n'+canonical).encode()).hexdigest()
def capture(db,row,action,actor,detail):
    if action not in PHASE_ACTIONS:return
    from app.models import SafeLoadPhotoAttempt,Shipment,SafeLoadBrokerContact,SafeLoadPhotoExtraction,SafeLoadBackPhoto,SafeLoadReleaseReceipt
    pending=[s for s in db.new if isinstance(s,SafeLoadCustodySnapshot) and s.shipment_id==row.shipment_id]
    previous=pending[-1] if pending else db.query(SafeLoadCustodySnapshot).filter_by(shipment_id=row.shipment_id).order_by(SafeLoadCustodySnapshot.id.desc()).first()
    last=previous.payload if previous else {}
    evidence=last.get('dispatcher_photo') if last.get('revision')==row.revision else None
    if row.photo_path and not evidence:
        raw=Path(row.photo_path).read_bytes()
        root=Path(settings.document_storage_path)/'safe-load'/'custody';root.mkdir(parents=True,exist_ok=True)
        path=root/(secrets.token_hex(24)+'.enc');path.write_bytes(raw)
        evidence={'path':str(path),'sha256':hashlib.sha256(raw).hexdigest()}
    attempt=db.query(SafeLoadPhotoAttempt).filter_by(shipment_id=row.shipment_id,revision=row.revision).order_by(SafeLoadPhotoAttempt.id.desc()).first()
    extracted=db.get(SafeLoadPhotoExtraction,attempt.id) if attempt else None
    files={}
    if attempt:
        for kind,path in [('license',attempt.license_path),('vin',attempt.vin_path)]:
            files[kind]={'sha256':hashlib.sha256(Path(path).read_bytes()).hexdigest(),'attempt_id':attempt.id,'path':path}
    back=db.get(SafeLoadBackPhoto,attempt.id) if attempt else None
    if back:files['license_back']={'sha256':hashlib.sha256(Path(back.path).read_bytes()).hexdigest(),'attempt_id':attempt.id,'path':back.path}
    req=db.info.get('request');user=getattr(req.state,'auth_user',None) if req else None
    ship=db.get(Shipment,row.shipment_id);from app.services.safe_load_contacts import contact_for
    contact=contact_for(db,row)
    receipt=db.get(SafeLoadReleaseReceipt,row.shipment_id)
    payload={'confirmation_number':receipt.confirmation_number if receipt else None,'capture_metadata_declared_by_client':db.info.get('safe_load_capture_times'),'shipment_id':row.shipment_id,'customer_id':row.customer_id,'revision':row.revision,'action':action,'phase':row.status,'timestamp':datetime.utcnow().isoformat()+'Z','actor':{'label':actor,'user_id':getattr(user,'id',None),'name':getattr(user,'full_name',actor),'role':getattr(user,'role','carrier_dispatcher')},'detail':detail,'driver_name':row.driver_name,'license_issuer':row.issuing_state,'license_last4':row.license_last4,'license_expires':row.license_expires.isoformat() if row.license_expires else None,'vin':row.vin,'approved_by':row.approved_by,'verified_by':row.verified_by,'released_by':row.released_by,'released_at':row.released_at.isoformat() if row.released_at else None,'shipment_status':ship.status if ship else None,'dispatcher_photo':evidence,'arrival_photos':files,'verification_mode':db.info.get('safe_load_verification_mode'),'extracted_fields':extracted.summary if extracted else None,'attempt_status':attempt.status if attempt else None,'attempt_reasons':attempt.reasons if attempt else [],'broker_contact':contact}
    previous_digest=previous.digest if previous else ''
    db.add(SafeLoadCustodySnapshot(shipment_id=row.shipment_id,customer_id=row.customer_id,revision=row.revision,action=action,phase=row.status,payload=payload,previous_digest=previous_digest,digest=digest(payload,previous_digest)))
@event.listens_for(Session,'before_flush')
def protect(db,context,instances):
    if any(isinstance(x,SafeLoadCustodySnapshot) for x in db.dirty|db.deleted):raise HTTPException(409,'Custody snapshots are append-only')
    from app.models import SafeLoadCase
    request=db.info.get('request')
    if request and getattr(request.state,'auth_user',None):
        pending=[x for x in db.new if isinstance(x,SafeLoadCase)]
        if pending:db.info.setdefault('safe_load_initial_snapshots',[]).extend(pending)
@event.listens_for(Session,'after_flush_postexec')
def initial(db,context):
    from app.services.safe_load import log
    request=db.info.get('request');user=getattr(request.state,'auth_user',None) if request else None
    for row in db.info.pop('safe_load_initial_snapshots',[]):
        if user and row.shipment_id:log(db,row,'hold_created',user.email,'Safe Load hold created with the shipment.')

def public(snapshot):
    payload=json.loads(json.dumps(snapshot.payload))
    for item in [payload.get('dispatcher_photo')]+list(payload.get('arrival_photos',{}).values()):
        if item:item.pop('path',None)
    return {'id':snapshot.id,'payload':payload,'digest':snapshot.digest,'previous_digest':snapshot.previous_digest}
def verify(rows):
    previous='';issues=[];checked={}
    for s in rows:
        if s.previous_digest!=previous or s.digest!=digest(s.payload,s.previous_digest):issues.append(f'Snapshot {s.id} chain mismatch')
        for item in [s.payload.get('dispatcher_photo')]+list(s.payload.get('arrival_photos',{}).values()):
            if item:
                try:
                    if item['path'] not in checked:checked[item['path']]=hashlib.sha256(Path(item['path']).read_bytes()).hexdigest()
                    valid=checked[item['path']]==item['sha256']
                except OSError:valid=False
                if not valid:issues.append(f'Snapshot {s.id} evidence unavailable or altered')
        previous=s.digest
    return {'valid':not issues,'issues':issues,'count':len(rows),'head_digest':previous}

@event.listens_for(Session,'do_orm_execute')
def prevent_bulk_snapshot_change(state):
    if (state.is_update or state.is_delete) and getattr(getattr(state.statement,'table',None),'name',None)=='safe_load_custody_snapshots':raise HTTPException(409,'Custody snapshots are append-only')
