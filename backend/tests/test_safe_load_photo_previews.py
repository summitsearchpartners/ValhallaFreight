"""Synthetic photos: native data-URI previews reuse the protected evidence reader."""
import base64,io
from PIL import Image
from test_manufacturer import setup,headers
from test_truckload_safe_load import freight
from test_safe_load_photos import prepared,packet
from test_safe_load_back_photo import with_back

def test_released_front_back_vin_previews_roundtrip_match_existing_broker_images(freight):
    c,_=freight;sid,rev=prepared(c)
    row=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**with_back(rev)).json()
    assert row['status']=='released';aid=row['photo_review']['id']
    for kind in ['license','license-back','vin']:
        path=f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/{kind}'
        binary=c.get(path,headers=headers(8));assert binary.status_code==200
        for user in [1,8,4]:
            response=c.get(path+'/photo-data',headers=headers(user));assert response.status_code==200,response.text
            assert 'no-store' in response.headers['cache-control'] and response.headers['x-content-type-options']=='nosniff'
            data=response.json();assert {k:data[k] for k in ['shipment_id','attempt_id','revision','kind']}=={'shipment_id':sid,'attempt_id':aid,'revision':rev,'kind':kind}
            image=base64.b64decode(data['data_uri'].split(',',1)[1],validate=True)
            assert image==binary.content;Image.open(io.BytesIO(image)).verify()
        assert c.get(path+'/photo-data',headers=headers(3)).status_code==404
        assert c.get(path+'/photo-data').status_code in [401,403]
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/bogus/photo-data',headers=headers(1)).status_code==404
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid+10000}/vin/photo-data',headers=headers(1)).status_code==404
    chain=c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(1)).json();assert chain['integrity']['valid']
    assert c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['status']=='released'

def test_older_two_photo_attempt_loads_and_missing_back_is_explicit(freight):
    c,_=freight;sid,rev=prepared(c)
    row=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet(rev)).json()
    assert row['status']=='released';aid=row['photo_review']['id']
    attempts=c.get(f'/api/v1/safe-load/shipments/{sid}/attempts',headers=headers(1)).json()
    assert not attempts[0]['has_back_photo']
    for kind in ['license','vin']:assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/{kind}/photo-data',headers=headers(1)).status_code==200
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/license-back/photo-data',headers=headers(1)).status_code==404
