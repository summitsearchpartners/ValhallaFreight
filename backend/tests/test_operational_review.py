from datetime import datetime,timedelta
from io import BytesIO
import pandas as pd
from test_manufacturer import setup,headers
from app.models import Carrier,Shipment,IntegrationConnection,OperationRun
from app.services.operations import connection_state,live_check,record_run
from app.integrations.service import save_credentials


def test_carrier_percentages_require_actual_denominators(setup):
    c,factory=setup
    with factory() as db:
        db.add(Carrier(id=1,name='Example',scac='TEST',on_time_pct=96.2,claims_pct=0.4));db.commit()
    row=c.get('/api/v1/carrier-360',headers=headers(4)).json()[0]
    assert row['shipments']==0 and row['on_time_delivery_pct'] is None
    assert row['on_time_pickup_pct'] is None and row['claims_pct'] is None
    assert row['benchmark_on_time_pct']==96.2
    with factory() as db:
        for i,late in [(1,False),(2,True)]:
            db.add(Shipment(shipment_number=f'MEASURE-{i}',customer_id=1,carrier_id=1,origin={},destination={},handling_units=[],requested_delivery_at=datetime(2026,10,1,12),delivered_at=datetime(2026,10,1,13 if late else 11)))
        db.commit()
    row=c.get('/api/v1/carrier-360',headers=headers(4)).json()[0]
    assert row['delivery_qualifying']==2 and row['delivery_on_time']==1
    assert row['on_time_delivery_pct']==50 and row['claims_pct']==0


def test_status_requires_recent_real_check_and_invalidates_changed_credentials(setup):
    c,factory=setup
    with factory() as db:
        row=IntegrationConnection(provider='Dayton Freight',category='Custom',customer_id=1,status='connected');db.add(row);db.commit()
        assert connection_state(db,row)['state']=='credentials_required'
        save_credentials(db,row,'basic_auth',{'username':'qa-user','password':'private-value'})
        assert connection_state(db,row)['state']=='not_verified'
        live_check(db,row,True)
        assert connection_state(db,row)['state']=='live_healthy'
        row.settings={**row.settings,'live_check':{'ok':True,'checked_at':'2020-01-01T00:00:00Z','successful_at':'2020-01-01T00:00:00Z'}};db.commit()
        assert connection_state(db,row)['state']=='check_stale'
        live_check(db,row,False)
        assert connection_state(db,row)['state']=='check_failed'
        save_credentials(db,row,'basic_auth',{'username':'qa-user','password':'changed-private-value'})
        assert connection_state(db,row)['state']=='not_verified'
    summary=c.get('/api/v1/operations/summary',headers=headers(1))
    assert summary.status_code==200,summary.text
    assert summary.json()['configured']==1 and summary.json()['healthy']==0
    assert 'private-value' not in summary.text
    assert c.get('/api/v1/operations/summary',headers=headers(3)).json()['connections']==[]
    assert c.get('/api/v1/operations/summary',headers=headers(5)).status_code==403


def test_configuration_review_is_not_live_health_and_runs_are_company_scoped(setup):
    c,factory=setup
    with factory() as db:
        row=IntegrationConnection(provider='Generic Framework',category='Custom',customer_id=1,status='available');db.add(row);db.commit();rid=row.id
    result=c.post(f'/api/v1/integrations/connection/{rid}/test',headers=headers(1))
    assert result.status_code==200 and result.json()['ok'] is False
    summary=c.get('/api/v1/operations/summary',headers=headers(1)).json()
    assert summary['healthy']==0 and summary['runs'][0]['status']=='review'
    assert c.get('/api/v1/operations/summary',headers=headers(3)).json()['runs']==[]
    with factory() as db:assert db.get(IntegrationConnection,rid).last_sync_at is None


def test_failed_connection_can_retry_successfully_without_booking_side_effects(setup,monkeypatch):
    c,factory=setup
    from app.integrations.carriers.dayton import DaytonAdapter
    async def failure(self):return {'ok':False,'message':'Not configured'}
    monkeypatch.setattr(DaytonAdapter,'test_connection',failure)
    c.post('/api/v1/integrations/dayton/test',headers=headers(1))
    run=c.get('/api/v1/operations/summary',headers=headers(1)).json()['runs'][0]
    assert run['status']=='failed' and run['retryable']
    assert c.post(f"/api/v1/operations/runs/{run['id']}/retry",headers=headers(2)).status_code==403
    assert c.post(f"/api/v1/operations/runs/{run['id']}/retry",headers=headers(3)).status_code==404
    async def success(self):return {'ok':True,'message':'Authenticated'}
    monkeypatch.setattr(DaytonAdapter,'test_connection',success)
    r=c.post(f"/api/v1/operations/runs/{run['id']}/retry",headers=headers(1));assert r.status_code==200,r.text
    assert c.get('/api/v1/operations/summary',headers=headers(1)).json()['needs_review']==0
    assert c.post(f"/api/v1/operations/runs/{run['id']}/retry",headers=headers(1)).status_code==409
    with factory() as db:assert db.query(Shipment).count()==0


def test_attention_points_to_overdue_shipments_and_hides_other_companies(setup):
    c,factory=setup
    with factory() as db:
        db.add(Shipment(shipment_number='LATE-ALPHA',customer_id=1,origin={},destination={},handling_units=[],requested_delivery_at=datetime.utcnow()-timedelta(days=1)))
        db.add(Shipment(shipment_number='PRIVATE-BETA',customer_id=2,origin={},destination={},handling_units=[]));db.commit()
    summary=c.get('/api/v1/operations/summary',headers=headers(2))
    assert summary.status_code==200,summary.text
    assert 'LATE-ALPHA' in summary.text and 'PRIVATE-BETA' not in summary.text
    assert '/shipments/' in summary.json()['attention'][0]['path']


def test_prospect_preview_mapping_validation_and_no_false_annualization(setup):
    c,_=setup
    body=b'Total Freight,Shipment Pounds,From\n"$1,000.50",500,00123\n250,1000,66061\n'
    mapping='{"spend":"Total Freight","weight":"Shipment Pounds","origin_zip":"From"}'
    preview=c.post('/api/v1/prospects/preview',headers=headers(4),files={'file':('history.csv',body,'text/csv')})
    assert preview.status_code==200,preview.text
    assert not preview.json()['valid'] and preview.json()['sample'][0]['From']=='00123'
    validated=c.post('/api/v1/prospects/preview',headers=headers(4),data={'mapping':mapping},files={'file':('history.csv',body,'text/csv')})
    assert validated.json()['valid']
    result=c.post('/api/v1/prospects/analyze',headers=headers(4),data={'mapping':mapping},files={'file':('history.csv',body,'text/csv')})
    assert result.status_code==200,result.text
    assert result.json()['spend_total']==1250.5 and result.json()['avg_weight']==750
    assert 'not annualized' in result.json()['message']
    assert c.get('/api/v1/prospects/template',headers=headers(4)).headers['content-type'].startswith('text/csv')
    assert c.post('/api/v1/prospects/preview',headers=headers(1),files={'file':('h.csv',body)}).status_code==403


def test_bad_imports_are_rejected_before_analysis(setup):
    c,_=setup
    for name,body in [('h.csv',b'spend,weight\nabc,0\n'),('h.exe',b'anything')]:
        r=c.post('/api/v1/prospects/analyze',headers=headers(4),files={'file':(name,body)})
        assert r.status_code==422,r.text
    output=BytesIO();pd.DataFrame({'spend':[500],'weight':[1000]}).to_excel(output,index=False)
    r=c.post('/api/v1/prospects/preview',headers=headers(4),files={'file':('h.xlsx',output.getvalue())})
    assert r.status_code==200 and r.json()['valid'],r.text


def test_hazmat_booking_requires_conditional_emergency_details(setup):
    from app.api.routes.shipments import _create_from_quote
    from app.models import Quote
    from fastapi import HTTPException
    import pytest
    _,factory=setup
    with factory() as db:
        q=db.get(Quote,1);q.options=[{'carrier_id':1,'transit_days':2}];q.handling_units=[{'quantity':1}];q.accessorials=['hazmat'];db.commit()
        with pytest.raises(HTTPException) as error:_create_from_quote(db,q,1)
        assert error.value.status_code==422 and 'emergency' in error.value.detail
        assert db.query(Shipment).count()==0


def test_tracking_retry_deduplicates_events_and_normalizes_offset_times(setup,monkeypatch):
    from types import SimpleNamespace
    from app.models import TrackingEvent
    from app.domains.integrations import routes
    c,factory=setup
    with factory() as db:
        db.add(Carrier(id=1,name='Dayton Freight',scac='DAFG'));db.flush()
        s=Shipment(shipment_number='RETRY-SAFE',customer_id=1,carrier_id=1,origin={},destination={},handling_units=[],pro_number='123456')
        db.add(s);db.commit();sid=s.id
    async def track(*args,**kwargs):
        return [SimpleNamespace(code=None,status='IN_TRANSIT',description='Departed terminal',location='KC',event_time='2026-10-20T10:00:00-05:00')],{}
    monkeypatch.setattr(routes,'dayton_track',track)
    path=f'/api/v1/integrations/dayton/shipments/{sid}/sync-tracking'
    first=c.post(path,headers=headers(1));assert first.status_code==200,first.text
    second=c.post(path,headers=headers(1));assert second.status_code==200,second.text
    assert first.json()['created_events']==1 and second.json()['created_events']==0
    with factory() as db:
        events=db.query(TrackingEvent).all();assert len(events)==1
        assert events[0].event_time==datetime(2026,10,20,15)
    summary=c.get('/api/v1/operations/summary',headers=headers(1)).json()
    assert len(summary['runs'])==2 and all(r['status']=='succeeded' for r in summary['runs'])

    # A platform-admin retry must reuse the manufacturer's original connection.
    from app.integrations.base.exceptions import CarrierIntegrationError
    from app.models import IntegrationConnection
    with factory() as db:
        connection=db.query(IntegrationConnection).filter_by(customer_id=1,provider='Dayton Freight').one()
        save_credentials(db,connection,'basic_auth',{'username':'manufacturer-user','password':'do-not-log-this'})
    async def failing_track(*args,**kwargs):raise CarrierIntegrationError('Tracking failed')
    monkeypatch.setattr(routes,'dayton_track',failing_track)
    assert c.post(path,headers=headers(1)).status_code==400
    failed=c.get('/api/v1/operations/summary',headers=headers(1)).json()['runs'][0]
    async def retry_track(*args,**kwargs):
        assert kwargs['client'].username=='manufacturer-user'
        return [],{}
    monkeypatch.setattr(routes,'dayton_track',retry_track)
    retried=c.post(f"/api/v1/operations/runs/{failed['id']}/retry",headers=headers(4))
    assert retried.status_code==200,retried.text
    assert c.get('/api/v1/operations/summary',headers=headers(1)).json()['needs_review']==0
