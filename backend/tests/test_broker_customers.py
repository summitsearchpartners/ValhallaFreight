import pytest
from test_manufacturer import setup,headers
from app.models import Customer,User,Carrier,Quote,BrokerCustomerAssignment,CarrierRateControl
from app.services.auth import hash_password
from app.core.config import settings
from test_truckload_safe_load import book,submit,approve,BARCODE,VIN

@pytest.fixture
def linked(setup,tmp_path,monkeypatch):
    client,factory=setup
    monkeypatch.setattr(settings,'document_storage_path',str(tmp_path))
    with factory() as db:
        db.add_all([Customer(id=3,code='BROKER',name='Test Brokerage'),Customer(id=4,code='OTHER',name='Other Brokerage')]);db.flush()
        db.add_all([User(id=8,email='broker@test.local',full_name='Broker Test',role='broker_admin',customer_id=3,password_hash=hash_password('BrowserTest123!')),User(id=9,email='other@test.local',full_name='Other Broker',role='broker',customer_id=4,password_hash=hash_password('BrowserTest123!'))]);db.add(Carrier(id=1,name='Broker Private Carrier',scac='BPRV',customer_id=3));db.commit()
    return client,factory

def assign(c):
    response=c.post('/api/v1/admin/broker-companies/3/customers',headers=headers(4),json={'customer_id':1})
    assert response.status_code==201,response.text

def test_assign_scope_and_revoke(linked):
    c,factory=linked
    assert c.get('/api/v1/quotes/1',headers=headers(8)).status_code==404
    assign(c)
    directory=c.get('/api/v1/admin/broker-customers',headers=headers(4)).json()
    assert any(b['id']==3 and b['accounts'][0]['email']=='broker@test.local' for b in directory['brokers'])
    assert next(x for x in directory['customers'] if x['id']==1)['broker_company_id']==3
    assert [x['id'] for x in c.get('/api/v1/customers',headers=headers(8)).json()]==[1]
    assert c.get('/api/v1/customers/1/360',headers=headers(8)).status_code==200
    assert c.get('/api/v1/quotes/1',headers=headers(8)).status_code==200
    assert c.get('/api/v1/quotes/2',headers=headers(8)).status_code==404
    assert c.get('/api/v1/quotes/1',headers=headers(9)).status_code==404
    assert c.get('/api/v1/quotes/2',headers=headers(1)).status_code==404
    assert c.patch('/api/v1/customers/1',headers=headers(8),json={'industry':'Industrial'}).status_code==200
    assert c.post('/api/v1/customers/1/locations',headers=headers(8),json={'name':'Assigned dock','location_type':'shipper','address1':'100 Main Street','city':'Olathe','state':'KS','postal_code':'66061','country':'USA'}).status_code==201
    assert c.post('/api/v1/admin/broker-companies/4/customers',headers=headers(4),json={'customer_id':1}).status_code==409
    assert c.delete('/api/v1/admin/broker-companies/3/customers/1',headers=headers(4)).status_code==200
    assert c.get('/api/v1/quotes/1',headers=headers(8)).status_code==404
    assert c.get('/api/v1/quotes/1',headers=headers(1)).status_code==200
    with factory() as db:
        assert db.get(Customer,1).manufacturer_id is None
        assert db.get(User,1).role=='manufacturer_admin'
        assert db.get(User,1).customer_id==1
        assert db.get(Quote,1) is not None

@pytest.mark.parametrize('uid',[1,2,5,8,9])
def test_only_super_admin_manages_assignments(linked,uid):
    c,_=linked
    assert c.get('/api/v1/admin/broker-customers',headers=headers(uid)).status_code==403
    assert c.post('/api/v1/admin/broker-companies/3/customers',headers=headers(uid),json={'customer_id':1}).status_code==403
    assert c.delete('/api/v1/admin/broker-companies/3/customers/1',headers=headers(uid)).status_code==403

def test_create_customer_and_invalid_targets(linked):
    c,factory=linked
    assert c.post('/api/v1/admin/broker-companies/1/customers',headers=headers(4),json={'customer_id':2}).status_code==422
    assert c.post('/api/v1/admin/broker-companies/3/customers',headers=headers(4),json={'customer_id':4}).status_code==422
    r=c.post('/api/v1/admin/broker-companies/3/customers',headers=headers(4),json={'name':'New Customer'})
    assert r.status_code==201,r.text
    cid=r.json()['customer_id']
    assert cid in [x['id'] for x in c.get('/api/v1/customers',headers=headers(8)).json()]
    assert c.get(f'/api/v1/customers/{cid}/360',headers=headers(9)).status_code==404
    assert c.get(f'/api/v1/customers/{cid}/360',headers=headers(1)).status_code==404
    with factory() as db:assert db.get(BrokerCustomerAssignment,cid).broker_company_id==3

def test_linked_manufacturer_safe_load_release_and_financial_privacy(linked):
    c,factory=linked;assign(c);oid,sid=book(c)
    assert c.get('/api/v1/safe-load',headers=headers(9)).json()==[]
    _,rev=submit(c,sid);approve(c,sid,rev)
    detail=c.get(f'/api/v1/shipments/{sid}',headers=headers(1));assert detail.status_code==200,detail.text
    assert 'carrier_cost' not in detail.json()
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/scan',headers=headers(1),json={'revision':rev,'license_barcode':BARCODE,'vin_barcode':VIN,'physical_id_matches_photo':True}).status_code==200
    release=c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(1),json={'revision':rev});assert release.status_code==200,release.text
    assert c.get('/api/v1/safe-load',headers=headers(8)).json()[0]['status']=='released'

def test_ltl_rating_uses_assigned_broker_carriers(linked):
    c,factory=linked;assign(c)
    with factory() as db:
        db.add(Carrier(id=2,name='Manufacturer Hidden Carrier',scac='MHID',customer_id=1));db.flush()
        db.add(CarrierRateControl(carrier_id=2,hide_rates=True));db.commit()
    address={'address1':'','city':'','state':'','postal_code':'66061'}
    payload={'customer_id':1,'origin':address,'destination':{**address,'postal_code':'45414'},'handling_units':[{'quantity':2,'weight_lbs':500,'length_in':48,'width_in':40,'height_in':42,'freight_class':'70'}]}
    response=c.post('/api/v1/quotes/rate',headers=headers(8),json=payload)
    assert response.status_code==200,response.text
    assert any(option['carrier_id']==1 for option in response.json()['options'])
    assert not any(option['carrier_id']==2 for option in response.json()['options'])
    denied=c.post('/api/v1/quotes/rate',headers=headers(9),json=payload)
    assert denied.status_code in {400,404},denied.text

def test_child_customers_inherit_without_manufacturer_scope_expansion(linked):
    c,factory=linked
    with factory() as db:
        db.add(Customer(id=5,code='CHILD',name='Manufacturer customer',manufacturer_id=1));db.flush()
        db.add(Quote(id=5,quote_number='CHILD-Q',customer_id=5,origin={},destination={},handling_units=[],options=[],accessorials=[]));db.commit()
    assign(c)
    assert c.get('/api/v1/quotes/5',headers=headers(8)).status_code==200
    assert c.get('/api/v1/quotes/5',headers=headers(9)).status_code==404
    assert c.get('/api/v1/quotes/2',headers=headers(1)).status_code==404
    assert c.delete('/api/v1/admin/broker-companies/3/customers/1',headers=headers(4)).status_code==200
    assert c.get('/api/v1/quotes/5',headers=headers(8)).status_code==404
    assert c.get('/api/v1/quotes/5',headers=headers(1)).status_code==200

def test_revocation_preserves_manufacturer_release_of_existing_load(linked):
    c,_=linked;assign(c);_,sid=book(c);_,rev=submit(c,sid);approve(c,sid,rev)
    assert c.delete('/api/v1/admin/broker-companies/3/customers/1',headers=headers(4)).status_code==200
    assert c.get('/api/v1/safe-load',headers=headers(8)).json()==[]
    matched=c.post(f'/api/v1/safe-load/shipments/{sid}/scan',headers=headers(1),json={'revision':rev,'license_barcode':BARCODE,'vin_barcode':VIN,'physical_id_matches_photo':True})
    assert matched.status_code==200,matched.text
    released=c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(1),json={'revision':rev})
    assert released.status_code==200,released.text
    assert released.json()['status']=='released'
