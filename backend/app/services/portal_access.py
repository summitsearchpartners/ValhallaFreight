"""Password/MFA-verified, per-window support grants. No customer impersonation."""
from datetime import datetime, timedelta, timezone
import hashlib, secrets, time
import pyotp
from fastapi import HTTPException
from jose import jwt, JWTError
from app.core.config import settings
from app.models import AdminPortalSecurity, AdminPortalSession, Customer, User
from app.services.auth import verify_password
from app.integrations.secrets import encrypt_secret_payload, decrypt_secret_payload
from app.services.user_activity import add_activity


def security_row(db,user):
    # Serialize first-time enrollment/verification even before a security row exists.
    db.query(User).filter_by(id=user.id).with_for_update().first()
    row=db.query(AdminPortalSecurity).filter_by(user_id=user.id).with_for_update().first()
    if not row:
        row=AdminPortalSecurity(user_id=user.id,last_counter=-1,failed_attempts=0)
        db.add(row);db.flush()
    return row


def reject(db,user,row,detail):
    row.failed_attempts+=1
    if row.failed_attempts>=5:row.locked_until=datetime.utcnow()+timedelta(minutes=5)
    add_activity(db,user,'portal_verification_failed',status_code=403)
    db.commit()
    raise HTTPException(403,detail)


def verify_identity(db,user,password,code=None,require_totp=True,clear_failures=True):
    row=security_row(db,user)
    if row.locked_until and row.locked_until>datetime.utcnow():raise HTTPException(429,'Too many failed attempts. Try again in five minutes.')
    if row.locked_until:
        row.failed_attempts=0;row.locked_until=None
    if not verify_password(password,user.password_hash):reject(db,user,row,'Your administrator password is incorrect')
    if require_totp and row.totp_secret:
        secret=decrypt_secret_payload(row.totp_secret).get('secret')
        counter=valid_counter(secret,code,row.last_counter)
        if counter is None:reject(db,user,row,'Enter a fresh six-digit authenticator code')
        row.last_counter=counter
    if clear_failures:row.failed_attempts=0;row.locked_until=None
    return row


def valid_counter(secret,code,last=-1):
    if not secret or not code:return None
    totp=pyotp.TOTP(secret)
    now=int(time.time())//30
    for counter in (now,now-1,now+1):
        if counter>last and secrets.compare_digest(totp.at(counter*30),str(code)):
            return counter
    return None


def launch(db,user,customer_id,password,code,portal_type=None):
    row=verify_identity(db,user,password,code)
    customer=db.get(Customer,customer_id)
    if not customer:raise HTTPException(404,'Customer portal not found')
    portal_type=portal_type or ('customer' if customer.manufacturer_id else 'manufacturer')
    if portal_type=='manufacturer' and customer.manufacturer_id is not None:raise HTTPException(422,'Select a manufacturer company for this workspace')
    ticket=secrets.token_urlsafe(32);now=datetime.utcnow()
    session=AdminPortalSession(id=secrets.token_hex(24),user_id=user.id,customer_id=customer.id,portal_type=portal_type,ticket_hash=hashlib.sha256(ticket.encode()).hexdigest(),ticket_expires_at=now+timedelta(seconds=60),expires_at=now+timedelta(minutes=15))
    db.add(session)
    add_activity(db,user,'portal_access_verified',status_code=200,details={'company_id':customer.id,'customer_name':customer.name,'portal_type':portal_type,'mfa':bool(row.totp_secret)})
    db.commit()
    return {'ticket':ticket,'customer_id':customer.id,'portal_type':portal_type,'company_name':customer.name,'ticket_expires_in':60,'session_expires_at':session.expires_at}


def redeem(db,user,ticket,expected_customer=None):
    row=db.query(AdminPortalSession).filter_by(ticket_hash=hashlib.sha256(ticket.encode()).hexdigest()).with_for_update().first()
    now=datetime.utcnow()
    if not row or row.user_id!=user.id or row.revoked_at or row.redeemed_at or row.ticket_expires_at<now:raise HTTPException(403,'This portal launch link is invalid, expired or already used. Verify again in Portal Access.')
    if expected_customer is not None and expected_customer!=row.customer_id:raise HTTPException(403,'Portal launch does not match the selected customer')
    row.redeemed_at=now
    exp=row.expires_at.replace(tzinfo=timezone.utc)
    token=jwt.encode({'sub':str(user.id),'purpose':'portal-support','customer_id':row.customer_id,'portal_type':row.portal_type,'jti':row.id,'exp':exp},settings.jwt_secret_key,algorithm=settings.jwt_algorithm)
    add_activity(db,user,'portal_support_opened',status_code=200,details={'company_id':row.customer_id,'session_id':row.id,'portal_type':row.portal_type})
    db.commit()
    return {'portal_token':token,'customer_id':row.customer_id,'portal_type':row.portal_type,'company_name':db.get(Customer,row.customer_id).name,'expires_at':row.expires_at}


def require_session(db,user,token,customer_id,portal_type=None):
    try:
        payload=jwt.decode(token or '',settings.jwt_secret_key,algorithms=[settings.jwt_algorithm])
        if payload.get('purpose')!='portal-support' or int(payload.get('sub',0))!=user.id or int(payload.get('customer_id',0))!=customer_id:raise ValueError()
    except (JWTError,ValueError,TypeError):raise HTTPException(403,'Verified portal access is required. Open Portal Access to continue.',headers={'X-Portal-Session-Invalid':'1'})
    row=db.get(AdminPortalSession,payload.get('jti',''))
    if not row or row.user_id!=user.id or row.customer_id!=customer_id or not row.redeemed_at or row.revoked_at or row.expires_at<datetime.utcnow():raise HTTPException(403,'This support session has expired or ended. Verify again in Portal Access.',headers={'X-Portal-Session-Invalid':'1'})
    if portal_type and row.portal_type!=portal_type:raise HTTPException(403,'This support session is for a different portal type. Verify again in Portal Access.',headers={'X-Portal-Session-Invalid':'1'})
    if payload.get('portal_type','customer')!=row.portal_type:raise HTTPException(403,'Invalid support workspace',headers={'X-Portal-Session-Invalid':'1'})
    return row
