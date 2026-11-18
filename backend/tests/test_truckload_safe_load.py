from datetime import datetime,timedelta
from io import BytesIO
import pytest
from PIL import Image
from test_manufacturer import setup,headers
from app.models import Carrier,SafeLoadCase,Shipment,User
from app.services.auth import hash_password
from app.core.config import settings

BARCODE='@\nANSI 636000100002DL\nDAQTEST1234\nDAJKS\nDCSDOE\nDACJOHN\nDBA01012030\n'
VIN='1HGCM82633A004352'

@pytest.fixture
def freight(setup,tmp_path,monkeypatch):
    client,factory=setup
    monkeypatch.setattr(settings,'document_storage_path',str(tmp_path))
    with factory() as db:
        db.add(Carrier(id=1,name='Truckload Test Carrier',scac='FTLT',customer_id=1))
        db.add(User(id=8,email='broker@test.local',full_name='Broker',role='broker',customer_id=1,password_hash=hash_password('BrowserTest123!')))
        db.commit()
    return client,factory

def book(client):
    stops=[{'kind':kind,'name':name,'address1':street,'city':city,'state':state,'postal_code':zip,'appointment_at':date} for kind,name,street,city,state,zip,date in [
        ('pickup','Test warehouse','100 Main St','Olathe','KS','66061','2026-12-01T10:00:00'),
        ('delivery','Test customer','200 Main St','Dayton','OH','45414','2026-12-02T12:00:00')]]
    response=client.post('/api/v1/truckload',headers=headers(8),json={'customer_id':1,'equipment':'Dry van','commodity':'Palletized tools','weight_lbs':40000,'packages':20,'customer_price':'2500.00','stops':stops})
    assert response.status_code==200,response.text
    oid=response.json()['id']
    bids=client.post(f'/api/v1/truckload/{oid}/bids',headers=headers(8),json={'carrier_id':1,'carrier_cost':'2000.00','expires_at':(datetime.utcnow()+timedelta(days=1)).isoformat()})
    assert bids.status_code==200,bids.text
    bid=bids.json()['bids'][0]['id']
    assert client.post(f'/api/v1/truckload/{oid}/select',headers=headers(8),json={'bid_id':bid}).status_code==200
    booked=client.post(f'/api/v1/truckload/{oid}/book',headers=headers(8))
    assert booked.status_code==200,booked.text
    return oid,booked.json()['shipment_id']

def submit(client,sid,token=None,name='John Doe'):
    if token is None:
        inv=client.post(f'/api/v1/safe-load/shipments/{sid}/invite',headers=headers(8));assert inv.status_code==200,inv.text;token=inv.json()['token']
    photo=BytesIO();Image.new('RGB',(64,40),'gray').save(photo,'PNG')
    response=client.post('/api/v1/safe-load/carrier',headers={'X-Safe-Load-Token':token},data={'driver_name':name,'license_number':'TEST1234','issuing_state':'KS','license_expires':'2030-01-01','truck_vin':VIN},files={'photo':('license.png',photo.getvalue(),'image/png')})
    assert response.status_code==200,response.text
    return token,response.json()['revision']

def approve(client,sid,rev):
    result=client.post(f'/api/v1/safe-load/shipments/{sid}/approve-assignment',headers=headers(8),json={'revision':rev,'reason':'Confirmed by callback to the known carrier dispatcher.'})
    assert result.status_code==200,result.text

def test_full_truckload_safe_load_chain(freight):
    c,factory=freight;oid,sid=book(c)
    assert c.post(f'/api/v1/truckload/{oid}/book',headers=headers(8)).json()['shipment_id']==sid
    rows=c.get('/api/v1/safe-load',headers=headers(1)).json();assert rows[0]['status']=='awaiting_assignment'
    assert c.patch(f'/api/v1/shipments/{sid}',headers=headers(8),json={'status':'in_transit'}).status_code==409
    assert c.post(f'/api/v1/truckload/{oid}/stops/0/complete',headers=headers(8)).status_code==409
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(1),json={'revision':0}).status_code==409
    token,rev=submit(c,sid);approve(c,sid,rev)
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/photo',headers=headers(1)).content.startswith(b'\xff\xd8')
    matched=c.post(f'/api/v1/safe-load/shipments/{sid}/scan',headers=headers(1),json={'revision':rev,'license_barcode':BARCODE,'vin_barcode':VIN,'physical_id_matches_photo':True})
    assert matched.status_code==200,matched.text
    assert matched.json()['status']=='verified'
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(8),json={'revision':rev}).status_code==409
    released=c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(1),json={'revision':rev})
    assert released.status_code==200,released.text
    assert released.json()['status']=='released'
    assert c.get('/api/v1/safe-load/carrier',headers={'X-Safe-Load-Token':token}).status_code==403
    for index in (0,1):assert c.post(f'/api/v1/truckload/{oid}/stops/{index}/complete',headers=headers(8)).status_code==200
    assert c.get(f'/api/v1/shipments/{sid}',headers=headers(8)).json()['status']=='delivered'
    assert c.post(f'/api/v1/shipments/{sid}/customer-invoice',headers=headers(8)).status_code==200
    assert c.get(f'/api/v1/truckload/{oid}/rate-confirmation',headers=headers(8)).content.startswith(b'%PDF')
    with factory() as db:
        row=db.get(SafeLoadCase,sid)
        assert row.license_digest!='TEST1234' and row.license_last4=='1234'
        from pathlib import Path
        assert not Path(row.photo_path).read_bytes().startswith(b'\x89PNG')

@pytest.mark.parametrize('license_scan,vin,physical',[(BARCODE,'1HGCM82633A004353',True),(BARCODE.replace('TEST1234','WRONG999'),VIN,True),(BARCODE,VIN,False),('unreadable',VIN,True),(BARCODE.replace('01012030','01012020'),VIN,True)])
def test_rejects_mismatches_and_alerts_broker(freight,license_scan,vin,physical):
    c,_=freight;_,sid=book(c);_,rev=submit(c,sid);approve(c,sid,rev)
    response=c.post(f'/api/v1/safe-load/shipments/{sid}/scan',headers=headers(1),json={'revision':rev,'license_barcode':license_scan,'vin_barcode':vin,'physical_id_matches_photo':physical})
    assert response.json()['status']=='rejected',response.text
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(1),json={'revision':rev}).status_code==409
    assert c.patch(f'/api/v1/shipments/{sid}',headers=headers(4),json={'status':'delivered','delivered_at':'2026-12-02T12:00:00'}).status_code==409
    notices=c.get('/api/v1/notifications',headers=headers(8)).json()
    assert any('Safe Load rejected' in n['title'] for n in notices)
    assert 'TEST1234' not in str(notices)
    approve(c,sid,rev)
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/scan',headers=headers(1),json={'revision':rev,'license_barcode':BARCODE,'vin_barcode':VIN,'physical_id_matches_photo':True}).json()['status']=='verified'

def test_scope_tokens_revision_expiry_and_roles(freight):
    c,factory=freight;oid,sid=book(c);token,rev=submit(c,sid);approve(c,sid,rev)
    assert c.get('/api/v1/truckload',headers=headers(1)).status_code==403
    assert c.get('/api/v1/safe-load',headers=headers(3)).json()==[]
    assert c.get('/api/v1/safe-load',headers=headers(5)).status_code==403
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/photo',headers=headers(3)).status_code==404
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/invite',headers=headers(1)).status_code==403
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/approve-assignment',headers=headers(1),json={'revision':rev,'reason':'Invalid manufacturer approval'}).status_code==403
    _,newrev=submit(c,sid,token)
    assert newrev>rev
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/scan',headers=headers(1),json={'revision':rev,'license_barcode':BARCODE,'vin_barcode':VIN,'physical_id_matches_photo':True}).status_code==409
    approve(c,sid,newrev)
    c.post(f'/api/v1/safe-load/shipments/{sid}/scan',headers=headers(1),json={'revision':newrev,'license_barcode':BARCODE,'vin_barcode':VIN,'physical_id_matches_photo':True})
    with factory() as db:db.get(SafeLoadCase,sid).verified_until=datetime.utcnow()-timedelta(minutes=1);db.commit()
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(1),json={'revision':newrev}).status_code==409
    newtoken=c.post(f'/api/v1/safe-load/shipments/{sid}/invite',headers=headers(8)).json()['token']
    assert c.get('/api/v1/safe-load/carrier',headers={'X-Safe-Load-Token':token}).status_code==403
    assert c.get('/api/v1/safe-load/carrier',headers={'X-Safe-Load-Token':newtoken}).status_code==200

def test_status_alias_and_manual_tracking_cannot_bypass_release(freight):
    c,_=freight;_,sid=book(c)
    for status in ['In Transit','PICKED UP','released','Delivered','loaded']:
        response=c.patch(f'/api/v1/shipments/{sid}',headers=headers(4),json={'status':status})
        assert response.status_code==409,(status,response.text)
    result=c.post(f'/api/v1/shipments/{sid}/tracking',headers=headers(4),json={'code':'PICKED_UP','status':'Picked Up','event_time':datetime.utcnow().isoformat()})
    assert result.status_code==409,result.text

def test_realistic_aamva_header_and_scanner_prefix():
    from app.services.safe_load import decode_license,vin
    raw='@\n\x1e\rANSI 636026090102DL00410255ZA02960029DLDAQTEST1234\nDCSDOE\nDACJOHN\nDAJKS\nDBA01012030\n'
    assert decode_license(raw)['DAQ']=='TEST1234'
    assert vin(']C1VIN:'+VIN)==VIN
    with pytest.raises(ValueError):decode_license(BARCODE+'DAQAMBIGUOUS\n')

def test_new_ltl_booking_also_has_a_release_hold(freight):
    c,factory=freight
    from app.models import Quote
    with factory() as db:
        q=db.get(Quote,1);q.origin={'postal_code':'66061'};q.destination={'postal_code':'45414'};q.handling_units=[{'quantity':2,'weight_lbs':500,'freight_class':'70'}]
        q.options=[{'carrier_id':1,'carrier_cost':'200','customer_price':'250','transit_days':2}];db.commit()
    address={'address1':'100 Main St','city':'Olathe','state':'KS','postal_code':'66061','manual_confirmation':True}
    result=c.post('/api/v1/shipments',headers=headers(1),json={'quote_number':'Q1','carrier_id':1,'origin':address,'destination':{**address,'postal_code':'45414'}})
    assert result.status_code==200,result.text
    sid=result.json()['id']
    assert c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['status']=='awaiting_assignment'
    assert c.patch(f'/api/v1/shipments/{sid}',headers=headers(1),json={'actual_pickup_at':datetime.utcnow().isoformat()}).status_code==409

def test_only_designated_muse_broker_admin_can_manage_actual_muse_shipments(freight):
    c,factory=freight;_,sid=book(c)
    from app.models import MuseBooking,MusePartnerCompany
    with factory() as db:
        db.add(User(id=9,email='muse9@test.local',full_name='Muse Broker Admin',role='broker_admin',customer_id=2,password_hash=hash_password('BrowserTest123!')))
        db.add(MusePartnerCompany(id=1,company_id=2));db.add(MuseBooking(customer_id=1,shipment_id=sid,status='requested'));db.commit()
    queue=c.get('/api/v1/safe-load',headers=headers(9));assert queue.status_code==200,queue.text
    assert queue.json()[0]['shipment_id']==sid
    invite=c.post(f'/api/v1/safe-load/shipments/{sid}/invite',headers=headers(9));assert invite.status_code==200,invite.text
    _,rev=submit(c,sid,invite.json()['token'])
    response=c.post(f'/api/v1/safe-load/shipments/{sid}/approve-assignment',headers=headers(9),json={'revision':rev,'reason':'Confirmed identity with the assigned Muse carrier dispatcher.'})
    assert response.status_code==200,response.text
    rejected=c.post(f'/api/v1/safe-load/shipments/{sid}/scan',headers=headers(1),json={'revision':rev,'license_barcode':BARCODE,'vin_barcode':VIN+'x','physical_id_matches_photo':True})
    assert rejected.json()['status']=='rejected'
    assert any('Safe Load rejected' in row['title'] for row in c.get('/api/v1/notifications',headers=headers(9)).json())
    assert c.get('/api/v1/safe-load',headers=headers(3)).json()==[]
    notice=next(row for row in c.get('/api/v1/notifications',headers=headers(9)).json() if 'Safe Load rejected' in row['title'])
    assert c.post(f"/api/v1/notifications/ops/{notice['id']}/read",headers=headers(9)).status_code==200
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/approve-assignment',headers=headers(9),json={'revision':rev,'reason':'Callback resolved the VIN mismatch. Rechecking the vehicle.'}).status_code==200
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/scan',headers=headers(9),json={'revision':rev,'license_barcode':BARCODE,'vin_barcode':VIN,'physical_id_matches_photo':True}).json()['status']=='verified'
    release=c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(9),json={'revision':rev})
    assert release.status_code==200,release.text

def test_booked_quotes_cannot_be_edited_and_invalid_equipment_rejected(freight):
    c,_=freight;oid,_=book(c)
    row=c.get(f'/api/v1/truckload/{oid}',headers=headers(8)).json()
    payload={k:row[k] for k in ['customer_id','reference','equipment','commodity','weight_lbs','packages','customer_price','stops','notes']}
    assert c.patch(f'/api/v1/truckload/{oid}',headers=headers(8),json=payload).status_code==409
    payload['equipment']='Reefer'
    assert c.post('/api/v1/truckload',headers=headers(8),json=payload).status_code==422
    payload['equipment']='Dry van'
    new=c.post('/api/v1/truckload',headers=headers(8),json=payload).json()
    bid=c.post(f"/api/v1/truckload/{new['id']}/bids",headers=headers(8),json={'carrier_id':1,'carrier_cost':'1800.00','expires_at':(datetime.utcnow()+timedelta(days=1)).isoformat()}).json()['bids'][0]
    assert c.patch(f"/api/v1/truckload/{new['id']}",headers=headers(8),json={**payload,'weight_lbs':45000}).status_code==200
    assert c.post(f"/api/v1/truckload/{new['id']}/select",headers=headers(8),json={'bid_id':bid['id']}).status_code==409

def test_cancellation_revokes_carrier_link_and_release(freight):
    c,_=freight;oid,sid=book(c);token,_=submit(c,sid)
    assert c.patch(f'/api/v1/shipments/{sid}',headers=headers(8),json={'status':'cancelled'}).status_code==200
    assert c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['status']=='cancelled'
    assert c.get('/api/v1/safe-load/carrier',headers={'X-Safe-Load-Token':token}).status_code==403
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(1),json={'revision':1}).status_code==409
    assert c.get(f'/api/v1/truckload/{oid}',headers=headers(8)).json()['status']=='cancelled'

def test_additional_pickups_are_rejected_instead_of_bypassing_a_warehouse_gate(freight):
    c,_=freight;oid,_=book(c)
    row=c.get(f'/api/v1/truckload/{oid}',headers=headers(8)).json()
    payload={k:row[k] for k in ['customer_id','reference','equipment','commodity','weight_lbs','packages','customer_price','stops','notes']}
    extra={**payload['stops'][0],'appointment_at':'2026-12-01T12:00:00'}
    payload['stops']=[payload['stops'][0],extra,payload['stops'][1]]
    response=c.post('/api/v1/truckload',headers=headers(8),json=payload)
    assert response.status_code==422 and 'one pickup' in response.text
