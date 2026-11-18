import pytest
from fastapi import HTTPException
from sqlalchemy import update
from test_manufacturer import setup,headers
from test_truckload_safe_load import freight,book,submit
from test_safe_load_photos import packet,license_photo
from app.models import SafeLoadCustodySnapshot,SafeLoadPhotoAttempt,User
from app.services.auth import hash_password

def arrival(c,wrong=False):
    _,sid=book(c);_,rev=submit(c,sid)
    assert c.put(f'/api/v1/safe-load/shipments/{sid}/broker-contact',headers=headers(8),json={'phone':'9135550100'}).status_code==200
    result=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet(rev,vin='1HGCM82633A004353' if wrong else '1HGCM82633A004352'))
    assert result.status_code==200,result.text
    return sid,rev,result.json()
def decision(rev,rejected):return {'revision':rev,'rejection_id':rejected['rejection_id'],'reason':'Called the verified carrier dispatcher and independently confirmed this driver and arriving truck VIN. OCR could not read the label correctly.','driver_confirmed':True,'vehicle_confirmed':True,'evidence_reviewed':True}

def test_first_dispatcher_assignment_has_capture_flow_and_auto_transit(freight):
    c,_=freight;sid,rev,result=arrival(c)
    assert result['status']=='released' and result['shipment_status']=='in_transit'
    chain=c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(1)).json()
    assert chain['integrity']['valid'],chain
    actions=[s['payload']['action'] for s in chain['snapshots']]
    assert actions.count('hold_created')==1
    assert all(a in actions for a in ['assignment_submitted','scan_matched','freight_released','in_transit','photo_review_completed'])
    assert any(s['payload']['arrival_photos'] for s in chain['snapshots'])
    assert 'path' not in str(chain['snapshots'])

def test_broker_authorizes_rejection_and_preserves_failed_evidence(freight):
    c,factory=freight;sid,rev,rejected=arrival(c,True)
    assert rejected['status']=='rejected'
    notices=c.get('/api/v1/notifications',headers=headers(8)).json()
    assert any(n.get('notification_type')=='safe_load' and n['shipment_id']==sid for n in notices)
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/broker-release',headers=headers(1),json=decision(rev,rejected)).status_code==403
    p=decision(rev,rejected);p['rejection_id']+=100
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/broker-release',headers=headers(8),json=p).status_code==409
    p=decision(rev,rejected);p['vehicle_confirmed']=False
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/broker-release',headers=headers(8),json=p).status_code==422
    with factory() as db:
        db.add(User(id=9,email='unrelated@test.local',full_name='Unrelated broker',role='broker_admin',customer_id=2,password_hash=hash_password('BrowserTest123!')));db.commit()
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/broker-release',headers=headers(9),json=decision(rev,rejected)).status_code==404
    response=c.post(f'/api/v1/safe-load/shipments/{sid}/broker-release',headers=headers(8),json=decision(rev,rejected))
    assert response.status_code==200,response.text
    assert response.json()['release_method']=='broker_authorized'
    assert response.json()['shipment_status']=='in_transit'
    observed=c.get('/api/v1/safe-load',headers=headers(1)).json()[0]
    assert observed['status']=='released' and observed['release_actor']=='broker@test.local'
    with factory() as db:assert db.query(SafeLoadPhotoAttempt).filter_by(shipment_id=sid).first().status=='rejected'
    chain=c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(8)).json()
    assert chain['integrity']['valid']
    broker=[s for s in chain['snapshots'] if s['payload']['action']=='broker_authorized_release'][0]
    assert broker['payload']['actor']['user_id']==8
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(9)).status_code==404

def test_rejected_case_keeps_hold_even_when_later_photos_match(freight):
    c,_=freight;sid,rev,rejected=arrival(c,True)
    result=c.post(f'/api/v1/safe-load/shipments/{sid}/photo-review',headers=headers(1),**packet(rev))
    assert result.status_code==200 and result.json()['status']=='rejected',result.text
    assert 'requires broker' in str(result.json()['photo_review']['reasons'])
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/broker-release',headers=headers(8),json=decision(rev,rejected)).status_code==409
    fresh=result.json()
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/broker-release',headers=headers(8),json=decision(rev,fresh)).status_code==200

def test_broker_requires_both_photos_and_snapshots_are_append_only(freight):
    c,factory=freight;_,sid=book(c);_,rev=submit(c,sid)
    rejection=c.post(f'/api/v1/safe-load/shipments/{sid}/reject-arrival',headers=headers(1),json={'revision':rev}).json()
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/broker-release',headers=headers(8),json=decision(rev,rejection)).status_code==409
    with factory() as db:
        s=db.query(SafeLoadCustodySnapshot).first();s.phase='tampered'
        with pytest.raises(HTTPException):db.flush()
        db.rollback()
        with pytest.raises(HTTPException):db.execute(update(SafeLoadCustodySnapshot).values(phase='tampered'))
        db.rollback()
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(1)).json()['integrity']['valid']

def test_dispatcher_photo_is_retained_across_assignment_versions(freight):
    c,_=freight;_,sid=book(c);token,rev=submit(c,sid)
    chain=c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(1)).json()
    old=next(s['id'] for s in chain['snapshots'] if s['payload']['dispatcher_photo'])
    submit(c,sid,token=token,name='Jane Doe')
    image=c.get(f'/api/v1/safe-load/shipments/{sid}/custody/{old}/dispatcher-photo',headers=headers(1))
    assert image.status_code==200,image.text
    assert c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(1)).json()['integrity']['valid']

def test_native_capture_reports_authenticated_operator_and_device_time(freight):
    c,_=freight;_,sid=book(c);_,rev=submit(c,sid)
    p={'revision':rev,'kind':'license','captured_at':'2026-11-14T03:00:00Z'}
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/capture-event',headers=headers(1),json=p).status_code==200
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/capture-event',headers=headers(3),json=p).status_code==404
    p['revision']+=1
    assert c.post(f'/api/v1/safe-load/shipments/{sid}/capture-event',headers=headers(1),json=p).status_code==409
    chain=c.get(f'/api/v1/safe-load/shipments/{sid}/custody',headers=headers(1)).json()
    captured=[s for s in chain['snapshots'] if s['payload']['action']=='onsite_photo_captured'][-1]
    assert captured['payload']['actor']['user_id']==1
    assert captured['payload']['capture_metadata_declared_by_client']['kind']=='license'
