from test_manufacturer import setup,headers
from test_truckload_safe_load import freight
from test_safe_load_photos import prepared,photo
from test_safe_load_back_photo import with_back
from test_safe_load_custody import decision

def test_same_saved_front_back_vin_remain_accessible_after_rejection_and_broker_release(freight):
    c,_=freight;sid,rev=prepared(c);packet=with_back(rev)
    packet['files']['vin_photo']=('wrong.jpg',photo(['1HGCM82633A004353']),'image/jpeg')
    row=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet).json()
    assert row['status']=='rejected';aid=row['photo_review']['id']
    saved={}
    for kind in ['license','license-back','vin']:
        path=f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/{kind}'
        image=c.get(path,headers=headers(1));assert image.status_code==200 and image.headers['cache-control']=='no-store'
        saved[kind]=image.content
        assert c.get(path,headers=headers(3)).status_code==404
    release=c.post(f'/api/v1/safe-load/shipments/{sid}/broker-release',headers=headers(8),json=decision(rev,row))
    assert release.status_code==200 and release.json()['status']=='released'
    attempts=c.get(f'/api/v1/safe-load/shipments/{sid}/attempts',headers=headers(1)).json()
    assert attempts[0]['id']==aid and attempts[0]['revision']==rev and attempts[0]['has_back_photo']
    for kind,original in saved.items():assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/{kind}',headers=headers(1)).content==original
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(1)).json()['integrity']['valid']

def test_local_neural_vin_flows_through_exact_match_release_and_custody(freight):
    from test_safe_load_vin_reader import plate
    c,_=freight;sid,rev=prepared(c);packet=with_back(rev)
    packet['files']['vin_photo']=('onsite-vin.jpg',plate(True),'image/jpeg')
    response=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet)
    assert response.status_code==200,response.text
    row=response.json();assert row['status']=='released' and row['confirmation_number']
    assert row['photo_review']['extraction']['vin_reader']=='local_neural_ocr'
    assert row['photo_review']['extraction']['vin_matched']
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(1)).json()['integrity']['valid']
