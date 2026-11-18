from pathlib import Path
import pytest
from test_manufacturer import setup,headers
from test_truckload_safe_load import freight,BARCODE,VIN,book,submit
from test_safe_load_photos import prepared,packet,photo
from test_safe_load_custody import decision
from app.models import SafeLoadReleaseReceipt,SafeLoadPhotoExtraction
from app.services.safe_load_progress import read

SCAN=BARCODE+'DBB01011990\nDADALAN\n'
def with_scan(rev,code=SCAN,vin=VIN,job='a'*32):
    p=packet(rev,license=photo(['TEST IMAGE - UNREADABLE FRONT']))
    p['data'].update({'license_barcode':code,'vin_barcode':vin,'upload_id':job})
    return p

def test_barcode_preview_extracts_dob_without_persistence_or_scope_leak(freight):
    c,factory=freight;sid,rev=prepared(c)
    url=f'/api/v1/safe-load/shipments/{sid}/license-barcode/preview'
    r=c.post(url,headers=headers(1),json={'revision':rev,'barcode':SCAN});assert r.status_code==200,r.text
    assert r.json()['date_of_birth']=='1990-01-01' and r.json()['first_name']=='JOHN' and r.json()['middle_name']=='ALAN'
    assert 'no-store' in r.headers['cache-control']
    assert c.post(url,headers=headers(3),json={'revision':rev,'barcode':SCAN}).status_code==404
    assert c.post(url,headers=headers(1),json={'revision':rev+1,'barcode':SCAN}).status_code==409
    assert c.post(url,headers=headers(1),json={'revision':rev,'barcode':'bad scan'}).status_code==422
    assert c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['status']!='released'

def test_scan_supplements_photos_and_records_confirmation_progress_custody(freight):
    c,factory=freight;sid,rev=prepared(c)
    result=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**with_scan(rev))
    assert result.status_code==200,result.text
    row=result.json();assert row['status']=='released',row
    assert row['confirmation_number'].startswith('SL-')
    with factory() as db:
        receipt=db.get(SafeLoadReleaseReceipt,sid);assert receipt.confirmation_number==row['confirmation_number']
        extraction=db.get(SafeLoadPhotoExtraction,row['photo_review']['id']);assert extraction.summary['reader']=='onsite_pdf417_scan'
        assert '1990' not in str(extraction.summary)
    progress=c.get(f'/api/v1/safe-load/shipments/{sid}/photo-progress/'+('a'*32),headers=headers(1))
    assert progress.status_code==200 and progress.json()['percent']==100
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/photo-progress/'+('a'*32),headers=headers(8)).json()['percent']==0
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/photo-progress/'+('a'*32),headers=headers(3)).status_code==404
    chain=c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(8)).json();assert chain['integrity']['valid']
    assert any(s['payload'].get('confirmation_number')==row['confirmation_number'] for s in chain['snapshots'])
    again=c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(1),json={'revision':rev}).json()
    assert again['confirmation_number']==row['confirmation_number']

@pytest.mark.parametrize('code,vin',[(SCAN.replace('TEST1234','WRONG123'),VIN),(SCAN,VIN[:-1]+'3'),('bad scan',VIN),(SCAN.replace('DBA01012030','DBA01012020'),VIN)])
def test_scan_mismatch_malformed_expired_or_wrong_vin_keeps_hold(freight,code,vin):
    c,factory=freight;sid,rev=prepared(c)
    r=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**with_scan(rev,code,vin))
    assert r.status_code==200,r.text
    assert r.json()['status']=='rejected' and not r.json()['confirmation_number']
    assert r.json()['broker_contact']['phone']
    with factory() as db:assert db.get(SafeLoadReleaseReceipt,sid) is None

def test_rejected_retry_stays_held_and_broker_release_gets_receipt(freight):
    c,_=freight;sid,rev=prepared(c)
    first=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**with_scan(rev,vin=VIN[:-1]+'3')).json()
    retry=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**with_scan(rev)).json()
    assert retry['status']=='rejected'
    released=c.post(f'/api/v1/safe-load/shipments/{sid}/broker-release',headers=headers(8),json=decision(rev,retry))
    assert released.status_code==200,released.text
    assert released.json()['confirmation_number'] and released.json()['shipment_status']=='in_transit'

def test_real_workflow_milestones_and_photo_barcode_conflict(freight,monkeypatch):
    from app.services import safe_load_progress,safe_load_images,safe_load
    c,_=freight;sid,rev=prepared(c);stages=[]
    original=safe_load_progress.update
    def record(uid,sid,job,percent,label):stages.append(percent);original(uid,sid,job,percent,label)
    monkeypatch.setattr(safe_load_progress,'update',record)
    # A different PDF417 detected inside the photograph cannot be overridden by
    # a matching separate scan. This checks conflict behavior, not OCR quality.
    monkeypatch.setattr(safe_load_images,'barcodes',lambda raw,license_only=False:[SCAN.replace('TEST1234','OTHER123')] if license_only else [])
    r=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**with_scan(rev))
    assert r.status_code==200,r.text
    assert r.json()['status']=='rejected' and 'disagree' in str(r.json()['photo_review']['reasons'])
    assert stages==[10,25,55,75,90,100]

def test_scanned_barcode_cannot_replace_the_two_required_photos(freight):
    c,_=freight;sid,rev=prepared(c)
    response=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),data={'revision':str(rev),'license_barcode':SCAN,'vin_barcode':VIN})
    assert response.status_code==422
    assert c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['status']!='released'

def test_sparse_two_column_id_layout_extracts_without_guessing():
    from io import BytesIO
    from PIL import Image,ImageDraw,ImageFont
    from app.services.safe_load_images import license_evidence
    image=Image.new('RGB',(2000,850),'white');draw=ImageDraw.Draw(image)
    font=ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf',40)
    for x,y,value in [(50,60,'TEST DOCUMENT - NOT VALID'),(50,210,'DL NUMBER: TEST1234'),(1100,210,'EXP: 01/01/2030'),(50,380,'LAST NAME: DOE'),(1100,380,'ISSUING STATE: KS'),(50,560,'FIRST NAME: JOHN')]:draw.text((x,y),value,fill='black',font=font)
    raw=BytesIO();image.save(raw,'JPEG');result=license_evidence(raw.getvalue())
    assert not result['errors'],result
    assert result['fields']['DAQ']=='TEST1234' and result['fields']['DCS']=='DOE'
