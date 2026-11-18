from datetime import datetime
import pytest
from test_manufacturer import setup,headers
from test_truckload_safe_load import freight,book,submit
from test_broker_customers import linked,assign
from test_safe_load_photos import packet,license_photo,photo
from test_safe_load_custody import decision
from app.models import User,SafeLoadCase,SafeLoadPhotoExtraction,SafeLoadCallProfile
from app.services.safe_load_assessment import assess,name_matches
from app.services.safe_load_images import license_evidence,rotated

CONTACT={'contact_name':'Safe Load Dispatch Desk','phone':'+1 913 555 0144'}
def save(c,uid=8,contact=None):
    return c.put('/api/v1/workspace/profile-page',headers=headers(uid),json={'full_name':'Broker Desk','safe_load_contact':contact or CONTACT})
def automatic(c,rev,**kw):
    p=packet(rev,**kw);p['data'].pop('physical_id_matches_photo')
    return p

def test_profile_contact_shared_with_assigned_manufacturer_and_isolated(linked):
    c,factory=linked;assign(c);_,sid=book(c);_,rev=submit(c,sid)
    assert save(c).status_code==200
    r=c.get('/api/v1/workspace/safe-load-contact',headers=headers(8));assert r.status_code==200 and r.json()['phone']==CONTACT['phone']
    row=c.get('/api/v1/safe-load',headers=headers(1)).json()[0]
    assert row['broker_contact']['phone']==CONTACT['phone'] and row['broker_contact']['source']=='broker_profile'
    assert c.get('/api/v1/workspace/safe-load-contact',headers=headers(9)).json()['phone']==''
    assert c.get('/api/v1/workspace/safe-load-contact',headers=headers(1)).status_code==403
    assert save(c,1).status_code==403
    assert save(c,9).status_code==403
    assert save(c,8,{'contact_name':'Night Dispatch','phone':'9135550199'}).status_code==200
    assert c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['broker_contact']['phone']=='9135550199'
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(1)).json()['integrity']['valid']
    bad=save(c,8,{'contact_name':'Broken','phone':'123'})
    assert bad.status_code==422
    assert c.get('/api/v1/workspace/safe-load-contact',headers=headers(8)).json()['phone']=='9135550199'
    with factory() as db:assert db.get(SafeLoadCallProfile,'company:3').updated_by==8

def test_no_warehouse_checkbox_automatic_release_and_broker_evidence(linked):
    c,factory=linked;assign(c);save(c);_,sid=book(c);_,rev=submit(c,sid)
    r=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**automatic(c,rev))
    assert r.status_code==200,r.text
    row=r.json();assert row['status']=='released' and row['shipment_status']=='in_transit'
    aid=row['photo_review']['id']
    assert row['photo_review']['extraction']['name_matched']
    detail=f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/extraction'
    broker=c.get(detail,headers=headers(8));assert broker.status_code==200,broker.text
    assert broker.json()['license_number']=='TEST1234' and 'no-store' in broker.headers['cache-control']
    assert c.get(detail,headers=headers(1)).status_code==403
    assert c.get(detail,headers=headers(9)).status_code==404
    for kind in ['license','vin']:
        image=c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/{kind}',headers=headers(8))
        assert image.status_code==200 and image.content.startswith(b'\xff\xd8')
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts',headers=headers(9)).status_code==404
    with factory() as db:
        e=db.get(SafeLoadPhotoExtraction,aid)
        assert 'TEST1234' not in e.encrypted_data and 'TEST1234' not in str(e.summary)
    chain=c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(8)).json()
    assert chain['integrity']['valid']
    assert any(s['payload'].get('verification_mode')=='automated_photo_qa' for s in chain['snapshots'])

def test_changed_license_routes_to_broker_and_requires_acknowledgement(linked):
    c,_=linked;assign(c);save(c);_,sid=book(c);_,rev=submit(c,sid)
    r=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**automatic(c,rev,license=license_photo('REISSUED9')))
    assert r.status_code==200,r.text
    row=r.json();assert row['status']=='rejected' and row['photo_review']['extraction']['requires_license_review']
    assert row['broker_contact']['phone']==CONTACT['phone']
    assert any(n['shipment_id']==sid and 'Safe Load rejected' in n['title'] for n in c.get('/api/v1/notifications',headers=headers(8)).json())
    p=decision(rev,row)
    endpoint=f'/api/v1/safe-load/shipments/{sid}/broker-release'
    assert c.post(endpoint,headers=headers(8),json=p).status_code==422
    p['reissued_license_reviewed']=True
    release=c.post(endpoint,headers=headers(8),json=p);assert release.status_code==200,release.text
    assert release.json()['shipment_status']=='in_transit'
    assert c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['status']=='released'

def test_later_expiration_same_identity_accepts_renewal_without_visual_bool(linked):
    c,_=linked;assign(c);save(c);_,sid=book(c);_,rev=submit(c,sid)
    image=photo(['TEST DOCUMENT - NOT VALID','DL NUMBER: TEST1234','FIRST NAME: JOHN','LAST NAME: DOE JR.','ISSUING STATE: KS','EXP: 01/01/2034'])
    response=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**automatic(c,rev,license=image))
    assert response.status_code==200,response.text
    row=response.json();assert row['status']=='released',row
    assert row['photo_review']['extraction']['renewal_accepted']

def test_rotated_license_reader_and_name_formatting():
    result=license_evidence(rotated(license_photo(),90))
    assert not result['errors'] and result['fields']['DAQ']=='TEST1234'
    assert name_matches('John A. Doe, Jr.','JOHN','DOE JR')
    assert name_matches('John A. Doe Jr.','JOHN','DOE JR')
    assert name_matches('Doe, John A.','JOHN','DOE')
    assert not name_matches('John Doe','JANE','DOE')

def test_shared_profile_overrides_legacy_and_explicit_clear_holds(freight):
    c,factory=freight
    with factory() as db:db.get(User,8).role='broker_admin';db.commit()
    _,sid=book(c);_,rev=submit(c,sid)
    c.put(f'/api/v1/safe-load/shipments/{sid}/broker-contact',headers=headers(8),json={'phone':'9135550100'})
    assert save(c).status_code==200
    assert c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['broker_contact']['phone']==CONTACT['phone']
    assert save(c,8,{'contact_name':'','phone':''}).status_code==200
    assert c.get('/api/v1/safe-load',headers=headers(1)).json()[0]['broker_contact'] is None
    r=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**automatic(c,rev))
    assert r.status_code==200 and r.json()['status']=='rejected' and r.json()['photo_review']['id']

def test_unreadable_camera_image_keeps_both_photos_for_broker(freight,monkeypatch):
    from test_safe_load_photos import prepared,_black
    from app.services import safe_load_images
    c,_=freight;sid,rev=prepared(c)
    monkeypatch.setattr(safe_load_images,'license_evidence',lambda raw:{'fields':{},'source':'local_ocr','errors':['License fields unreadable']})
    r=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**automatic(c,rev,license=_black()))
    assert r.status_code==200 and r.json()['status']=='rejected'
    aid=r.json()['photo_review']['id']
    for kind in ['license','vin']:assert c.get(f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/{kind}',headers=headers(8)).status_code==200

def test_profile_permissions_platform_context_and_atomic_failure(linked):
    c,factory=linked
    from app.services.auth import hash_password
    with factory() as db:
        db.add(User(id=10,email='regular@broker.test',full_name='Regular Broker',role='broker',customer_id=3,password_hash=hash_password('BrowserTest123!')));db.commit()
    assert save(c).status_code==200
    assert c.get('/api/v1/workspace/safe-load-contact',headers=headers(10)).json()['phone']==CONTACT['phone']
    assert save(c,10).status_code==403
    with factory() as db:assert db.get(User,10).full_name=='Regular Broker'
    platform=save(c,4);assert platform.status_code==200,platform.text
    selected=c.put('/api/v1/workspace/profile-page',headers={**headers(4),'X-Company-Id':'4'},json={'full_name':'Test Super','safe_load_contact':{'contact_name':'Other Desk','phone':'9135550188'}})
    assert selected.status_code==200,selected.text
    assert c.get('/api/v1/workspace/safe-load-contact',headers={**headers(4),'X-Company-Id':'4'}).json()['phone']=='9135550188'
    assert c.get('/api/v1/workspace/safe-load-contact',headers=headers(4)).json()['phone']==CONTACT['phone']
    assert c.get('/api/v1/workspace/safe-load-contact',headers={**headers(8),'X-Company-Id':'4'}).status_code==403

def test_designated_muse_profile_contact_updates_only_real_partner_shipments(freight):
    from app.models import MuseBooking,MusePartnerCompany,SafeLoadCustodySnapshot
    from app.services.auth import hash_password
    c,factory=freight;_,sid=book(c);_,rev=submit(c,sid)
    with factory() as db:
        db.add(User(id=9,email='muse@partner.test',full_name='Muse Broker Admin',role='broker_admin',customer_id=2,password_hash=hash_password('BrowserTest123!')))
        db.add(MusePartnerCompany(id=1,company_id=2));db.add(MuseBooking(customer_id=1,shipment_id=sid,status='requested'));db.commit()
    configured=save(c,9);assert configured.status_code==200,configured.text
    maker=c.get('/api/v1/safe-load',headers=headers(1)).json()[0]
    assert maker['broker_contact']['company_id']==2 and maker['broker_contact']['phone']==CONTACT['phone']
    chain=c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(9)).json()
    assert any(s['payload']['action']=='broker_profile_contact_updated' for s in chain['snapshots'])
    rejected=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**automatic(c,rev,vin='1HGCM82633A004353'))
    assert rejected.status_code==200,rejected.text
    aid=rejected.json()['photo_review']['id']
    endpoint=f'/api/v1/safe-load/shipments/{sid}/attempts/{aid}/extraction'
    assert c.get(endpoint,headers=headers(9)).status_code==200
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(9)).json()['integrity']['valid']
