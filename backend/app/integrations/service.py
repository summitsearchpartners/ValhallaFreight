from __future__ import annotations
from datetime import datetime
from app.integrations.base import get_carrier
from app.models import IntegrationConnection, IntegrationCredential, AuditEvent
from app.integrations.secrets import encrypt_secret_payload, decrypt_secret_payload, hint

DAYTON_PROVIDER='Dayton Freight'
SENSITIVE_KEYS={'password','api_key','client_secret','bearer_token','token','secret'}


def get_dayton_connection(db):
    row=db.query(IntegrationConnection).filter(IntegrationConnection.provider==DAYTON_PROVIDER).first()
    if not row:
        row=IntegrationConnection(provider=DAYTON_PROVIDER,category='Carrier Connectivity',status='available',environment='sandbox',capabilities=['rating','pickup','tracking','bol','documents','service'])
        db.add(row); db.commit(); db.refresh(row)
    return row


def public_connection(row):
    settings=row.settings or {}
    return {
      'id':row.id,'provider':row.provider,'category':row.category,'status':row.status,'environment':row.environment,
      'capabilities':row.capabilities or [],'last_sync_at':row.last_sync_at,'last_error':row.last_error,
      'settings':{k:v for k,v in settings.items() if k not in SENSITIVE_KEYS},
    }


def get_credential_row(db, integration_id: int):
    return db.query(IntegrationCredential).filter(IntegrationCredential.integration_id==integration_id).first()


def credential_payload(db, integration_id: int) -> dict:
    row=get_credential_row(db,integration_id)
    return decrypt_secret_payload(row.encrypted_payload) if row else {}


def save_credentials(db, integration: IntegrationConnection, auth_type: str, payload: dict, *, merge: bool=True):
    row=get_credential_row(db,integration.id)
    current=decrypt_secret_payload(row.encrypted_payload) if (row and merge) else {}
    clean={k:v for k,v in payload.items() if v not in (None,'')}
    current.update(clean)
    # Explicit null sentinels can clear a credential field.
    for k,v in payload.items():
        if v is None and k in current:
            current.pop(k,None)
    encrypted=encrypt_secret_payload(current)
    if not row:
        row=IntegrationCredential(integration_id=integration.id,auth_type=auth_type or 'none',encrypted_payload=encrypted)
        db.add(row)
    else:
        row.auth_type=auth_type or row.auth_type
        row.encrypted_payload=encrypted
        row.updated_at=datetime.utcnow()
    if integration.status in {'available','imported','error'}:
        integration.status='configured'
    db.commit();db.refresh(row)
    return row,current


def delete_credentials(db, integration: IntegrationConnection):
    row=get_credential_row(db,integration.id)
    if row: db.delete(row)
    integration.status='configured' if integration.settings else 'available'
    integration.last_error=None
    db.commit()


def public_credentials(db, integration: IntegrationConnection):
    row=get_credential_row(db,integration.id)
    payload=decrypt_secret_payload(row.encrypted_payload) if row else {}
    auth=(row.auth_type if row else (integration.settings or {}).get('detected_auth_type') or 'none')
    return {
      'configured': bool(row and payload),
      'auth_type': auth,
      'username_hint': hint(payload.get('username')),
      'has_password': bool(payload.get('password')),
      'has_api_key': bool(payload.get('api_key')),
      'has_bearer_token': bool(payload.get('bearer_token')),
      'client_id_hint': hint(payload.get('client_id')),
      'has_client_secret': bool(payload.get('client_secret')),
      'custom_header_names': sorted((payload.get('headers') or {}).keys()) if isinstance(payload.get('headers'),dict) else [],
      'configured_at': row.configured_at if row else None,
      'updated_at': row.updated_at if row else None,
    }


def audit(db, action: str, details: dict, entity_id: str='DAFG'):
    # Never place credential values in audit details.
    safe={k:v for k,v in (details or {}).items() if k.lower() not in SENSITIVE_KEYS and 'password' not in k.lower() and 'secret' not in k.lower() and 'token' not in k.lower()}
    db.add(AuditEvent(entity_type='integration',entity_id=entity_id,action=action,actor='Valhalla Freight',details=safe))
    db.commit()


def _detect_auth(spec: dict):
    components=(spec.get('components') or {}) if isinstance(spec,dict) else {}
    schemes=components.get('securitySchemes') or {}
    detected=[]
    for name, cfg in schemes.items():
        if not isinstance(cfg,dict): continue
        typ=str(cfg.get('type') or '').lower()
        scheme=str(cfg.get('scheme') or '').lower()
        if typ=='http' and scheme=='basic': auth='basic_auth'
        elif typ=='http' and scheme=='bearer': auth='bearer_token'
        elif typ=='apiKey'.lower(): auth='api_key'
        elif typ=='oauth2': auth='oauth2'
        else: auth=typ or 'custom'
        detected.append({'name':name,'auth_type':auth,'location':cfg.get('in'),'parameter':cfg.get('name')})
    # Swagger 2.0
    for name,cfg in (spec.get('securityDefinitions') or {}).items():
        if not isinstance(cfg,dict): continue
        typ=str(cfg.get('type') or '').lower()
        if typ=='basic': auth='basic_auth'
        elif typ=='apikey': auth='api_key'
        elif typ=='oauth2': auth='oauth2'
        else: auth=typ or 'custom'
        detected.append({'name':name,'auth_type':auth,'location':cfg.get('in'),'parameter':cfg.get('name')})
    return detected


def analyze_openapi(spec: dict):
    info=spec.get('info') or {}; paths=spec.get('paths') or {}
    tags={}
    operations=[]
    servers=spec.get('servers') or []
    base_urls=[x.get('url') for x in servers if isinstance(x,dict) and x.get('url')]
    auth=_detect_auth(spec)
    for path, methods in paths.items():
        for method, op in (methods or {}).items():
            if method.lower() not in {'get','post','put','delete','patch'} or not isinstance(op,dict): continue
            tag=(op.get('tags') or ['Other'])[0]
            tags[tag]=tags.get(tag,0)+1
            operations.append({'method':method.upper(),'path':path,'tag':tag,'summary':op.get('summary')})
    return {'title':info.get('title') or 'OpenAPI Integration','version':info.get('version'),'openapi':spec.get('openapi') or spec.get('swagger'),
            'endpoint_count':len(operations),'tags':tags,'operations':operations[:250], 'auth_schemes':auth,
            'detected_auth_type':auth[0]['auth_type'] if auth else 'none','base_urls':base_urls}
