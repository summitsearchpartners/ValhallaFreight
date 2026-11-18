from datetime import datetime,timedelta
from app.models import OperationRun,IntegrationConnection,IntegrationCredential
from app.integrations.service import credential_payload
from app.core.config import settings

def connection_state(db,row):
    secret=credential_payload(db,row.id)
    credential=db.query(IntegrationCredential).filter_by(integration_id=row.id).first()
    auth=credential.auth_type if credential else 'none'
    configured=bool(secret)
    if auth=='basic_auth':configured=bool(secret.get('username') and secret.get('password'))
    elif auth=='api_key':configured=bool(secret.get('api_key'))
    elif auth=='bearer_token':configured=bool(secret.get('bearer_token'))
    elif auth in {'client_credentials','oauth2'}:configured=bool(secret.get('client_id') and secret.get('client_secret'))
    if row.provider=='Dayton Freight':configured=bool((secret.get('username') or (settings.dayton_api_username if row.customer_id is None else '')) and (secret.get('password') or (settings.dayton_api_password if row.customer_id is None else '')))
    meta=(row.settings or {}).get('live_check') or {}
    checked=meta.get('checked_at');successful=meta.get('successful_at')
    stale=True
    if successful:
        try:stale=datetime.fromisoformat(successful.replace('Z','+00:00')).replace(tzinfo=None)<datetime.utcnow()-timedelta(minutes=15)
        except ValueError:pass
    adapter_available=row.provider=='Dayton Freight'
    state='credentials_required' if not configured else 'check_failed' if meta.get('ok') is False else 'live_healthy' if adapter_available and checked and meta.get('ok') and not stale else 'check_stale' if successful else 'not_verified'
    return {'id':row.id,'provider':row.provider,'customer_id':row.customer_id,'adapter_available':adapter_available,'credentials_configured':configured,'connection_verified':bool(successful),'live_healthy':state=='live_healthy','state':state,'last_check_at':checked,'last_success_at':successful}

def record_run(db,*,kind,status,summary,company=None,integration=None,shipment=None,retryable=False):
    row=OperationRun(customer_id=company,integration_id=integration,shipment_id=shipment,kind=kind,status=status,summary=summary,retryable=retryable)
    db.add(row);db.commit();return row

def live_check(db,row,ok):
    now=datetime.utcnow().isoformat()+'Z';previous=(row.settings or {}).get('live_check') or {}
    row.settings={**(row.settings or {}),'live_check':{'checked_at':now,'ok':bool(ok),'successful_at':now if ok else previous.get('successful_at')}}
    db.commit()
    record_run(db,kind='connection_check',status='succeeded' if ok else 'failed',summary=f'{row.provider}: live connection check '+('passed' if ok else 'failed; review credentials and configuration'),company=row.customer_id,integration=row.id,retryable=not ok)
