from datetime import datetime,timedelta
from test_manufacturer import setup,headers
from app.models import AdminPortalSession,User

PREFIX='/api/v1/admin/portal-access'

def manufacturer_grant(c,company=1):
    launched=c.post(PREFIX+'/launch',headers=headers(4),json={'customer_id':company,'password':'Original12345!'})
    assert launched.status_code==200,launched.text
    assert launched.json()['portal_type']=='manufacturer'
    redeemed=c.post(PREFIX+'/redeem',headers=headers(4),json={'ticket':launched.json()['ticket']})
    assert redeemed.status_code==200,redeemed.text
    assert redeemed.json()['portal_type']=='manufacturer'
    return {**headers(4),'X-Company-Id':str(company),'X-Portal-Workspace':'manufacturer','X-Portal-Session':redeemed.json()['portal_token']}


def test_manufacturer_support_opens_real_company_scope_and_preserves_admin(setup):
    c,factory=setup
    h=manufacturer_grant(c)
    identity=c.get('/api/v1/auth/me',headers=h)
    assert identity.status_code==200,identity.text
    assert identity.json()['id']==4 and identity.json()['role']=='admin'
    assert c.get('/api/v1/workspace/settings',headers=h).json()['company_name']=='Alpha'
    assert [q['id'] for q in c.get('/api/v1/quotes',headers=h).json()]==[1]
    assert c.get('/api/v1/quotes/2',headers=h).status_code==404
    assert c.get('/api/v1/customers',headers=h).json()==[]
    child=c.post('/api/v1/customers',headers=h,json={'name':'Support-created customer'})
    assert child.status_code==201,child.text
    assert child.json()['manufacturer_id']==1
    assert len(c.get('/api/v1/customers',headers=headers(1)).json())==1
    assert c.get('/api/v1/customers',headers=headers(3)).json()==[]
    assert c.get('/api/v1/integrations',headers=h).status_code==200
    assert all(row['customer_id']==1 for row in c.get('/api/v1/integrations',headers=h).json())
    saved=c.put('/api/v1/workspace/settings-page',headers=h,json={'preferences':{'theme':'dark'},'pricing':{'show_pricing':True}})
    assert saved.status_code==200,saved.text
    assert c.get('/api/v1/workspace/settings',headers=headers(1)).json()['show_pricing']
    assert not c.get('/api/v1/workspace/settings',headers=headers(3)).json()['show_pricing']
    assert c.get('/api/v1/auth/me',headers=headers(4)).json()['role']=='admin'
    assert len(c.get('/api/v1/quotes',headers=headers(4)).json())==2
    with factory() as db:
        assert db.get(User,4).role=='admin' and db.get(User,4).customer_id is None
    events=c.get('/api/v1/admin/users/activity?user_id=4',headers=headers(4)).json()
    assert any(e['action']=='portal_support_opened' and e['details'].get('portal_type')=='manufacturer' and e['company_id']==1 for e in events)


def test_workspace_type_cannot_be_forged_or_reused_for_another_company(setup):
    c,_=setup
    h=manufacturer_grant(c)
    for invalid in [{**h,'X-Company-Id':'2'},{key:value for key,value in h.items() if key!='X-Portal-Session'}]:
        r=c.get('/api/v1/quotes',headers=invalid)
        assert r.status_code==403,r.text
        assert r.headers['X-Portal-Session-Invalid']=='1'
    assert c.get('/api/v1/portal/me',headers=h).status_code==403
    customer=c.post('/api/v1/customers',headers=headers(1),json={'name':'Customer portal only'}).json()['id']
    bad=c.post(PREFIX+'/launch',headers=headers(4),json={'customer_id':customer,'portal_type':'manufacturer','password':'Original12345!'})
    assert bad.status_code==422,bad.text
    launched=c.post(PREFIX+'/launch',headers=headers(4),json={'customer_id':customer,'password':'Original12345!'})
    assert launched.json()['portal_type']=='customer'
    redeemed=c.post(PREFIX+'/redeem',headers=headers(4),json={'ticket':launched.json()['ticket']}).json()
    ch={**headers(4),'X-Company-Id':str(customer),'X-Portal-Session':redeemed['portal_token']}
    assert c.get('/api/v1/portal/me',headers=ch).status_code==200
    assert c.get('/api/v1/quotes',headers={**ch,'X-Portal-Workspace':'manufacturer'}).status_code==403


def test_manufacturer_support_revocation_expiry_and_active_role(setup):
    c,factory=setup
    h=manufacturer_grant(c)
    assert c.post(PREFIX+'/end',headers=h).status_code==200
    assert c.get('/api/v1/auth/me',headers=h).status_code==403
    h=manufacturer_grant(c)
    with factory() as db:
        db.query(AdminPortalSession).filter(AdminPortalSession.revoked_at.is_(None)).one().expires_at=datetime.utcnow()-timedelta(seconds=1);db.commit()
    assert c.get('/api/v1/quotes',headers=h).status_code==403
    assert c.get('/api/v1/auth/me',headers=headers(4)).status_code==200
