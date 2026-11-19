import base64
import binascii
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator, ConfigDict, model_validator
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.core.roles import COMPANY_ROLES, COMPANY_ADMIN_ROLES
from app.models import User, Customer, UserDisplayPreferences, SafeLoadCallProfile
from app.schemas.auth import UserOut
from app.services.auth import verify_password, hash_password

router=APIRouter(prefix='/workspace', tags=['Workspace'])
class SettingsIn(BaseModel):
    company_name: str = Field(default='', max_length=180)
    logo_data: str = Field(default='', max_length=410000)
    show_pricing: bool = False

    @field_validator('logo_data')
    @classmethod
    def validate_logo(cls, value):
        if not value:
            return value
        try:
            header, encoded = value.split(',', 1)
            content = base64.b64decode(encoded, validate=True)
            valid = (header == 'data:image/png;base64' and content.startswith(b'\x89PNG\r\n\x1a\n')) or (header == 'data:image/jpeg;base64' and content.startswith(b'\xff\xd8\xff'))
            if not valid or len(content) > 300000:
                raise ValueError()
        except (ValueError, binascii.Error):
            raise ValueError('Use a PNG or JPEG logo smaller than 300 KB')
        return value

class ProfileIn(BaseModel):
    full_name: str = Field(min_length=1, max_length=180)
    @field_validator('full_name')
    @classmethod
    def nonblank(cls, value):
        if not value.strip(): raise ValueError('Display name is required')
        return value.strip()

class PasswordIn(BaseModel):
    current_password: str
    new_password: str = Field(min_length=12, max_length=72)
    @field_validator('new_password')
    @classmethod
    def byte_limit(cls, value):
        if len(value.encode()) > 72: raise ValueError('Password must fit within 72 UTF-8 bytes')
        return value

def scope(user, request=None):
    context=getattr(request.state,'integration_company_id',None) if request else None
    if user.role=='admin' and context is not None:
        return 'company_workspace_settings', 'customer_id', context
    if user.role in COMPANY_ROLES:
        if not user.customer_id: raise HTTPException(403, 'Account must be linked to a company')
        return 'company_workspace_settings', 'customer_id', user.customer_id
    if user.role != 'admin': raise HTTPException(403, 'Workspace access required')
    return 'workspace_settings', 'user_id', user.id

@router.get('/settings')
def settings(request:Request, db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    table, key, identity = scope(user,request)
    row=db.execute(text(f'SELECT company_name,logo_data,show_pricing FROM {table} WHERE {key}=:id'), {'id':identity}).mappings().first()
    company = db.get(Customer, identity) if key=='customer_id' else None
    return {**dict(row),'show_pricing':bool(row['show_pricing'])} if row else {'company_name':company.name if company else 'Valhalla TMS', 'logo_data':'', 'show_pricing':False}

@router.put('/settings')
def update_settings(payload:SettingsIn, request:Request, db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    table, key, identity = scope(user,request)
    if user.role not in COMPANY_ADMIN_ROLES | {'admin'}: raise HTTPException(403, 'Company administrator required')
    name=payload.company_name.strip()
    if not name: raise HTTPException(422, 'Company name is required')
    db.execute(text(f'INSERT INTO {table} ({key},company_name,logo_data,show_pricing) VALUES (:id,:name,:logo,:pricing) ON CONFLICT ({key}) DO UPDATE SET company_name=EXCLUDED.company_name,logo_data=EXCLUDED.logo_data,show_pricing=EXCLUDED.show_pricing'), {'id':identity,'name':name,'logo':payload.logo_data,'pricing':payload.show_pricing})
    db.commit()
    return {**payload.model_dump(), 'company_name':name}

@router.put('/profile', response_model=UserOut)
def update_profile(payload:ProfileIn, db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    user.full_name=payload.full_name
    db.commit()
    return user

@router.put('/password')
def update_password(payload:PasswordIn, db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    if not verify_password(payload.current_password, user.password_hash): raise HTTPException(400, 'Current password is incorrect')
    user.password_hash=hash_password(payload.new_password)
    db.commit()
    return {'ok':True}


class DisplayPreferencesIn(BaseModel):
    model_config = ConfigDict(extra='forbid')
    theme: Literal['light','dark','system'] = 'light'
    time_format: Literal['12h','24h'] = '12h'
    timezone: str = Field(default='local', max_length=100)
    date_format: Literal['MM/DD/YYYY','DD/MM/YYYY','YYYY-MM-DD'] = 'MM/DD/YYYY'
    density: Literal['comfortable','compact'] = 'comfortable'
    show_seconds: bool = False
    show_clock: bool = True

    @field_validator('timezone')
    @classmethod
    def valid_timezone(cls, value):
        if value != 'local':
            try: ZoneInfo(value)
            except (ZoneInfoNotFoundError, ValueError): raise ValueError('Choose a valid IANA timezone')
        return value

class BrandingIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    company_name: str=Field(min_length=1,max_length=180)
    logo_data: str=Field(default='',max_length=410000)
    @field_validator('logo_data')
    @classmethod
    def logo(cls,value): return SettingsIn.validate_logo(value)

class PricingVisibilityIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    show_pricing: bool

@router.get('/preferences', response_model=DisplayPreferencesIn)
def preferences(db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    row=db.get(UserDisplayPreferences,user.id)
    return DisplayPreferencesIn(**(row.preferences if row else {}))

@router.put('/preferences', response_model=DisplayPreferencesIn)
def update_preferences(payload:DisplayPreferencesIn,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    # Personal settings are always keyed to the authenticated user, never company context.
    row=db.get(UserDisplayPreferences,user.id)
    if row: row.preferences=payload.model_dump()
    else: db.add(UserDisplayPreferences(user_id=user.id,preferences=payload.model_dump()))
    db.commit()
    return payload

def patch_company_settings(changes,request,db,user,commit=True):
    table,key,identity=scope(user,request)
    if user.role not in COMPANY_ADMIN_ROLES | {'admin'}:raise HTTPException(403,'Company administrator required')
    current=settings(request,db,user)
    values={**current,**changes}
    values['company_name']=values['company_name'].strip()
    if not values['company_name']:raise HTTPException(422,'Company name is required')
    # Update only submitted fields so branding and pricing saves cannot overwrite each other.
    updates=', '.join(f'{column}=EXCLUDED.{column}' for column in changes)
    db.execute(text(f'INSERT INTO {table} ({key},company_name,logo_data,show_pricing) VALUES (:id,:name,:logo,:pricing) ON CONFLICT ({key}) DO UPDATE SET {updates}'),{'id':identity,'name':values['company_name'],'logo':values['logo_data'],'pricing':values['show_pricing']})
    if commit:db.commit()
    return settings(request,db,user)

@router.patch('/branding')
def update_branding(payload:BrandingIn,request:Request,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    return patch_company_settings(payload.model_dump(),request,db,user)

@router.patch('/pricing')
def update_pricing(payload:PricingVisibilityIn,request:Request,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    return patch_company_settings(payload.model_dump(),request,db,user)


class SafeLoadContactIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    contact_name:str=Field(default='',max_length=180)
    phone:str=Field(default='',max_length=60)
    @model_validator(mode='after')
    def valid(self):
        import re
        self.contact_name=self.contact_name.strip();self.phone=self.phone.strip()
        if not self.contact_name and not self.phone:return self
        if not self.contact_name or not re.fullmatch(r'[+0-9(). xX-]{7,60}',self.phone) or len(re.sub(r'\D','',self.phone))<7:raise ValueError('Enter a Safe Load contact name and callable phone number including area code')
        return self

def call_profile_scope(request,user):
    if getattr(request.state,'support_company_id',None) is not None:raise HTTPException(403,'Exit manufacturer support mode to edit broker contacts')
    if user.role=='admin':
        company=getattr(request.state,'integration_company_id',None)
        return (f'company:{company}',company) if company else ('platform',None)
    if user.role not in {'broker','broker_admin'} or not user.customer_id:raise HTTPException(403,'Broker workspace required')
    return f'company:{user.customer_id}',user.customer_id

@router.get('/safe-load-contact')
def safe_load_contact_profile(request:Request,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    key,company=call_profile_scope(request,user)
    row=db.get(SafeLoadCallProfile,key)
    return {'contact_name':row.contact_name if row else '', 'phone':row.phone if row else '', 'configured':bool(row and row.phone),'company_id':company,'can_edit':user.role in {'admin','broker_admin'}}

def save_call_profile(payload,request,db,user):
    if user.role not in {'admin','broker_admin'}:raise HTTPException(403,'Only Broker Admin or Super Admin can manage the shared Safe Load call contact')
    from datetime import datetime
    from app.models import SafeLoadCase
    from app.services.safe_load_contacts import responsible_company
    key,company=call_profile_scope(request,user)
    row=db.get(SafeLoadCallProfile,key)
    if row:row.contact_name=payload.contact_name;row.phone=payload.phone;row.updated_by=user.id;row.updated_at=datetime.utcnow()
    else:db.add(SafeLoadCallProfile(scope_key=key,customer_id=company,contact_name=payload.contact_name,phone=payload.phone,updated_by=user.id))
    db.flush()
    from app.services.safe_load import log
    from app.services.muse_partner import has_access
    if user.role=='broker_admin' and has_access(db,user):db.info['safe_load_partner_request']=True
    for load in db.query(SafeLoadCase).filter(SafeLoadCase.status.notin_(['released','cancelled'])).with_for_update().all():
        owner=responsible_company(db,load)
        if owner==company:log(db,load,'broker_profile_contact_updated',user.email,'Shared Safe Load callback contact updated in broker profile.')

class ProfilePageIn(ProfileIn):
    model_config=ConfigDict(extra='forbid')
    branding: BrandingIn | None = None
    safe_load_contact: SafeLoadContactIn | None = None

class SettingsPageIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    preferences: DisplayPreferencesIn
    pricing: PricingVisibilityIn | None = None

@router.put('/profile-page')
def save_profile_page(payload:ProfilePageIn,request:Request,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    # One transaction: unauthorized branding cannot leave a partially saved name.
    workspace=None
    if payload.branding is not None:
        workspace=patch_company_settings(payload.branding.model_dump(),request,db,user,commit=False)
    if payload.safe_load_contact is not None:save_call_profile(payload.safe_load_contact,request,db,user)
    user.full_name=payload.full_name
    db.commit()
    return {'user':UserOut.model_validate(user),'workspace':workspace}

@router.put('/settings-page')
def save_settings_page(payload:SettingsPageIn,request:Request,db:Session=Depends(get_db),user:User=Depends(get_current_user)):
    # Personal preferences and an authorized company visibility edit commit together.
    workspace=None
    if payload.pricing is not None:
        workspace=patch_company_settings(payload.pricing.model_dump(),request,db,user,commit=False)
    row=db.get(UserDisplayPreferences,user.id)
    if row:row.preferences=payload.preferences.model_dump()
    else:db.add(UserDisplayPreferences(user_id=user.id,preferences=payload.preferences.model_dump()))
    db.commit()
    return {'preferences':payload.preferences,'workspace':workspace}
