from conftest import synthetic_font
from io import BytesIO
from pathlib import Path
import base64,pytest
from PIL import Image,ImageDraw,ImageFont
from test_manufacturer import headers,setup
from test_truckload_safe_load import freight,book,submit,approve
from app.models import SafeLoadPhotoAttempt,Shipment
from app.services.safe_load_images import license_data,vehicle,normalize,_tesseract_executable

def photo(lines):
    img=Image.new('RGB',(1800,700),'white');d=ImageDraw.Draw(img);font=synthetic_font(40, family='mono', style='regular') if Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf').exists() else ImageFont.load_default(size=40)
    for n,line in enumerate(lines):d.text((40,40+n*72),line,fill='black',font=font)
    b=BytesIO();img.save(b,'JPEG');return b.getvalue()

def license_photo(number='TEST1234',first='JOHN'):
    return photo(['TEST DOCUMENT - NOT A VALID LICENSE','DL NUMBER: '+number,'FIRST NAME: '+first,'LAST NAME: DOE','ISSUING STATE: KS','EXP: 01/01/2030'])

def packet(rev,license=None,vin='1HGCM82633A004352',physical='true'):
    return {'data':{'revision':str(rev),'physical_id_matches_photo':physical},'files':{'license_photo':('arrival-id.jpg',license or license_photo(),'image/jpeg'),'vin_photo':('arrival-vin.jpg',photo(['TRUCK VIN',vin]),'image/jpeg')}}

def prepared(c):
    _,sid=book(c);_,rev=submit(c,sid);approve(c,sid,rev)
    assert c.put(f'/api/v1/safe-load/shipments/{sid}/broker-contact',headers=headers(8),json={'phone':'+1 913 555 0100'}).status_code==200
    return sid,rev

def test_real_local_ocr_reads_synthetic_document():
    assert _tesseract_executable(), 'Install Tesseract OCR with English language data before running OCR integration tests'
    fields=license_data(normalize(license_photo()))
    assert fields['DAQ']=='TEST1234' and fields['DAC']=='JOHN' and fields['DAJ']=='KS'
    assert vehicle(normalize(photo(['VIN 1HGCM82633A004352'])))=='1HGCM82633A004352'
    with pytest.raises(ValueError):normalize(_black())

def _black():
    b=BytesIO();Image.new('RGB',(100,100),'black').save(b,'PNG');return b.getvalue()

def test_photo_confirm_release_encrypted_evidence_and_display(freight):
    c,factory=freight;sid,rev=prepared(c)
    image=c.get(f'/api/v1/safe-load/shipments/{sid}/photo-data',headers=headers(1));assert image.status_code==200,image.text
    raw=base64.b64decode(image.json()['data_uri'].split(',')[1]);assert Image.open(BytesIO(raw)).format=='JPEG'
    assert 'no-store' in image.headers['cache-control']
    response=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet(rev))
    assert response.status_code==200,response.text
    result=response.json();assert result['status']=='released' and result['photo_review']['status']=='confirmed'
    aid=result['photo_review']['id']
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/license',headers=headers(1)).status_code==200
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/license',headers=headers(3)).status_code==404
    with factory() as db:
        attempt=db.get(SafeLoadPhotoAttempt,aid)
        assert not Path(attempt.license_path).read_bytes().startswith(b'\xff\xd8')
        assert db.get(Shipment,sid).actual_pickup_at is not None

@pytest.mark.parametrize('number,first,vin',[('WRONG999','JOHN','1HGCM82633A004352'),('TEST1234','JANE','1HGCM82633A004352'),('TEST1234','JOHN','1HGCM82633A004353')])
def test_photo_mismatch_rejects_notifies_broker_and_returns_phone(freight,number,first,vin):
    c,_=freight;sid,rev=prepared(c)
    result=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet(rev,license_photo(number,first),vin))
    assert result.status_code==200,result.text
    assert result.json()['status']=='rejected' and result.json()['photo_review']['reasons']
    assert result.json()['broker_contact']['phone']=='+1 913 555 0100'
    assert any('Safe Load rejected' in n['title'] for n in c.get('/api/v1/notifications',headers=headers(8)).json())
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/release',headers=headers(1),json={'revision':rev}).status_code==409

def test_photo_preconditions_and_unreadable(freight):
    c,_=freight;_,sid=book(c);_,rev=submit(c,sid);approve(c,sid,rev)
    missing=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet(rev))
    assert missing.status_code==200 and missing.json()['status']=='rejected'
    assert 'configure' in str(missing.json()['photo_review']['reasons'])
    assert missing.json()['photo_review']['id']
    assert c.put(f'/api/v1/safe-load/shipments/{sid}/broker-contact',headers=headers(1),json={'phone':'9135550100'}).status_code==403
    c.put(f'/api/v1/safe-load/shipments/{sid}/broker-contact',headers=headers(8),json={'phone':'9135550100'})
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet(rev+1)).status_code==409
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet(rev,physical='false')).json()['status']=='rejected'
    response=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet(rev,photo(['UNREADABLE TEST DOCUMENT'])))
    assert response.status_code==200 and response.json()['status']=='rejected',response.text

def test_visual_person_mismatch_can_be_reported(freight):
    c,_=freight;sid,rev=prepared(c)
    response=c.post(f'/api/v1/safe-load/shipments/{sid}/reject-arrival',headers=headers(1),json={'revision':rev})
    assert response.status_code==200 and response.json()['status']=='rejected'
    assert any('Safe Load rejected' in n['title'] for n in c.get('/api/v1/notifications',headers=headers(8)).json())

def test_actual_barcode_photographs_decode_without_ocr():
    import zxingcpp,numpy as np
    from test_truckload_safe_load import BARCODE,VIN
    def encoded(value,format):
        symbol=zxingcpp.create_barcode(value,format)
        image=Image.fromarray(np.asarray(zxingcpp.write_barcode_to_image(symbol,size_hint=1000)))
        b=BytesIO();image.save(b,'PNG');return b.getvalue()
    assert license_data(encoded(BARCODE,zxingcpp.BarcodeFormat.PDF417))['DAQ']=='TEST1234'
    assert vehicle(encoded(VIN,zxingcpp.BarcodeFormat.Code128))==VIN
