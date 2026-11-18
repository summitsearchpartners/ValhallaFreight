from datetime import datetime, timedelta
from typing import Literal
import base64, io
import pyotp, qrcode, qrcode.image.svg
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.routes.users import super_user
from app.models import Customer, User
from app.services import portal_access as service
from app.integrations.secrets import encrypt_secret_payload,decrypt_secret_payload
from app.services.user_activity import add_activity

router=APIRouter(prefix='/admin/portal-access',tags=['Valhalla Portal Access'])
class VerifyIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    password:str=Field(min_length=1,max_length=256)
    code:str|None=Field(default=None,pattern=r'^\d{6}$')
class LaunchIn(VerifyIn):
    customer_id:int=Field(gt=0)
    portal_type:Literal['manufacturer','customer']|None=None
class RedeemIn(BaseModel):ticket:str=Field(min_length=20,max_length=180)

@router.get('/portals')
def portals(db:Session=Depends(get_db),user=Depends(super_user)):
    customers=db.query(Customer).order_by(Customer.name).all();names={c.id:c.name for c in customers}
    accounts=db.query(User).all()
    return [{'id':c.id,'name':c.name,'code':c.code,'status':c.status,'manufacturer_id':c.manufacturer_id,'manufacturer_name':names.get(c.manufacturer_id),'portal_type':'customer' if c.manufacturer_id else 'manufacturer','login_count':sum(u.role=='customer' and u.customer_id==c.id and u.active for u in accounts)} for c in customers]

@router.get('/security')
def security(db:Session=Depends(get_db),user=Depends(super_user)):
    row=service.security_row(db,user);db.commit()
    return {'mfa_enabled':bool(row.totp_secret),'locked_until':row.locked_until}

@router.post('/authenticator/setup')
def setup(payload:VerifyIn,db:Session=Depends(get_db),user=Depends(super_user)):
    row=service.verify_identity(db,user,payload.password,payload.code)
    if row.totp_secret:raise HTTPException(409,'Authenticator is already enabled. Disable it before replacing the device.')
    secret=pyotp.random_base32();row.pending_secret=encrypt_secret_payload({'secret':secret});row.pending_expires_at=datetime.utcnow()+timedelta(minutes=10)
    uri=pyotp.TOTP(secret).provisioning_uri(name=user.email,issuer_name='Valhalla Freight Admin')
    output=io.BytesIO();qrcode.make(uri,image_factory=qrcode.image.svg.SvgPathImage).save(output)
    db.commit()
    return {'secret':secret,'provisioning_uri':uri,'qr_data':'data:image/svg+xml;base64,'+base64.b64encode(output.getvalue()).decode(),'expires_in':600}

@router.post('/authenticator/confirm')
def confirm(payload:VerifyIn,db:Session=Depends(get_db),user=Depends(super_user)):
    row=service.verify_identity(db,user,payload.password,require_totp=False,clear_failures=False)
    if not row.pending_secret or not row.pending_expires_at or row.pending_expires_at<datetime.utcnow():raise HTTPException(403,'Authenticator setup expired. Start setup again.')
    secret=decrypt_secret_payload(row.pending_secret).get('secret');counter=service.valid_counter(secret,payload.code)
    if counter is None:service.reject(db,user,row,'The authenticator code is incorrect')
    row.failed_attempts=0;row.locked_until=None
    row.totp_secret=row.pending_secret;row.pending_secret=None;row.pending_expires_at=None;row.last_counter=counter
    add_activity(db,user,'portal_authenticator_enabled',status_code=200);db.commit()
    return {'mfa_enabled':True}

@router.post('/authenticator/disable')
def disable(payload:VerifyIn,db:Session=Depends(get_db),user=Depends(super_user)):
    row=service.verify_identity(db,user,payload.password,payload.code)
    row.totp_secret=None;row.pending_secret=None;row.pending_expires_at=None;row.last_counter=-1
    add_activity(db,user,'portal_authenticator_disabled',status_code=200);db.commit()
    return {'mfa_enabled':False}

@router.post('/launch')
def launch(payload:LaunchIn,db:Session=Depends(get_db),user=Depends(super_user)):
    return service.launch(db,user,payload.customer_id,payload.password,payload.code,payload.portal_type)

@router.post('/redeem')
def redeem(payload:RedeemIn,request:Request,db:Session=Depends(get_db),user=Depends(super_user)):
    return service.redeem(db,user,payload.ticket,getattr(request.state,'integration_company_id',None))

@router.post('/end')
def end(request:Request,db:Session=Depends(get_db),user=Depends(super_user)):
    customer_id=getattr(request.state,'integration_company_id',None)
    if not customer_id:raise HTTPException(422,'Select a customer portal')
    row=service.require_session(db,user,request.headers.get('X-Portal-Session'),customer_id)
    row.revoked_at=datetime.utcnow();add_activity(db,user,'portal_support_ended',status_code=200,details={'company_id':customer_id,'session_id':row.id});db.commit()
    return {'ok':True}
