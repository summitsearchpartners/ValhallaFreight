from app.models import Customer, MusePartnerCompany, MuseEnrollment, User
from app.services.muse_partner import initialize
from test_manufacturer import headers, setup
from test_accounts import account
from test_broker_roles import add_user

API='/api/v1'


def test_only_designated_muse_company_broker_admin_has_cross_company_access(setup):
    client,factory=setup
    muse=add_user(client,'broker_admin',2)
    other=add_user(client,'broker_admin',1)
    normal=add_user(client,'broker',2)
    with factory() as db:
        db.add(MuseEnrollment(customer_id=1,enabled=True,status='not_submitted'));db.commit()
    assert client.get(API+'/muse/manufacturers',headers=muse).status_code==403
    for h in (muse,other,normal,headers(1),headers(2),headers(5)):
        assert client.put(API+'/admin/muse-partner',headers=h,json={'company_id':2}).status_code==403
    designated=client.put(API+'/admin/muse-partner',headers=headers(4),json={'company_id':2})
    assert designated.status_code==200
    assert client.get(API+'/auth/me',headers=muse).json()['muse_partner_access'] is True
    assert client.get(API+'/auth/me',headers=other).json()['muse_partner_access'] is False
    assert client.get(API+'/auth/me',headers=normal).json()['muse_partner_access'] is False
    assert [r['manufacturer_id'] for r in client.get(API+'/muse/manufacturers',headers=muse).json()]==[1]
    assert client.get(API+'/muse/manufacturers/1',headers=muse).json()['manufacturer_name']=='Alpha'
    # Muse partner access does not remove broker isolation in its ordinary workspace.
    assert [q['id'] for q in client.get(API+'/quotes',headers=muse).json()]==[2]
    assert client.get(API+'/admin/users',headers=muse).status_code==403
    for h in (other,normal,headers(1),headers(2),headers(5)):
        assert client.get(API+'/muse/manufacturers',headers=h).status_code==403
    # Revocation takes effect on the backend even with an existing access token.
    client.put(API+'/admin/muse-partner',headers=headers(4),json={'company_id':None})
    assert client.get(API+'/muse/manufacturers',headers=muse).status_code==403
    assert client.get(API+'/auth/me',headers=muse).json()['muse_partner_access'] is False


def test_customer_portal_administration_is_super_only(setup):
    client,_=setup
    broker_admin=add_user(client,'broker_admin',1)
    for h in [headers(1),headers(2),headers(3),headers(5),broker_admin]:
        assert client.get(API+'/portal-administration/customers',headers=h).status_code==403
        assert client.get(API+'/portal-administration/customers/1',headers=h).status_code==403
        assert client.patch(API+'/portal-administration/customers/1',headers=h,json={'threshold':20}).status_code==403
    assert client.get(API+'/portal-administration/customers',headers=headers(4)).status_code==200
    detail=client.get(API+'/portal-administration/customers/1',headers=headers(4))
    assert detail.status_code==200 and detail.json()['customer']['customer']['name']=='Alpha'
    # Actual customer logins retain access to their own portal.
    assert client.get(API+'/portal/me',headers=headers(5)).status_code==200


def test_upgrade_designates_only_unambiguous_existing_muse_company_once(setup):
    _,factory=setup
    with factory() as db:
        db.get(Customer,2).name='Muse Freight'
        db.add(User(email='muse-upgrade@example.test',full_name='Muse Broker',role='broker_admin',customer_id=2,password_hash='test'))
        db.commit()
        initialize(db)
        assert db.get(MusePartnerCompany,1).company_id==2
        db.get(Customer,2).name='Renamed Muse Company'
        db.commit();initialize(db)
        assert db.get(MusePartnerCompany,1).company_id==2
        db.get(MusePartnerCompany,1).company_id=None
        db.get(Customer,2).name='Muse Freight';db.commit();initialize(db)
        assert db.get(MusePartnerCompany,1).company_id is None


def test_login_capability_and_assignment_changes(setup):
    client,_=setup
    created=client.post(API+'/admin/users',headers=headers(4),json=account(
        email='muse-broker@example.test',role='broker_admin',customer_id=2))
    assert created.status_code==201
    client.put(API+'/admin/muse-partner',headers=headers(4),json={'company_id':2})
    signed=client.post(API+'/auth/login',json={'email':'muse-broker@example.test','password':'InitialPassword123!'})
    assert signed.status_code==200 and signed.json()['user']['muse_partner_access']
    # Renaming or branding an unrelated company does not grant Muse permission.
    client.put(API+'/admin/users/'+str(created.json()['id']),headers=headers(4),json=account(email='muse-broker@example.test',role='broker_admin',customer_id=1))
    assert not client.get(API+'/auth/me',headers=headers(created.json()['id'])).json()['muse_partner_access']
