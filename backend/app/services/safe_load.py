"""Fail-closed warehouse release. Barcode matching is not government identity validation."""
import hashlib,hmac,re,secrets
from datetime import datetime,timedelta
from fastapi import HTTPException
from sqlalchemy import event,select,inspect
from sqlalchemy.orm import Session
from app.models.safe_load import SafeLoadCase,SafeLoadEvent
from app.models import Shipment,OperationalNotification,TrackingEvent
from app.integrations.secrets import _fernet
from app.core.config import settings

PREFLIGHT={'booked','pickup_requested','pending','scheduled','quoted','selected','cancelled','canceled','created','unassigned','hold'}
def normalized(value):return re.sub('[^a-z0-9]+','_',str(value or 'booked').lower()).strip('_')

BLOCKED={'picked_up','in_transit','delivered','dispatched','out_for_delivery','at_destination_terminal'}

def digest(value):
    key=(settings.integration_secret_key or settings.jwt_secret_key).encode()
    return hmac.new(key,value.encode(),hashlib.sha256).hexdigest()

def license_key(number,state):return digest(re.sub('[^A-Z0-9]','',number.upper())+'|'+state.strip().upper())

def vin(value):
    value=re.sub(r'^\][A-Z0-9]{2}', '', value.strip().upper())
    if value.startswith('*') and value.endswith('*'):value=value[1:-1]
    value=re.sub(r'^VIN[:\s]*','',value)
    if not re.fullmatch('[A-HJ-NPR-Z0-9]{17}',value):raise ValueError('VIN must contain 17 valid characters')
    return value

def decode_license(raw):
    raw=raw.lstrip('\ufeff').replace('\x00','')
    if '\n' not in raw and '\\n' in raw:raw=raw.replace('\\n','\n').replace('\\r','\r')
    if '@' not in raw or 'ANSI' not in raw:raise ValueError('Scan the PDF417 barcode on the back of the license')
    # AAMVA fields are newline-delimited; some devices prefix the first DAQ with DL.
    first=raw.find('DLDAQ')
    if first>=0:raw=raw[first+2:]
    lines=raw.replace('\r','\n').replace('\x1e','\n').replace('\x1d','\n').split('\n')
    values={}
    for line in lines:
        match=re.match(r'^(?:DL)?(DAQ|DAJ|DCS|DAC|DBA|DBB|DAD)([^\n]+)$',line.strip())
        if match:
            if match[1] in values:raise ValueError('Ambiguous license barcode')
            values[match[1]]=match[2].strip()
    if not values.get('DAQ') or not values.get('DAJ'):raise ValueError('The scan is missing the license number or issuing state')
    return values

def case(db,sid,lock=False):
    row=db.query(SafeLoadCase).filter_by(shipment_id=sid)
    result=(row.with_for_update() if lock else row).first()
    if not result:raise HTTPException(404,'Safe Load record not found')
    return result

def log(db,row,action,actor,detail):
    from app.services.safe_load_custody import capture
    capture(db,row,action,actor,detail)
    row.updated_at=datetime.utcnow()
    db.add(SafeLoadEvent(shipment_id=row.shipment_id,customer_id=row.customer_id,action=action,actor=actor,detail=f'Assignment revision {row.revision}: {detail}'))

def notify(db,row,detail):
    from app.models import MuseBooking,MusePartnerCompany
    from sqlalchemy import select
    targets={row.customer_id}
    related=db.execute(select(MuseBooking.__table__.c.shipment_id).where(MuseBooking.__table__.c.shipment_id==row.shipment_id)).first()
    partner=db.get(MusePartnerCompany,1) if related else None
    if partner and partner.company_id:targets.add(partner.company_id)
    db.info['safe_load_notice_targets']=targets
    for target in targets:
        db.add(OperationalNotification(customer_id=target,shipment_id=row.shipment_id,notification_type='safe_load',audience='internal',title='Safe Load rejected · release blocked',body=detail,severity='critical',target_path=f'/safe-load?shipment={row.shipment_id}'))

def new_invite(db,row,actor):
    if row.released_at or row.status=='cancelled':raise HTTPException(409,'Released or cancelled assignments cannot be changed')
    token=secrets.token_urlsafe(32);row.invite_digest=digest(token);row.invite_expires=datetime.utcnow()+timedelta(hours=24)
    log(db,row,'invitation_created',actor,'A carrier submission link was created; previous links are revoked.')
    db.commit();return token

@event.listens_for(Session,'before_flush')
def enforce_release(db,context,instances):
    req=db.info.get('request');user=getattr(req.state,'auth_user',None) if req else None
    if not user:return
    for shipment in list(db.new|db.dirty):
        if not isinstance(shipment,Shipment):continue
        row=next((x for x in db.new if isinstance(x,SafeLoadCase) and getattr(x,'_shipment',None) is shipment),None)
        if shipment not in db.new:row=db.get(SafeLoadCase,shipment.id)
        if shipment in db.new and row is None:
            row=SafeLoadCase(customer_id=shipment.customer_id,status='awaiting_assignment',revision=0)
            row._shipment=shipment;row.shipment=shipment
            db.add(row)
            db.info.setdefault('safe_load_initial_snapshots',[]).append(row)
        if row is not None and row.status=='cancelled' and normalized(shipment.status) not in {'cancelled','canceled'}:
            raise HTTPException(409,'Cancelled Safe Load shipments cannot be reactivated. Create a replacement load.')
        if row is not None and row.status!='released' and normalized(shipment.status) in {'cancelled','canceled'}:
            if row.status!='cancelled':
                row.status='cancelled';row.invite_digest=None;row.verified_until=None;row.approved_by=None
                if shipment.id:log(db,row,'cancelled',user.email,'Shipment cancelled; warehouse release is disabled.')
        changing=shipment in db.new or inspect(shipment).attrs.status.history.has_changes() or inspect(shipment).attrs.actual_pickup_at.history.has_changes() or inspect(shipment).attrs.delivered_at.history.has_changes()
        if row is not None and changing and (normalized(shipment.status) not in PREFLIGHT or shipment.actual_pickup_at or shipment.delivered_at):
            if row.status!='released' and db.info.get('safe_load_release')!=shipment.id:
                raise HTTPException(409,'Safe Load hold: warehouse verification and release are required before pickup or transit')


    for tracking in list(db.new):
        if not isinstance(tracking,TrackingEvent):continue
        row=db.get(SafeLoadCase,tracking.shipment_id)
        if row and row.status!='released' and db.info.get('safe_load_release')!=tracking.shipment_id:
            if normalized(tracking.status) not in {'created','scheduled','pickup_requested','shipment_information_received','hold','booked','arrived_at_pickup','at_origin'}:
                raise HTTPException(409,'Safe Load hold: transport events cannot advance this shipment before warehouse release')


def release_receipt(db,row,user,method):
    from app.models import SafeLoadReleaseReceipt
    receipt=db.get(SafeLoadReleaseReceipt,row.shipment_id)
    if receipt:return receipt
    receipt=SafeLoadReleaseReceipt(shipment_id=row.shipment_id,customer_id=row.customer_id,revision=row.revision,released_by=user.id,method=method,confirmation_number='SL-'+datetime.utcnow().strftime('%Y%m%d')+'-'+secrets.token_hex(8).upper())
    db.add(receipt);db.flush();return receipt
