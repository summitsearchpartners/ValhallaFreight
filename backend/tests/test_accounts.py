from test_manufacturer import setup, headers
from app.models import User, UserActivity, IntegrationConnection, IntegrationCredential
from app.core.config import settings


def account(**changes):
    return {'email':'new@alpha.com','full_name':'New User','role':'manufacturer','customer_id':1,'active':True,'password':'InitialPassword123!',**changes}


def test_role_selectors_and_superuser_create(setup):
    c,_=setup
    assert [r['value'] for r in c.get('/api/v1/admin/users/roles',headers=headers(4)).json()]==['admin','manufacturer_admin','manufacturer','broker_admin','broker','customer','muse_admin']
    for uid in [1,2,3,5,6,7]:
        assert c.get('/api/v1/admin/users',headers=headers(uid)).status_code==403
        assert c.post('/api/v1/admin/users',headers=headers(uid),json=account()).status_code==403
    for role in ['manufacturer_admin','manufacturer','broker_admin','broker','customer','admin','muse_admin']:
        r=c.post('/api/v1/admin/users',headers=headers(4),json=account(email=f'{role}@alpha.com',role=role))
        assert r.status_code==201,r.text
        assert r.json()['customer_id']==(None if role=='admin' else 1)
        assert 'password_hash' not in r.text
        login=c.post('/api/v1/auth/login',json={'email':f'{role}@alpha.com','password':'InitialPassword123!'})
        assert login.status_code==200
    assert c.post('/api/v1/admin/users',headers=headers(4),json=account(role='manufacturer',customer_id=None)).status_code==422
    assert c.post('/api/v1/admin/users',headers=headers(4),json=account(role='manufacturer',customer_id=999)).status_code==422
    assert c.post('/api/v1/admin/users',headers=headers(4),json=account(role='owner')).status_code==422


def test_update_assignment_disable_remove_and_activity(setup):
    c,factory=setup
    r=c.post('/api/v1/admin/users',headers=headers(4),json=account())
    uid=r.json()['id']
    token=c.post('/api/v1/auth/login',json={'email':'new@alpha.com','password':'InitialPassword123!'}).json()['access_token']
    h={'Authorization':'Bearer '+token}
    assert [q['id'] for q in c.get('/api/v1/quotes',headers=h).json()]==[1]
    changed=account(customer_id=2,role='manufacturer_admin',password='ResetPassword123!')
    assert c.put(f'/api/v1/admin/users/{uid}',headers=headers(4),json=changed).status_code==200
    assert [q['id'] for q in c.get('/api/v1/quotes',headers=h).json()]==[2]
    assert c.post('/api/v1/auth/login',json={'email':'new@alpha.com','password':'InitialPassword123!'}).status_code==401
    assert c.post('/api/v1/auth/login',json={'email':'new@alpha.com','password':'ResetPassword123!'}).status_code==200
    changed['active']=False
    assert c.put(f'/api/v1/admin/users/{uid}',headers=headers(4),json=changed).status_code==200
    assert c.get('/api/v1/quotes',headers=h).status_code==401
    assert c.delete(f'/api/v1/admin/users/{uid}',headers=headers(4)).status_code==200
    activity=c.get('/api/v1/admin/users/activity',headers=headers(4)).json()
    assert any(a['action']=='account_removed' and a['details']['target_user_id']==uid for a in activity)
    assert 'InitialPassword123!' not in str(activity) and 'ResetPassword123!' not in str(activity)
    assert c.delete('/api/v1/admin/users/4',headers=headers(4)).status_code==409
    assert c.put('/api/v1/admin/users/4',headers=headers(4),json=account(email='4@test.local',role='manufacturer')).status_code==409


def test_presence_last_login_activity_and_filtering(setup):
    c,_=setup
    login=c.post('/api/v1/auth/login',json={'email':'2@test.local','password':'Original12345!'})
    assert login.status_code==200 and login.json()['user']['last_login_at']
    assert c.post('/api/v1/auth/presence',headers=headers(2),json={'event':'page_view','path':'/shipments?token=private'}).status_code==200
    assert c.post('/api/v1/auth/presence',headers=headers(2),json={'path':'/shipments','event':'heartbeat'}).status_code==200
    c.get('/api/v1/quotes',headers=headers(2))
    rows=c.get('/api/v1/admin/users?company_id=1&role=manufacturer',headers=headers(4)).json()
    assert len(rows)==1 and rows[0]['id']==2 and rows[0]['last_seen_at']
    events=c.get('/api/v1/admin/users/activity?user_id=2',headers=headers(4)).json()
    assert any(e['action']=='login' for e in events)
    assert any(e['action']=='page_view' and e['path']=='/shipments' for e in events)
    assert any(e['action']=='api_request' and e['status_code']==200 for e in events)
    assert 'private' not in str(events)
    assert c.get('/api/v1/admin/users/activity',headers=headers(1)).status_code==403


def test_manufacturer_admin_integrations_company_isolation(setup):
    c,factory=setup
    with factory() as db:
        db.add(IntegrationConnection(id=50,provider='Global API',category='Custom',customer_id=None));db.commit()
    assert c.get('/api/v1/integrations',headers=headers(2)).status_code==403
    a=c.get('/api/v1/integrations',headers=headers(1))
    assert a.status_code==200,a.text
    assert all(x['customer_id']==1 for x in a.json())
    assert c.get('/api/v1/integrations/connection/50/manage',headers=headers(1)).status_code==404
    b=c.get('/api/v1/integrations',headers=headers(3))
    assert all(x['customer_id']==2 for x in b.json())
    aid=a.json()[0]['id']
    assert c.put(f'/api/v1/integrations/connection/{aid}/credentials',headers=headers(1),json={'auth_type':'api_key','api_key':'company-one-secret'}).status_code==200
    assert c.get(f'/api/v1/integrations/connection/{aid}/credentials',headers=headers(3)).status_code==404
    assert c.get('/api/v1/integrations',headers={**headers(1),'X-Company-Id':'2'}).status_code==403
    adminscope={**headers(4),'X-Company-Id':'1'}
    rows=c.get('/api/v1/integrations',headers=adminscope).json()
    assert rows and all(x['customer_id']==1 for x in rows)
    assert len(c.get('/api/v1/integrations',headers=headers(4)).json())>=3
    assert c.get(f'/api/v1/integrations/connection/{aid}/credentials',headers=adminscope).json()['has_api_key']
    # Secrets are encrypted and never echoed in API responses.
    assert 'company-one-secret' not in c.get(f'/api/v1/integrations/connection/{aid}/manage',headers=adminscope).text
    with factory() as db:
        credential=db.query(IntegrationCredential).filter_by(integration_id=aid).one()
        assert 'company-one-secret' not in credential.encrypted_payload


def test_manufacturer_credentials_never_fall_back_to_broker_env(setup,monkeypatch):
    c,_=setup
    monkeypatch.setattr(settings,'dayton_api_username','broker-private-user')
    monkeypatch.setattr(settings,'dayton_api_password','broker-private-password')
    r=c.get('/api/v1/integrations/dayton',headers=headers(1))
    assert r.status_code==200,r.text
    assert r.json()['credentials_configured'] is False
    assert r.json()['credential_source']=='Not configured'
    assert 'broker-private' not in r.text


def test_manufacturer_admin_portal_configuration_and_superuser_preview(setup):
    c,_=setup
    c.post('/api/v1/admin/users',headers=headers(4),json=account(email='portal@alpha.com',role='customer'))
    # Company portal view accepts only customer accounts or explicit super-user context.
    assert c.get('/api/v1/portal/me',headers=headers(1)).status_code==403
    launched=c.post('/api/v1/admin/portal-access/launch',headers=headers(4),json={'customer_id':2,'portal_type':'customer','password':'Original12345!'})
    grant=c.post('/api/v1/admin/portal-access/redeem',headers=headers(4),json={'ticket':launched.json()['ticket']}).json()
    preview=c.get('/api/v1/portal/me',headers={**headers(4),'X-Company-Id':'2','X-Portal-Session':grant['portal_token']})
    assert preview.status_code==200,preview.text
    assert preview.json()['customer']['id']==2
    assert c.get('/api/v1/portal/me',headers=headers(5)).json()['customer']['id']==1
    assert c.patch('/api/v1/customers/2/margin-protection',headers=headers(1),json={'threshold':50}).status_code==404
    assert c.patch('/api/v1/customers/1/margin-protection',headers=headers(2),json={'threshold':50}).status_code==403
    configured=c.patch('/api/v1/customers/1/margin-protection',headers=headers(1),json={'threshold':50})
    assert configured.status_code==200,configured.text
    assert float(configured.json()['threshold'])==50
    # Super-user can edit any company's workspace settings.
    payload={'company_name':'Managed by VF','logo_data':'','show_pricing':True}
    assert c.put('/api/v1/workspace/settings',headers={**headers(4),'X-Company-Id':'1'},json=payload).status_code==200
    assert c.get('/api/v1/workspace/settings',headers=headers(1)).json()==payload
