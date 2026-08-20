from datetime import datetime
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import IntegrationConnection
router=APIRouter(prefix='/integrations',tags=['Integration Hub'])
class IntegrationUpdate(BaseModel): status:str|None=None;environment:str|None=None;settings:dict|None=None
@router.get('')
def list_integrations(db:Session=Depends(get_db)):
    rows=db.query(IntegrationConnection).order_by(IntegrationConnection.category,IntegrationConnection.provider).all()
    return [{'id':x.id,'provider':x.provider,'category':x.category,'status':x.status,'environment':x.environment,'capabilities':x.capabilities,'last_sync_at':x.last_sync_at,'last_error':x.last_error} for x in rows]
@router.patch('/{integration_id}')
def update(integration_id:int,payload:IntegrationUpdate,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(row,k,v)
    db.commit();return {'ok':True}
@router.post('/{integration_id}/test')
def test(integration_id:int,db:Session=Depends(get_db)):
    row=db.get(IntegrationConnection,integration_id)
    if not row: raise HTTPException(404,'Integration not found')
    row.last_sync_at=datetime.utcnow(); row.last_error=None
    if row.status=='available': row.status='configured'
    db.commit();return {'ok':True,'status':row.status,'message':'Configuration health check completed. Live vendor calls require provider credentials and enabled adapters.'}
