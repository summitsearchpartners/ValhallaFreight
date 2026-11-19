from conftest import synthetic_font
from io import BytesIO
from pathlib import Path
import pytest,numpy as np,zxingcpp
from PIL import Image,ImageDraw,ImageFont,ImageFilter
from test_manufacturer import setup,headers
from test_truckload_safe_load import freight,VIN,BARCODE
from test_safe_load_photos import prepared,packet
from app.models import SafeLoadPhotoAttempt,SafeLoadReleaseReceipt
from app.services.safe_load import vin,decode_license
from app.services.safe_load_camera import document_readiness

def encoded(value,format):
    code=zxingcpp.create_barcode(value,format);image=Image.fromarray(np.asarray(zxingcpp.write_barcode_to_image(code,size_hint=1400)));b=BytesIO();image.save(b,'PNG');return b.getvalue()
def frame(data,rev,kind='license'):return {'data':{'revision':str(rev),'kind':kind},'files':{'frame':('camera.png',data,'image/png')}}
def card(blur=0,offset=0):
    image=Image.new('RGB',(1200,900),(35,45,55));d=ImageDraw.Draw(image);d.rounded_rectangle((200+offset,198,1000+offset,702),radius=20,fill=(210,215,220),outline='white',width=5);font=synthetic_font(24, family='mono', style='regular') if Path('/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf').exists() else ImageFont.load_default(size=24)
    for y in range(230,675,44):d.text((240+offset,y),'TEST DRIVER ID 1234 -- FICTIONAL',font=font,fill='black')
    if blur:image=image.filter(ImageFilter.GaussianBlur(blur))
    b=BytesIO();image.save(b,'JPEG');return b.getvalue()

def test_real_pdf417_frame_extracts_fields_and_is_qa_evidence(freight):
    c,factory=freight;sid,rev=prepared(c);code=BARCODE+'DBB01011990\n'
    result=c.post(f'/api/v1/safe-load/shipments/{sid}/barcode-frame',headers=headers(1),**frame(encoded(code,zxingcpp.BarcodeFormat.PDF417),rev))
    assert result.status_code==200,result.text
    scan=result.json();assert scan['first_name']=='JOHN' and scan['date_of_birth']=='1990-01-01' and scan['barcode']==code
    assert 'no-store' in result.headers['cache-control']
    with factory() as db:assert db.query(SafeLoadPhotoAttempt).count()==0 and db.get(SafeLoadReleaseReceipt,sid) is None
    p=packet(rev);p['data']['license_barcode']=scan['barcode']
    qa=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**p)
    assert qa.status_code==200 and qa.json()['status']=='released',qa.text

@pytest.mark.parametrize('value',[VIN,']C0'+VIN,'*'+VIN+'*','VIN: '+VIN])
def test_vin_preview_handles_real_scanner_prefixes(freight,value):
    c,_=freight;sid,rev=prepared(c)
    r=c.post(f'/api/v1/safe-load/shipments/{sid}/vin-barcode/preview',headers=headers(1),json={'revision':rev,'barcode':value})
    assert r.status_code==200 and r.json()['vin']==VIN,r.text

def test_real_vin_frame_scope_no_code_and_stale_assignment(freight):
    c,_=freight;sid,rev=prepared(c);url=f'/api/v1/safe-load/shipments/{sid}/barcode-frame';raw=encoded(VIN,zxingcpp.BarcodeFormat.Code128)
    assert c.post(url,headers=headers(1),**frame(raw,rev,'vin')).json()['vin']==VIN
    assert c.post(url,headers=headers(3),**frame(raw,rev,'vin')).status_code==404
    assert c.post(url,headers=headers(1),**frame(raw,rev+1,'vin')).status_code==409
    assert c.post(url,headers=headers(1),**frame(card(),rev,'vin')).status_code==422
    assert c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['status']!='released'

def test_quality_gates_real_sharpness_rectangle_and_does_not_release(freight):
    assert document_readiness(card())['ready']
    assert not document_readiness(card(blur=12))['ready']
    assert not document_readiness(card(offset=-230))['ready']
    c,factory=freight;sid,rev=prepared(c);url=f'/api/v1/safe-load/shipments/{sid}/capture-readiness'
    r=c.post(url,headers=headers(1),**frame(card(),rev));assert r.status_code==200 and r.json()['ready'],r.text
    assert c.post(url,headers=headers(3),**frame(card(),rev)).status_code==404
    assert c.post(url,headers=headers(1),**frame(card(),rev+1)).status_code==409
    with factory() as db:assert db.query(SafeLoadPhotoAttempt).count()==0
    assert not c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['confirmation_number']

def test_decoder_handles_real_delimiters_and_rejects_bad_values():
    assert decode_license('\ufeff'+BARCODE.replace('\n','\r\n')+'\x00')['DAQ']=='TEST1234'
    assert decode_license(BARCODE.replace('\n','\\n'))['DCS']=='DOE'
    with pytest.raises(ValueError):vin('https://example.test/'+VIN)
