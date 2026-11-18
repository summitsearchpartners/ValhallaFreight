import asyncio
from datetime import datetime
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from test_manufacturer import setup,headers
from app.models import Quote, Carrier, Shipment
from app.services.freight_totals import confirmed_package_count

ADDRESS={'address1':'100 Main Street','city':'Olathe','state':'KS','postal_code':'66061','manual_confirmation':True}
UNITS=[{'quantity':2,'type':'Pallet','weight_lbs':500,'length_in':48,'width_in':40,'height_in':48,'freight_class':'70'},
       {'quantity':1,'type':'Crate','weight_lbs':300,'length_in':30,'width_in':30,'height_in':30,'freight_class':'125'}]

def prepare(factory):
    with factory() as db:
        db.add(Carrier(id=1,name='Test Carrier',scac='TEST'))
        q=db.get(Quote,1);q.origin={'postal_code':'66061'};q.destination={'postal_code':'45414'};q.handling_units=UNITS
        q.options=[{'carrier_id':1,'carrier_cost':'100','customer_price':'150','transit_days':2}]
        db.commit()
    return {'quote_number':'Q1','carrier_id':1,'origin':ADDRESS,'destination':{**ADDRESS,'postal_code':'45414'}}

@pytest.mark.parametrize('uid',[1,2])
def test_manual_booking_totals_and_bol_without_google(setup,uid):
    c,factory=setup;payload=prepare(factory)
    result=c.post('/api/v1/shipments',headers=headers(uid),json=payload)
    assert result.status_code==200,result.text
    row=result.json();assert row['package_count']==3 and row['bol_number'].isdigit()
    assert row['origin']['manual_confirmation'] is True
    assert row['handling_units']==UNITS
    detail=c.get(f"/api/v1/shipments/{row['id']}",headers=headers(uid)).json()
    assert detail['package_count']==3 and detail['invoice_issued'] is False
    assert 'carrier_cost' not in detail and 'gross_profit' not in detail
    changed=c.patch(f"/api/v1/shipments/{row['id']}",headers=headers(uid),json={'package_count':99})
    assert changed.status_code==422


def test_booking_rejects_wrong_zip_missing_confirmation_and_count(setup):
    c,factory=setup;payload=prepare(factory)
    for origin in [{**ADDRESS,'manual_confirmation':False},{**ADDRESS,'address1':' '},{**ADDRESS,'postal_code':'66062'}]:
        result=c.post('/api/v1/shipments',headers=headers(1),json={**payload,'origin':origin})
        assert result.status_code in (400,422),result.text
    mismatch=c.post('/api/v1/shipments',headers=headers(1),json={**payload,'package_count':2})
    assert mismatch.status_code==422 and 'freight lines (3)' in mismatch.text
    with factory() as db:assert db.query(Shipment).count()==0
    assert c.post('/api/v1/shipments',headers=headers(1),json={**payload,'package_count':3}).status_code==200

@pytest.mark.parametrize('value',[0,-1,1.5,None])
def test_invalid_freight_quantity(value):
    with pytest.raises(HTTPException):confirmed_package_count([{'quantity':value}])


def test_dayton_totals_test_status_and_fail_response(monkeypatch):
    import app.integrations.carriers.dayton as module
    adapter=module.DaytonAdapter()
    monkeypatch.setattr(adapter,'client',lambda:SimpleNamespace(has_credentials=True,account='ABC'))
    s=SimpleNamespace(origin=ADDRESS,destination=ADDRESS,handling_units=UNITS,scheduled_pickup_at=None,created_at=datetime(2026,11,12),
                      commodity_description='Tools',hazmat_emergency_contact=None,package_type='Pallet',nmfc_number=None,
                      customer=SimpleNamespace(name='Manufacturer'),payment_terms='Prepaid',pro_number=None,shipment_number='TEST',bol_number='10000001',
                      po_number='PO123',package_count=3,customer_reference=None,declared_value=None)
    sent=[]
    async def fake(payload,client):
        sent.append(payload);return {'messageStatus':{'status':'PASS'},'referenceNumbers':{'pro':'123'}}
    monkeypatch.setattr(module,'create_standard',fake)
    result=asyncio.run(adapter.book_shipment(s))
    assert result['is_test'] is True
    p=sent[0];assert p['shipmentTotals']['grossWeight']==1300 and p['shipmentTotals']['handlingUnits']==3
    assert [u['weight'] for u in p['commodities']['handlingUnits']]==[1000,300]
    assert [u['lineItems'][0]['weight'] for u in p['commodities']['handlingUnits']]==[1000,300]
    assert p['referenceNumbers']['po'][0]['pieces']==3
    async def fail(payload,client):return {'messageStatus':{'status':'FAIL','message':'Invalid request'}}
    monkeypatch.setattr(module,'create_standard',fail)
    with pytest.raises(ValueError,match='did not accept'):asyncio.run(adapter.book_shipment(s))


def test_sandbox_submission_and_invoice_permissions(setup,monkeypatch):
    c,factory=setup;payload=prepare(factory)
    import app.integrations.shipment_booking as booking
    class Adapter:
        async def book_shipment(self,shipment,db=None):
            return {'is_test':True,'pro_number':'TEST-PRO','provider_reference':'TEST-REF'}
    monkeypatch.setattr(booking,'get_carrier',lambda code:Adapter())
    with factory() as db:db.get(Carrier,1).api_enabled=True;db.commit()
    row=c.post('/api/v1/shipments',headers=headers(1),json=payload).json()
    sid=row['id']
    detail=c.get(f'/api/v1/shipments/{sid}',headers=headers(1)).json()
    assert detail['carrier_submissions'][0]['status']=='test_submitted'
    assert detail['carrier_submissions'][0]['is_test'] is True
    assert c.post(f'/api/v1/shipments/{sid}/customer-invoice',headers=headers(1)).status_code==403
    path=f'/api/v1/shipments/{sid}/customer-invoice'
    first=c.post(path,headers=headers(4));assert first.status_code==200,first.text
    assert first.json()['invoice_issued'] is True
    assert float(first.json()['customer_invoice']['amount'])==150
    second=c.post(path,headers=headers(4));assert second.status_code==200
    assert first.json()['customer_invoice']['invoice_number']==second.json()['customer_invoice']['invoice_number']
    invoices=c.get('/api/v1/finance/customer-invoices',headers=headers(1)).json()
    assert len(invoices)==1 and invoices[0]['status']=='issued'
    assert c.get('/api/v1/finance/customer-invoices',headers=headers(3)).json()==[]
