import os
os.environ['DATABASE_URL']='sqlite://'
from types import SimpleNamespace
import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.base import Base
from app.db.session import get_db
from app.models import Customer, User, Quote
from app.services.auth import hash_password, create_access_token

@pytest.fixture
def setup():
    engine=create_engine('sqlite://',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory=sessionmaker(bind=engine,autoflush=False)
    with engine.begin() as c:
        for table,key in [('workspace_settings','user_id'),('company_workspace_settings','customer_id')]:
            c.execute(text(f"CREATE TABLE {table} ({key} INTEGER PRIMARY KEY, company_name TEXT, logo_data TEXT, show_pricing BOOLEAN)"))
    with factory() as db:
        db.add_all([Customer(id=1,code='A',name='Alpha'),Customer(id=2,code='B',name='Beta')]);db.flush()
        for i,role,cid in [(1,'manufacturer_admin',1),(2,'manufacturer',1),(3,'manufacturer_admin',2),(4,'admin',None),(5,'customer',1),(6,'broker',None),(7,'manufacturer',None)]:
            db.add(User(id=i,email=f'{i}@test.local',full_name=f'User {i}',role=role,customer_id=cid,password_hash=hash_password('Original12345!')))
        for i in [1,2]:db.add(Quote(id=i,quote_number=f'Q{i}',customer_id=i,origin={},destination={},handling_units=[],options=[],accessorials=[]))
        db.commit()
    def dependency(request:Request):
        with factory() as db:
            db.info['request']=request
            request.state.activity_engine=engine
            yield db
    app.dependency_overrides[get_db]=dependency
    yield TestClient(app),factory
    app.dependency_overrides.clear()

def headers(uid):return {'Authorization':'Bearer '+create_access_token(uid,'test','admin')}

def test_shared_settings_and_roles(setup):
    client,_=setup
    payload={'company_name':'Alpha Freight','logo_data':'','show_pricing':True}
    assert client.put('/api/v1/workspace/settings',headers=headers(1),json=payload).status_code==200
    assert client.get('/api/v1/workspace/settings',headers=headers(2)).json()==payload
    assert not client.get('/api/v1/workspace/settings',headers=headers(3)).json()['show_pricing']
    assert client.put('/api/v1/workspace/settings',headers=headers(2),json=payload).status_code==403
    assert client.get('/api/v1/pricing-rules',headers=headers(2)).status_code==403
    assert client.get('/api/v1/pricing-rules',headers=headers(3)).status_code==403
    assert client.post('/api/v1/pricing-rules',headers=headers(2),json={}).status_code==403

def test_company_queries_and_direct_ids(setup):
    client,_=setup
    assert [q['id'] for q in client.get('/api/v1/quotes',headers=headers(1)).json()]==[1]
    assert client.get('/api/v1/quotes/2',headers=headers(1)).status_code==404
    assert len(client.get('/api/v1/quotes',headers=headers(4)).json())==2
    assert client.get('/api/v1/quotes',headers=headers(6)).status_code==403
    assert client.get('/api/v1/quotes',headers=headers(5)).status_code==403
    assert client.get('/api/v1/quotes',headers=headers(7)).status_code==403

@pytest.mark.parametrize('path',['/capacity','/prospects','/carrier-360','/finance/email-outbox'])
def test_restricted_modules(setup,path):
    client,_=setup
    # Some modules expose only nested paths; test dependency directly as well.
    from app.api.permissions import internal_access
    req=Request({'type':'http','path':'/api/v1'+path,'method':'GET','headers':[]})
    with pytest.raises(HTTPException):internal_access(req,SimpleNamespace(role='manufacturer_admin',customer_id=1),None)

def test_profile_and_password(setup):
    client,_=setup
    assert client.put('/api/v1/workspace/profile',headers=headers(2),json={'full_name':'Updated User'}).json()['full_name']=='Updated User'
    assert client.get('/api/v1/auth/me',headers=headers(2)).json()['full_name']=='Updated User'
    assert client.put('/api/v1/workspace/profile',headers=headers(2),json={'full_name':'  '}).status_code==422
    assert client.put('/api/v1/workspace/password',headers=headers(2),json={'current_password':'wrong','new_password':'NewPassword123!'}).status_code==400
    assert client.put('/api/v1/workspace/password',headers=headers(2),json={'current_password':'Original12345!','new_password':'NewPassword123!'}).status_code==200
    assert client.post('/api/v1/auth/login',json={'email':'2@test.local','password':'NewPassword123!'}).status_code==200

def test_write_and_aggregate_isolation(setup):
    _,factory=setup
    req=SimpleNamespace(state=SimpleNamespace(auth_user=SimpleNamespace(role='manufacturer_admin',customer_id=1)))
    with factory() as db:
        db.info['request']=req
        assert db.query(func.count(Quote.id)).scalar()==1
        assert db.get(Quote,2) is None
        db.add(Quote(quote_number='BAD',customer_id=2,origin={},destination={},handling_units=[]))
        with pytest.raises(HTTPException):db.commit()

def test_logo_validation(setup):
    client,_=setup
    assert client.put('/api/v1/workspace/settings',headers=headers(1),json={'company_name':'Alpha','logo_data':'data:image/png;base64,bm90YW5pbWFnZQ==','show_pricing':False}).status_code==422

@pytest.mark.parametrize("owned_customer",[False,True])
def test_quote_multiple_classes_booking_and_bol(setup, monkeypatch,owned_customer):
    client,factory=setup
    from app.models import Carrier
    from app.schemas.entities import RateOption
    from app.services.rating import RatingEngine
    from app.api.routes import shipments
    async def rates(self,payload):
        return [RateOption(carrier_id=1,carrier_name='Test Carrier',scac='TEST',service='LTL',transit_days=2,base_charge=100,fuel=10,accessorials=0,carrier_cost=110,customer_price=150,gross_profit=40,margin_pct=26.67)]
    async def submit(db,shipment):return None
    monkeypatch.setattr(RatingEngine,'get_rates',rates)
    monkeypatch.setattr(shipments,'submit_shipment_to_carrier',submit)
    with factory() as db:
        db.add(Carrier(id=1,scac='TEST',name='Test Carrier'));db.commit()
    customer_id=1
    if owned_customer:
        customer_id=client.post('/api/v1/customers',headers=headers(1),json={'name':'Shipment customer'}).json()['id']
    address={'address1':'100 Main St','city':'Kansas City','state':'KS','postal_code':'66101','verified_postal_code':'66101'}
    units=[{'quantity':1,'type':'Pallet','weight_lbs':500,'length_in':48,'width_in':40,'height_in':48,'freight_class':c} for c in ['70','125']]
    response=client.post('/api/v1/quotes/rate',headers=headers(1),json={'customer_id':customer_id,'origin':address,'destination':address,'handling_units':units})
    assert response.status_code==200,response.text
    option=response.json()['options'][0]
    assert float(option['customer_price']) == 150
    assert not {'carrier_cost','gross_profit','margin_pct','base_charge','fuel'} & option.keys()
    quote=response.json()['quote_number']
    broker_quote=client.get('/api/v1/quotes/'+quote,headers=headers(4)).json()
    assert float(broker_quote['options'][0]['carrier_cost'])==110
    assert float(broker_quote['options'][0]['gross_profit'])==40
    result=client.post('/api/v1/shipments',headers=headers(1),json={'quote_number':quote,'carrier_id':1,'origin':address,'destination':address})
    assert result.status_code==200,result.text
    shipment=result.json()
    assert len(shipment['handling_units'])==2
    assert shipment['bol_number'].isdigit()
    detail=client.get(f"/api/v1/shipments/{shipment['id']}",headers=headers(1))
    assert detail.status_code==200
    assert detail.json()['bol_number']==shipment['bol_number']
    assert client.get(f"/api/v1/shipments/{shipment['id']}",headers=headers(3)).status_code==404
