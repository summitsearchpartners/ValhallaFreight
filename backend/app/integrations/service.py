from __future__ import annotations
from datetime import datetime
from app.integrations.base import get_carrier
from app.models import IntegrationConnection, AuditEvent

DAYTON_PROVIDER='Dayton Freight'

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
      'settings':{k:v for k,v in settings.items() if k not in {'password','api_key','client_secret'}},
    }

def audit(db, action: str, details: dict):
    db.add(AuditEvent(entity_type='integration',entity_id='DAFG',action=action,actor='Valhalla Freight',details=details))
    db.commit()

def analyze_openapi(spec: dict):
    info=spec.get('info') or {}; paths=spec.get('paths') or {}
    tags={}
    operations=[]
    for path, methods in paths.items():
        for method, op in (methods or {}).items():
            if method.lower() not in {'get','post','put','delete','patch'} or not isinstance(op,dict): continue
            tag=(op.get('tags') or ['Other'])[0]
            tags[tag]=tags.get(tag,0)+1
            operations.append({'method':method.upper(),'path':path,'tag':tag,'summary':op.get('summary')})
    return {'title':info.get('title') or 'OpenAPI Integration','version':info.get('version'),'openapi':spec.get('openapi') or spec.get('swagger'),
            'endpoint_count':len(operations),'tags':tags,'operations':operations[:250]}
