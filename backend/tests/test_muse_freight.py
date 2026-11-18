from datetime import timedelta
from decimal import Decimal
from io import BytesIO
from hashlib import sha256
from pypdf import PdfReader

from app.models import (Customer, Carrier, MuseAccount, MuseCreditApplication, MuseEnrollment,
                        MuseQuoteRate, MuseBooking, OperationalNotification, EmailOutbox, Quote)
from app.services.muse_credit import FIELDS, TEMPLATE, TEMPLATE_SHA256
from app.services import muse_enrollment as access
from test_manufacturer import headers, setup

API='/api/v1'
ADDRESS={'address1':'123 Main Street','city':'Olathe','state':'KS','postal_code':'66061','verified_postal_code':'66061'}
UNITS=[{'quantity':2,'weight_lbs':420,'length_in':48,'width_in':40,'height_in':48,'freight_class':'85'},
       {'quantity':1,'weight_lbs':200,'length_in':48,'width_in':40,'height_in':48,'freight_class':'125'}]


def partner(client):
    r=client.post(API+'/admin/users',headers=headers(4),json={
        'email':'muse@example.test','full_name':'Muse Reviewer','role':'muse_admin','customer_id':2,
        'active':True,'password':'MuseTest12345!'})
    assert r.status_code==201,r.text
    designation=client.put(API+'/admin/muse-partner',headers=headers(4),json={'company_id':2})
    assert designation.status_code==200,designation.text
    return headers(r.json()['id'])


def enable(client,company=1,value=True):
    r=client.put(API+f'/muse/enrollment/{company}/opt-in',headers=headers(4),json={'enabled':value})
    assert r.status_code==200,r.text
    return r.json()


def rate(client,factory,company=1):
    with factory() as db:
        carrier=db.query(Carrier).filter_by(scac='MTEST').first()
        if not carrier:
            carrier=Carrier(name='Shared Test Carrier',scac='MTEST');db.add(carrier);db.commit()
    r=client.post(API+'/quotes/rate',headers=headers(1 if company==1 else 3),json={
        'customer_id':company,'origin':ADDRESS,'destination':{**ADDRESS,'postal_code':'45414','verified_postal_code':'45414'},
        'handling_units':UNITS})
    assert r.status_code==200,r.text
    return r.json()


def publish(client,ref,carrier_id,reviewer):
    r=client.put(API+f'/quotes/{ref}/muse-rate',headers=headers(4),json={
        'carrier_name':'Shared Test Carrier','carrier_id':carrier_id,'customer_price':'487.65',
        'carrier_cost':'400.00','transit_days':3})
    assert r.status_code==200,r.text
    return r.json()['rate']


def application(client,company=1):
    values={f[0]:'Test Applicant' if f[-1] else '' for f in FIELDS}
    values.update(company_name='Alpha Manufacturing LLC',ap_email='ap@example.test',date='2026-11-12',
                  checking_account='000123456',signature='Test Applicant',print_name='Test Applicant')
    r=client.post(API+f'/muse/enrollment/{company}/application',headers=headers(1 if company==1 else 3),json={
        'values':values,'business_type':'corporation','consent':True})
    assert r.status_code==201,r.text
    return r.json()['application_id']


def approve(client,app_id,reviewer):
    r=client.post(API+f'/muse/applications/{app_id}/decision',headers=reviewer,json={'decision':'approved','note':'Approved by Muse'})
    assert r.status_code==200,r.text


def select(client,ref,offer,user=1):
    return client.post(API+f'/quotes/{ref}/muse-rate/select',headers=headers(user),json={'revision':offer['revision']})


def test_opt_in_is_default_off_super_only_and_inherited(setup):
    client,factory=setup;reviewer=partner(client)
    result=rate(client,factory)
    assert result['muse_preview'] is None
    for h in [headers(1),headers(2),headers(3),headers(5),reviewer]:
        assert client.put(API+'/muse/enrollment/1/opt-in',headers=h,json={'enabled':True}).status_code==403
    enable(client)
    with factory() as db:
        db.add(Customer(id=10,code='CHILD',name='Alpha child',manufacturer_id=1));db.commit()
    child=client.get(API+'/muse/enrollment/10',headers=headers(2))
    assert child.status_code==200 and child.json()['manufacturer_id']==1 and child.json()['enabled']
    assert not client.get(API+'/muse/enrollment/2',headers=headers(3)).json()['enabled']
    assert client.get(API+'/muse/enrollment/1',headers=headers(3)).status_code==404
    assert client.get(API+'/muse/manufacturers',headers=headers(2)).status_code==403
    assert [m['manufacturer_id'] for m in client.get(API+'/muse/manufacturers',headers=reviewer).json()]==[1]
    for path in ['/admin/users','/quotes','/shipments','/integrations','/portal/me']:
        assert client.get(API+path,headers=reviewer).status_code==403
    for key in ['broker','broker_admin']:
        r=client.post(API+'/admin/users',headers=headers(4),json={'email':key+'@example.test','full_name':key,'role':key,'customer_id':1,'password':'BrokerTest123!'})
        assert r.status_code==201
        assert client.get(API+'/muse/manufacturers',headers=headers(r.json()['id'])).status_code==403


def test_credit_application_is_private_immutable_and_muse_reviewed(setup):
    client,factory=setup;reviewer=partner(client);enable(client)
    app_id=application(client)
    info=client.get(API+'/muse/enrollment/1',headers=headers(2)).json()
    assert info['application_status']=='pending' and not info['can_book']
    assert client.post(API+f'/muse/applications/{app_id}/decision',headers=headers(1),json={'decision':'approved'}).status_code==403
    assert client.put(API+'/customers/1/muse-account',headers=headers(4),json={'account_verified':True}).status_code==409
    assert client.get(API+f'/muse/applications/{app_id}/pdf',headers=headers(3)).status_code==404
    r=client.get(API+f'/muse/applications/{app_id}/pdf',headers=reviewer)
    assert r.status_code==200,r.text
    assert r.headers['cache-control']=='no-store'
    pdf=PdfReader(BytesIO(r.content))
    assert len(pdf.pages)==1 and float(pdf.pages[0].mediabox.width)==612
    text=pdf.pages[0].extract_text()
    assert 'Credit Application' in text and '000123456' in text and 'Test Applicant' in text
    assert sha256(TEMPLATE.read_bytes()).hexdigest()==TEMPLATE_SHA256
    with factory() as db:
        app=db.get(MuseCreditApplication,app_id)
        assert '000123456' not in app.encrypted_payload
        assert app.template_sha256==TEMPLATE_SHA256
        assert db.query(OperationalNotification).filter_by(audience='muse').count()==1
        mail=db.query(EmailOutbox).filter_by(recipient_type='muse').first()
        assert mail.status=='captured' and '000123456' not in mail.body
    approve(client,app_id,reviewer)
    assert client.get(API+'/muse/enrollment/1',headers=headers(2)).json()['can_book']
    assert client.post(API+f'/muse/applications/{app_id}/decision',headers=reviewer,json={'decision':'approved'}).status_code==409


def test_muse_select_and_full_booking_require_approval_and_preserve_direct_rate(setup):
    client,factory=setup;reviewer=partner(client);enable(client)
    result=rate(client,factory);ref=result['quote_number'];carrier_id=result['options'][0]['carrier_id']
    offer=publish(client,ref,carrier_id,reviewer)
    selected=select(client,ref,offer)
    assert selected.status_code==200 and not selected.json()['selected']
    assert client.get(API+f'/quotes/{ref}',headers=headers(1)).json()['selected_option'] is None
    payload={'quote_number':ref,'carrier_id':carrier_id,'muse_revision':offer['revision'],'origin':ADDRESS,
             'destination':{**ADDRESS,'postal_code':'45414','verified_postal_code':'45414'}}
    assert client.post(API+'/shipments',headers=headers(1),json=payload).status_code==403
    app_id=application(client);approve(client,app_id,reviewer)
    assert select(client,ref,offer,2).json()['selected']
    detail=client.get(API+f'/quotes/{ref}',headers=headers(2)).json()
    assert len([o for o in detail['options'] if o['carrier_id']==carrier_id])==2
    assert detail['selected_option']['provider']=='muse_freight'
    booked=client.post(API+'/shipments',headers=headers(2),json=payload)
    assert booked.status_code==200,booked.text
    assert booked.json()['bol_number'] and booked.json()['status']=='pickup_requested'
    assert booked.json()['customer_charge']=='487.65'
    assert len(booked.json()['handling_units'])==2
    assert client.post(API+'/shipments',headers=headers(2),json=payload).status_code==409
    shipments=client.get(API+'/muse/bookings',headers=reviewer).json()
    assert len(shipments)==1 and shipments[0]['status']=='requested'
    bid=shipments[0]['id']
    assert client.get(API+f'/muse/bookings/{bid}/detail',headers=reviewer).json()['carrier_submissions'][0]['status']=='pending_muse_confirmation'
    assert client.post(API+f'/muse/bookings/{bid}/confirm',headers=headers(1),json={'provider_reference':'P1','pro_number':'PRO1'}).status_code==403
    confirmed=client.post(API+f'/muse/bookings/{bid}/confirm',headers=reviewer,json={'provider_reference':'P1','pro_number':'PRO1'})
    assert confirmed.status_code==200,confirmed.text
    assert client.get(API+f"/shipments/{booked.json()['id']}",headers=headers(2)).json()['pro_number']=='PRO1'


def test_revocation_decline_resubmit_and_stale_offers(setup):
    client,factory=setup;reviewer=partner(client);enable(client)
    first=application(client)
    assert client.post(API+f'/muse/applications/{first}/decision',headers=reviewer,json={'decision':'declined'}).status_code==422
    assert client.post(API+f'/muse/applications/{first}/decision',headers=reviewer,json={'decision':'declined','note':'Please correct the address'}).status_code==200
    second=application(client);assert second!=first
    approve(client,second,reviewer)
    result=rate(client,factory);ref=result['quote_number'];cid=result['options'][0]['carrier_id']
    offer=publish(client,ref,cid,reviewer)
    latest=publish(client,ref,cid,reviewer)
    assert select(client,ref,offer).status_code==409
    assert select(client,ref,latest).json()['selected']
    enable(client,value=False)
    assert client.get(API+f'/quotes/{ref}',headers=headers(2)).json()['muse_preview'] is None
    assert client.get(API+f'/quotes/{ref}',headers=headers(2)).json()['selected_option'] is None
    assert select(client,ref,latest).status_code==403
    assert client.post(API+'/shipments',headers=headers(2),json={'quote_number':ref,'carrier_id':cid,
        'muse_revision':latest['revision'],'origin':ADDRESS,'destination':{**ADDRESS,'postal_code':'45414','verified_postal_code':'45414'}}).status_code==403
    # Normal company carrier rates continue to select and book after Muse is disabled.
    direct=client.post(API+f'/quotes/{ref}/select',headers=headers(2),json={'carrier_id':cid})
    assert direct.status_code==200 and direct.json()['selected_option']['provider'] is None
    assert client.get(API+f'/muse/applications/{second}/pdf',headers=reviewer).status_code==403
