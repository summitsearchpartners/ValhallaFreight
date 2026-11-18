from pathlib import Path
import pytest
from test_manufacturer import setup,headers
from test_truckload_safe_load import freight,BARCODE
from test_safe_load_photos import prepared,packet,photo
from test_safe_load_camera import encoded
from app.models import SafeLoadBackPhoto,SafeLoadPhotoAttempt
import zxingcpp

def with_back(rev,code=BARCODE):
    p=packet(rev);p['files']['license_back_photo']=('id-back.png',encoded(code,zxingcpp.BarcodeFormat.PDF417),'image/png');return p

def test_back_barcode_drives_qa_is_encrypted_scoped_and_in_custody(freight):
    c,factory=freight;sid,rev=prepared(c)
    p=with_back(rev);p['files']['license_photo']=('front.jpg',photo(['TEST FRONT IMAGE - OCR UNREADABLE']),'image/jpeg')
    response=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**p)
    assert response.status_code==200,response.text
    row=response.json();assert row['status']=='released',row
    assert row['photo_review']['extraction']['reader']=='id_back_pdf417'
    aid=row['photo_review']['id']
    image=c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/license-back',headers=headers(8))
    assert image.status_code==200 and image.content.startswith(b'\xff\xd8')
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/license-back',headers=headers(3)).status_code==404
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts',headers=headers(8)).json()[0]['has_back_photo']
    with factory() as db:assert not Path(db.get(SafeLoadBackPhoto,aid).path).read_bytes().startswith(b'\xff\xd8')
    chain=c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(8)).json()
    assert chain['integrity']['valid']
    assert any('license_back' in s['payload']['arrival_photos'] for s in chain['snapshots'])

@pytest.mark.parametrize('kind',['unreadable','wrong_number','expired','missing_name'])
def test_bad_back_photo_keeps_hold_and_evidence(freight,kind):
    c,factory=freight;sid,rev=prepared(c)
    code=BARCODE.replace('TEST1234','OTHER999') if kind=='wrong_number' else BARCODE.replace('01012030','01012020') if kind=='expired' else BARCODE.replace('DACJOHN\n','') if kind=='missing_name' else BARCODE
    p=with_back(rev,code)
    if kind=='unreadable':p['files']['license_back_photo']=('blank.jpg',photo(['NO READABLE BARCODE']),'image/jpeg')
    row=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**p)
    assert row.status_code==200,row.text
    assert row.json()['status']=='rejected' and row.json()['photo_review']['reasons']
    with factory() as db:assert db.get(SafeLoadBackPhoto,row.json()['photo_review']['id']) is not None

def test_wrong_front_barcode_cannot_be_overridden_by_correct_back(freight):
    c,_=freight;sid,rev=prepared(c);p=with_back(rev)
    p['files']['license_photo']=('front.png',encoded(BARCODE.replace('TEST1234','OTHER999'),zxingcpp.BarcodeFormat.PDF417),'image/png')
    r=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**p)
    assert r.status_code==200 and r.json()['status']=='rejected',r.text
    assert 'disagree' in str(r.json()['photo_review']['reasons'])

def test_designated_muse_reviewer_can_access_back_photo_only_for_booked_load(freight):
    from app.models import User,MusePartnerCompany,MuseBooking
    from app.services.auth import hash_password
    c,factory=freight;sid,rev=prepared(c)
    with factory() as db:
        db.add(User(id=9,email='muse@back.test',full_name='Muse Reviewer',role='broker_admin',customer_id=2,password_hash=hash_password('BrowserTest123!')))
        db.add(MusePartnerCompany(id=1,company_id=2));db.add(MuseBooking(customer_id=1,shipment_id=sid,status='requested'));db.commit()
    row=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**with_back(rev)).json();aid=row['photo_review']['id']
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/license-back',headers=headers(9)).status_code==200
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/license-back',headers=headers(3)).status_code==404
    assert c.get('/api/v1/safe-load/capture-features',headers=headers(1)).json()['id_back_photo']
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(9)).json()['integrity']['valid']
