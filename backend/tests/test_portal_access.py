from datetime import datetime,timedelta
import pyotp
from fastapi import HTTPException
from types import SimpleNamespace
from test_manufacturer import setup,headers
from app.models import Customer,User,Quote,AdminPortalSession,AdminPortalSecurity
from app.services import portal_access as service
from test_accounts import account

PREFIX='/api/v1/admin/portal-access'
PASSWORD='Original12345!'

def launch(c,cid=2,**extra):
    return c.post(PREFIX+'/launch',headers=headers(4),json={'customer_id':cid,'portal_type':'customer','password':PASSWORD,**extra})

def grant(c,cid=2):
    result=launch(c,cid)
    assert result.status_code==200,result.text
    result=c.post(PREFIX+'/redeem',headers={**headers(4),'X-Company-Id':str(cid)},json={'ticket':result.json()['ticket']})
    assert result.status_code==200,result.text
    return {**headers(4),'X-Company-Id':str(cid),'X-Portal-Session':result.json()['portal_token']}

def test_manufacturer_customers_are_owned_records_not_logins(setup):
    c,factory=setup
    assert c.get('/api/v1/customers',headers=headers(1)).json()==[]
    assert [x['id'] for x in c.get('/api/v1/customers?include_workspace=true',headers=headers(1)).json()]==[1]
    for uid in (1,2):
        r=c.post('/api/v1/customers',headers=headers(uid),json={'name':f'Customer {uid}'})
        assert r.status_code==201,r.text
        child=r.json()['id'];assert r.json()['manufacturer_id']==1
        assert c.patch(f'/api/v1/customers/{child}',headers=headers(uid),json={'name':f'Updated {uid}'}).status_code==200
        assert c.get(f'/api/v1/customers/{child}/360',headers=headers(3)).status_code==404
        assert c.patch(f'/api/v1/customers/{child}',headers=headers(3),json={'name':'Foreign'}).status_code in (403,404)
        assert c.post('/api/v1/admin/users',headers=headers(uid),json=account(customer_id=child)).status_code==403
        assert c.post('/api/v1/admin/users',headers=headers(4),json=account(email=f'bad{uid}@test.local',customer_id=child)).status_code==422
        login=c.post('/api/v1/admin/users',headers=headers(4),json=account(email=f'customer{uid}@test.local',role='customer',customer_id=child))
        assert login.status_code==201,login.text
        customer_headers=headers(login.json()['id'])
        assert c.get('/api/v1/portal/me',headers=customer_headers).json()['customer']['id']==child
    assert len(c.get('/api/v1/customers',headers=headers(2)).json())==2
    assert c.get('/api/v1/customers',headers=headers(3)).json()==[]
    assert c.post('/api/v1/customers',headers=headers(1),json={'name':'Wrong owner','manufacturer_id':2}).status_code==403
    with factory() as db:
        assert db.query(User).count()==9  # Only explicit Valhalla login creation above.
        assert db.get(Customer,1).manufacturer_id is None
        child=db.query(Customer).filter_by(manufacturer_id=1).first()
        db.add(Quote(quote_number='CHILD',customer_id=child.id,origin={},destination={},handling_units=[]));db.commit()
    assert len(c.get('/api/v1/quotes',headers=headers(1)).json())==2
    assert len(c.get('/api/v1/quotes',headers=headers(3)).json())==1
    assert len(c.get('/api/v1/admin/users?company_id=1',headers=headers(4)).json())==5


def test_support_requires_real_superuser_and_verified_single_use_ticket(setup):
    c,_=setup
    for uid in (1,2,3,5,6):
        assert c.get(PREFIX+'/portals',headers=headers(uid)).status_code==403
        assert c.post(PREFIX+'/launch',headers=headers(uid),json={'customer_id':2,'password':PASSWORD}).status_code==403
    assert c.get('/api/v1/portal/me',headers={**headers(4),'X-Company-Id':'2'}).status_code==403
    assert launch(c,password='wrong').status_code==403
    issued=launch(c).json();ticket=issued['ticket']
    assert c.post(PREFIX+'/redeem',headers={**headers(4),'X-Company-Id':'1'},json={'ticket':ticket}).status_code==403
    redeemed=c.post(PREFIX+'/redeem',headers=headers(4),json={'ticket':ticket})
    assert redeemed.status_code==200,redeemed.text
    token=redeemed.json()['portal_token'];h={**headers(4),'X-Company-Id':'2','X-Portal-Session':token}
    assert c.post(PREFIX+'/redeem',headers=headers(4),json={'ticket':ticket}).status_code==403
    result=c.get('/api/v1/portal/me',headers=h)
    assert result.status_code==200,result.text
    assert result.json()['user']['role']=='admin'
    assert result.json()['customer']['id']==2
    assert c.get('/api/v1/portal/me',headers={**h,'X-Company-Id':'1'}).status_code==403
    assert c.get('/api/v1/auth/me',headers={'Authorization':'Bearer '+token}).status_code==401
    assert c.post(PREFIX+'/end',headers=h).status_code==200
    assert c.get('/api/v1/portal/me',headers=h).status_code==403
    assert c.get('/api/v1/auth/me',headers=headers(4)).json()['role']=='admin'
    events=c.get('/api/v1/admin/users/activity?user_id=4',headers=headers(4)).json()
    assert {'portal_access_verified','portal_support_opened','portal_support_ended'}<={x['action'] for x in events}
    assert PASSWORD not in str(events) and ticket not in str(events) and token not in str(events)


def test_ticket_and_support_session_expiry(setup):
    c,factory=setup
    ticket=launch(c).json()['ticket']
    with factory() as db:
        db.query(AdminPortalSession).one().ticket_expires_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
    assert c.post(PREFIX+'/redeem',headers=headers(4),json={'ticket':ticket}).status_code==403
    h=grant(c)
    with factory() as db:
        row=db.query(AdminPortalSession).filter(AdminPortalSession.redeemed_at.is_not(None)).one()
        row.expires_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
    assert c.get('/api/v1/portal/me',headers=h).status_code==403


def test_google_authenticator_encryption_replay_and_disable(setup,monkeypatch):
    c,factory=setup
    setup_result=c.post(PREFIX+'/authenticator/setup',headers=headers(4),json={'password':PASSWORD})
    assert setup_result.status_code==200,setup_result.text
    secret=setup_result.json()['secret'];totp=pyotp.TOTP(secret)
    assert setup_result.json()['qr_data'].startswith('data:image/svg+xml;base64,')
    with factory() as db:assert secret not in db.get(AdminPortalSecurity,4).pending_secret
    base=int(service.time.time())//30*30
    monkeypatch.setattr(service.time,'time',lambda:base)
    code=totp.at(base)
    assert c.post(PREFIX+'/authenticator/confirm',headers=headers(4),json={'password':PASSWORD,'code':code}).status_code==200
    assert c.get(PREFIX+'/security',headers=headers(4)).json()['mfa_enabled']
    assert launch(c).status_code==403
    assert launch(c,code=code).status_code==403
    monkeypatch.setattr(service.time,'time',lambda:base+30)
    assert launch(c,code=totp.at(base+30)).status_code==200
    assert launch(c,code=totp.at(base+30)).status_code==403
    with factory() as db:assert secret not in db.get(AdminPortalSecurity,4).totp_secret
    monkeypatch.setattr(service.time,'time',lambda:base+60)
    assert c.post(PREFIX+'/authenticator/disable',headers=headers(4),json={'password':PASSWORD,'code':totp.at(base+60)}).status_code==200
    assert not c.get(PREFIX+'/security',headers=headers(4)).json()['mfa_enabled']
    events=c.get('/api/v1/admin/users/activity',headers=headers(4)).json()
    assert secret not in str(events)


def test_portal_verification_has_persistent_attempt_lockout(setup):
    c,_=setup
    for _ in range(5):assert launch(c,password='wrong').status_code==403
    assert launch(c).status_code==429
    assert c.get('/api/v1/auth/me',headers=headers(4)).status_code==200


def test_owned_customer_primary_contacts_and_portal_changes(setup):
    c,_=setup
    child=c.post('/api/v1/customers',headers=headers(1),json={'name':'Contacts customer'}).json()['id']
    for first in ['First','Second']:
        r=c.post(f'/api/v1/customers/{child}/contacts',headers=headers(2),json={'first_name':first,'last_name':'Contact','email':first.lower()+'@test.local','primary':True})
        assert r.status_code==201,r.text
    detail=c.get(f'/api/v1/customers/{child}/360',headers=headers(1)).json()
    assert sum(x['primary'] for x in detail['contacts'])==1
    h=grant(c,child)
    r=c.patch('/api/v1/portal/me/margin-protection',headers=h,json={'threshold':95,'email_notify':True})
    assert r.status_code==200,r.text
    assert c.get('/api/v1/portal/me',headers=h).json()['profile']['margin_protection_threshold']==95
    assert c.get('/api/v1/portal/documents',headers={**h,'X-Company-Id':'2'}).status_code==403
