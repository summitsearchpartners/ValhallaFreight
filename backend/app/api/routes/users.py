from datetime import datetime
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, EmailStr, Field, field_validator, ConfigDict
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.core.roles import COMPANY_ROLES
from app.models import User, Customer, UserActivity, UserDisplayPreferences, AdminPortalSecurity, AdminPortalSession
from app.schemas.auth import UserOut
from app.services.auth import hash_password
from app.services.user_activity import add_activity

router=APIRouter(tags=['Account Administration'])
Role=Literal['admin','manufacturer_admin','manufacturer','broker_admin','broker','customer','muse_admin']
ROLE_OPTIONS=[{'value':'admin','label':'Valhalla Freight Admin (Super User)'}, {'value':'manufacturer_admin','label':'Manufacturer Admin'}, {'value':'manufacturer','label':'Manufacturer'}, {'value':'broker_admin','label':'Broker Admin'}, {'value':'broker','label':'Broker'}, {'value':'customer','label':'Customer'}, {'value':'muse_admin','label':'Muse Freight Admin'}]

def super_user(user=Depends(get_current_user)):
    if user.role != 'admin': raise HTTPException(403,'Only Valhalla Freight Admin can manage accounts')
    return user

class AccountIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    email: str=Field(min_length=3,max_length=180)
    full_name: str=Field(min_length=1,max_length=180)
    role: Role
    customer_id: int | None=None
    active: bool=True
    password: str | None=Field(default=None,min_length=12,max_length=72)

    @field_validator('email')
    @classmethod
    def email_address(cls,value):
        import re
        value=value.strip().lower()
        if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):raise ValueError('Enter a valid email address')
        return value
    @field_validator('full_name')
    @classmethod
    def name(cls,value):
        if not value.strip(): raise ValueError('Full name is required')
        return value.strip()
    @field_validator('password')
    @classmethod
    def password_bytes(cls,value):
        if value is not None and len(value.encode())>72: raise ValueError('Password must fit within 72 UTF-8 bytes')
        return value

class PresenceIn(BaseModel):
    path: str=Field(default='/',max_length=240)
    event: Literal['heartbeat','page_view']='heartbeat'
    @field_validator('path')
    @classmethod
    def clean_path(cls,value):
        # Only a page path; never retain query strings, tokens or fragments.
        if not value.startswith('/') or '://' in value: raise ValueError('A page path is required')
        return value.split('?',1)[0].split('#',1)[0]

def out(user, companies):
    row=UserOut.model_validate(user).model_dump()
    row['company_name']=companies.get(user.customer_id)
    return row

@router.get('/admin/users/roles')
def roles(user=Depends(super_user)): return ROLE_OPTIONS

@router.get('/admin/users')
def accounts(search:str='',role:str='',company_id:int|None=None,active:bool|None=None,db:Session=Depends(get_db),user=Depends(super_user)):
    q=db.query(User)
    if search.strip():q=q.filter(or_(User.full_name.ilike(f'%{search.strip()}%'),User.email.ilike(f'%{search.strip()}%')))
    if role:q=q.filter(User.role==role)
    if company_id is not None:q=q.filter(User.customer_id.in_([company_id]+[c.id for c in db.query(Customer).filter(Customer.manufacturer_id==company_id).all()]))
    if active is not None:q=q.filter(User.active==active)
    companies={c.id:c.name for c in db.query(Customer).all()}
    return [out(x,companies) for x in q.order_by(User.full_name,User.id).all()]

@router.get('/admin/users/companies')
def companies(db:Session=Depends(get_db),user=Depends(super_user)):
    users=db.query(User).all()
    customers=db.query(Customer).order_by(Customer.name).all()
    rows=[]
    for company in customers:
        owned={company.id}|{child.id for child in customers if child.manufacturer_id==company.id}
        assigned=[account for account in users if account.customer_id in owned]
        rows.append({'id':company.id,'name':company.name,'code':company.code,'manufacturer_id':company.manufacturer_id,'account_count':len(assigned),'active_account_count':sum(account.active for account in assigned)})
    return rows

@router.get('/admin/users/activity')
def activity(user_id:int|None=None,company_id:int|None=None,limit:int=Query(100,ge=1,le=500),before_id:int|None=None,db:Session=Depends(get_db),user=Depends(super_user)):
    q=db.query(UserActivity)
    if user_id is not None:q=q.filter(UserActivity.user_id==user_id)
    if company_id is not None:q=q.filter(UserActivity.company_id==company_id)
    if before_id is not None:q=q.filter(UserActivity.id<before_id)
    rows=q.order_by(UserActivity.id.desc()).limit(limit).all()
    return [{'id':x.id,'user_id':x.user_id,'user_email':x.user_email,'user_name':x.user_name,'role':x.role,'company_id':x.company_id,'action':x.action,'path':x.path,'status_code':x.status_code,'details':x.details,'created_at':x.created_at} for x in rows]

def validate_company(db,payload):
    if payload.role=='admin': return None
    if not payload.customer_id or not db.get(Customer,payload.customer_id):raise HTTPException(422,'Select an existing company for this role')
    company=db.get(Customer,payload.customer_id)
    if payload.role in {'broker','broker_admin'}:
        from app.models import BrokerCustomerAssignment
        if db.get(BrokerCustomerAssignment,company.id):raise HTTPException(409,'Remove this company’s broker customer assignment before making it a broker workspace')
    if payload.role in COMPANY_ROLES | {'muse_admin'} and company.manufacturer_id is not None:raise HTTPException(422,'Select a parent company workspace for this role')
    return payload.customer_id

def commit(db):
    try:db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409,'An account with this email already exists')

@router.post('/admin/users',status_code=201)
def create(payload:AccountIn,db:Session=Depends(get_db),user=Depends(super_user)):
    company_id=validate_company(db,payload)
    if not payload.password:raise HTTPException(422,'An initial password is required')
    email=str(payload.email).lower().strip()
    if db.query(User).filter(User.email==email).first():raise HTTPException(409,'An account with this email already exists')
    target=User(email=email,full_name=payload.full_name,role=payload.role,customer_id=company_id,active=payload.active,password_hash=hash_password(payload.password))
    db.add(target)
    try:db.flush()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'An account with this email already exists')
    add_activity(db,user,'account_created',details={'target_user_id':target.id,'target_email':email,'role':target.role,'company_id':company_id})
    commit(db);db.refresh(target)
    return out(target,{c.id:c.name for c in db.query(Customer).all()})

def protect_superuser(db,target,payload,user):
    removing_admin=target.role=='admin' and target.active and (payload is None or payload.role!='admin' or not payload.active)
    if target.id==user.id and (payload is None or payload.role!='admin' or not payload.active):raise HTTPException(409,'You cannot remove your own super-user access')
    if removing_admin and db.query(User).filter(User.role=='admin',User.active.is_(True),User.id!=target.id).count()==0:raise HTTPException(409,'At least one active Valhalla Freight Admin must remain')

@router.put('/admin/users/{user_id}')
def update(user_id:int,payload:AccountIn,db:Session=Depends(get_db),user=Depends(super_user)):
    target=db.get(User,user_id)
    if not target:raise HTTPException(404,'Account not found')
    protect_superuser(db,target,payload,user)
    company_id=validate_company(db,payload)
    email=str(payload.email).lower().strip()
    if db.query(User).filter(User.email==email,User.id!=target.id).first():raise HTTPException(409,'An account with this email already exists')
    previous={'role':target.role,'company_id':target.customer_id,'active':target.active}
    target.email=email;target.full_name=payload.full_name;target.role=payload.role;target.customer_id=company_id;target.active=payload.active
    if payload.password:target.password_hash=hash_password(payload.password)
    add_activity(db,user,'account_updated',details={'target_user_id':target.id,'target_email':email,'before':previous,'role':target.role,'company_id':company_id,'active':target.active,'password_reset':bool(payload.password)})
    commit(db);db.refresh(target)
    return out(target,{c.id:c.name for c in db.query(Customer).all()})

@router.delete('/admin/users/{user_id}')
def remove(user_id:int,db:Session=Depends(get_db),user=Depends(super_user)):
    target=db.get(User,user_id)
    if not target:raise HTTPException(404,'Account not found')
    protect_superuser(db,target,None,user)
    add_activity(db,user,'account_removed',details={'target_user_id':target.id,'target_email':target.email,'role':target.role,'company_id':target.customer_id})
    # Keep historical activity snapshots and all company freight records.
    security=db.get(AdminPortalSecurity,target.id)
    if security:db.delete(security)
    for support in db.query(AdminPortalSession).filter_by(user_id=target.id).all():db.delete(support)
    preference=db.get(UserDisplayPreferences,target.id)
    if preference:db.delete(preference)
    db.delete(target);db.commit()
    return {'ok':True}

@router.post('/auth/presence')
def presence(payload:PresenceIn,db:Session=Depends(get_db),user=Depends(get_current_user)):
    user.last_seen_at=datetime.utcnow()
    if payload.event=='page_view':add_activity(db,user,'page_view',path=payload.path,status_code=200)
    db.commit()
    return {'ok':True}

@router.post('/auth/logout')
def logout(db:Session=Depends(get_db),user=Depends(get_current_user)):
    add_activity(db,user,'logout',status_code=200);db.commit()
    return {'ok':True}

# Broker portal customer membership is separate from manufacturer ownership.
def broker_assignment_admin(db, user):
    request=db.info.get('request')
    if request and getattr(request.state,'support_company_id',None) is not None:
        raise HTTPException(403,'Exit the manufacturer support portal to manage broker assignments')

def broker_company(db,company_id):
    company=db.get(Customer,company_id)
    if not company or company.manufacturer_id is not None:raise HTTPException(422,'Select a parent broker company workspace')
    if not db.query(User).filter(User.customer_id==company_id,User.role.in_(['broker','broker_admin']),User.active.is_(True)).first():
        raise HTTPException(422,'This company needs an active Broker or Broker Admin account first. Edit the account role in Users & Company Access.')
    return company

@router.get('/admin/broker-customers')
def broker_customers(db:Session=Depends(get_db),user=Depends(super_user)):
    from app.models import BrokerCustomerAssignment
    broker_assignment_admin(db,user)
    companies=db.query(Customer).order_by(Customer.name).all()
    users=db.query(User).all()
    broker_ids={u.customer_id for u in users if u.role in {'broker','broker_admin'}}
    assignments={a.customer_id:a for a in db.query(BrokerCustomerAssignment).all()}
    broker_ids |= {a.broker_company_id for a in assignments.values()}
    brokers=[{'id':c.id,'name':c.name,'code':c.code,'accounts':[{'email':u.email,'full_name':u.full_name,'role':u.role,'active':u.active} for u in users if u.customer_id==c.id and u.role in {'broker','broker_admin'}]} for c in companies if c.id in broker_ids and c.manufacturer_id is None]
    customers=[]
    for c in companies:
        if c.id in broker_ids:continue
        explicit=assignments.get(c.id)
        parent_assignment=assignments.get(c.manufacturer_id)
        inherited=c.manufacturer_id if c.manufacturer_id in broker_ids else parent_assignment.broker_company_id if parent_assignment else None
        customers.append({'id':c.id,'name':c.name,'code':c.code,'manufacturer_id':c.manufacturer_id,'broker_company_id':explicit.broker_company_id if explicit else inherited,'assignment_type':'assigned' if explicit else 'owned' if inherited else None,'can_assign':c.manufacturer_id is None,'account_count':sum(u.customer_id==c.id for u in users)})
    return {'brokers':brokers,'customers':customers}

class BrokerCustomerIn(BaseModel):
    model_config=ConfigDict(extra='forbid')
    customer_id:int|None=None
    name:str|None=Field(default=None,min_length=2,max_length=180)
    @field_validator('name')
    @classmethod
    def clean_customer_name(cls,value):
        if value is not None and len(value.strip())<2:raise ValueError('Enter at least two characters for the customer name')
        return value.strip() if value is not None else None

@router.post('/admin/broker-companies/{company_id}/customers',status_code=201)
def assign_broker_customer(company_id:int,payload:BrokerCustomerIn,db:Session=Depends(get_db),user=Depends(super_user)):
    from app.models import BrokerCustomerAssignment, CustomerProfile
    from uuid import uuid4
    broker_assignment_admin(db,user);broker_company(db,company_id)
    if bool(payload.customer_id)==bool(payload.name):raise HTTPException(422,'Choose an existing customer or enter a new customer name')
    created=False
    if payload.name:
        customer=Customer(code='PENDING-'+uuid4().hex[:12].upper(),name=payload.name)
        db.add(customer);db.flush();customer.code=f'VFC-{customer.id:06d}'
        db.add(CustomerProfile(customer_id=customer.id));created=True
    else:
        customer=db.get(Customer,payload.customer_id)
        if not customer:raise HTTPException(404,'Customer not found')
    if customer.id==company_id or customer.manufacturer_id is not None:raise HTTPException(422,'Choose an independent customer company. Existing parent ownership is preserved.')
    if db.query(User).filter(User.customer_id==customer.id,User.role.in_(['broker','broker_admin'])).first():raise HTTPException(422,'A broker workspace cannot be added as another broker’s customer')
    assignment=db.get(BrokerCustomerAssignment,customer.id)
    if assignment:
        if assignment.broker_company_id!=company_id:raise HTTPException(409,'Customer already belongs to another broker portal. Remove that assignment first.')
        return {'customer_id':customer.id,'broker_company_id':company_id,'created':False}
    child_ids=[c.id for c in db.query(Customer).filter(Customer.manufacturer_id==customer.id).all()]
    if child_ids and db.query(BrokerCustomerAssignment).filter(BrokerCustomerAssignment.customer_id.in_(child_ids)).first():raise HTTPException(409,'A child customer already has a broker assignment')
    db.add(BrokerCustomerAssignment(customer_id=customer.id,broker_company_id=company_id,assigned_by=user.id))
    add_activity(db,user,'broker_customer_assigned',details={'company_id':company_id,'customer_id':customer.id,'customer_name':customer.name,'customer_created':created})
    try:db.commit()
    except IntegrityError:
        db.rollback();raise HTTPException(409,'Customer assignment changed in another session. Refresh and try again.')
    return {'customer_id':customer.id,'broker_company_id':company_id,'created':created}

@router.delete('/admin/broker-companies/{company_id}/customers/{customer_id}')
def unassign_broker_customer(company_id:int,customer_id:int,db:Session=Depends(get_db),user=Depends(super_user)):
    from app.models import BrokerCustomerAssignment
    broker_assignment_admin(db,user)
    assignment=db.get(BrokerCustomerAssignment,customer_id)
    if not assignment or assignment.broker_company_id!=company_id:raise HTTPException(404,'Explicit customer assignment not found')
    db.delete(assignment)
    add_activity(db,user,'broker_customer_unassigned',details={'company_id':company_id,'customer_id':customer_id})
    db.commit();return {'ok':True}
