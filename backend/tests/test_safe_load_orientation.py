"""Synthetic ID text/markers only; no real identity images."""
from conftest import synthetic_font

import io
from pathlib import Path
import pytest
from PIL import Image,ImageDraw,ImageFont
from app.services.safe_load_orientation import correction,normalize_license
from app.services.safe_load_images import normalize
from test_manufacturer import setup,headers
from test_truckload_safe_load import freight,book,approve,VIN
from test_safe_load_back_photo import with_back
from app.models import SafeLoadCase,SafeLoadPhotoAttempt
from app.integrations.secrets import _fernet

def card(angle=0,exif=False):
    image=Image.new('RGB',(1100,720),'white');draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,65,65),fill=(240,10,10))
    font=synthetic_font(34, family='sans', style='regular')
    lines=['KANSAS DRIVER LICENSE','DL NUMBER: TEST1234','FIRST NAME: JOHN','LAST NAME: DOE','ISSUING STATE: KS','EXP: 01/01/2030','RESTRICTIONS NONE','ENDORSEMENTS NONE']
    for i,line in enumerate(lines):draw.text((90,80+i*72),line,font=font,fill='black')
    image=image.rotate(angle,expand=True);buf=io.BytesIO()
    metadata=Image.Exif()
    if exif:metadata[274]=6
    image.save(buf,'JPEG',quality=96,exif=metadata);return buf.getvalue()

def is_upright(raw):
    image=Image.open(io.BytesIO(raw));assert image.size==(1100,720)
    pixel=image.getpixel((30,30));assert pixel[0]>200 and pixel[1]<40 and pixel[2]<40

@pytest.mark.parametrize('angle',[0,90,180,270])
def test_confident_text_direction_makes_real_pixels_upright(angle):
    assert correction(card(angle))==angle
    result=normalize_license(card(angle));is_upright(result)
    assert correction(result)==0

def test_exif_is_applied_once_not_double_rotated():
    result=normalize_license(card(90,exif=True));is_upright(result)
    assert Image.open(io.BytesIO(result)).getexif().get(274,1)==1

def test_no_readable_text_is_not_forced_into_an_orientation():
    b=io.BytesIO();Image.new('RGB',(100,60),'gray').save(b,'JPEG')
    assert correction(b.getvalue())==0

def test_legacy_dispatcher_and_onsite_preview_rotate_without_rewriting_evidence(freight,monkeypatch):
    import base64
    from app.services import safe_load_orientation
    c,factory=freight;_,sid=book(c)
    invite=c.post(f'/api/v1/safe-load/shipments/{sid}/invite',headers=headers(8)).json()['token']
    # Simulate a historical client/backend which normalized EXIF but kept rotated pixels.
    with monkeypatch.context() as patch:
        patch.setattr(safe_load_orientation,'normalize_license',lambda raw,allow_blank=False:normalize(raw,allow_blank=allow_blank))
        r=c.post('/api/v1/safe-load/carrier',headers={'X-Safe-Load-Token':invite},data={'driver_name':'John Doe','license_number':'TEST1234','issuing_state':'KS','license_expires':'2030-01-01','truck_vin':VIN},files={'photo':('old-license.jpg',card(90),'image/jpeg')})
        assert r.status_code==200,r.text;rev=r.json()['revision'];approve(c,sid,rev)
        assert c.put(f'/api/v1/safe-load/shipments/{sid}/broker-contact',headers=headers(8),json={'phone':'+1 913 555 0100'}).status_code==200
        packet=with_back(rev);packet['files']['license_photo']=('old-onsite.jpg',card(180),'image/jpeg')
        r=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet)
        assert r.status_code==200,r.text
        row=r.json();assert row['status']=='released',row;aid=row['photo_review']['id']
    with factory() as db:
        paths=[Path(db.get(SafeLoadCase,sid).photo_path),Path(db.get(SafeLoadPhotoAttempt,aid).license_path)]
        original=[path.read_bytes() for path in paths]
    is_upright(c.get(f'/api/v1/safe-load/shipments/{sid}/photo',headers=headers(8)).content)
    data=c.get(f'/api/v1/safe-load/shipments/{sid}/photo-data',headers=headers(1)).json();is_upright(base64.b64decode(data['data_uri'].split(',')[1]))
    path=f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/license'
    # Original byte access remains available; display paths are derivatives only.
    assert c.get(path,headers=headers(8)).content==_fernet().decrypt(original[1])
    is_upright(c.get(path+'?upright=true',headers=headers(8)).content)
    data=c.get(path+'/photo-data',headers=headers(1)).json();is_upright(base64.b64decode(data['data_uri'].split(',')[1]))
    assert [path.read_bytes() for path in paths]==original
    assert c.get(path+'?upright=true',headers=headers(3)).status_code==404
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(8)).json()['integrity']['valid']
