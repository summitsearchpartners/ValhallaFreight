from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Claim,Shipment
router=APIRouter(prefix='/claims',tags=['Claims'])
class ClaimCreate(BaseModel): shipment_id:int;claim_type:str='damage';amount:Decimal=Decimal('0');description:str|None=None
@router.get('')
def list_claims(db:Session=Depends(get_db)):
    rows=db.query(Claim).order_by(Claim.filed_at.desc()).all();out=[]
    for c in rows:
      s=db.get(Shipment,c.shipment_id)
      out.append({'id':c.id,'claim_number':c.claim_number,'shipment_id':c.shipment_id,'shipment_number':s.shipment_number if s else None,'claim_type':c.claim_type,'amount':float(c.amount),'status':c.status,'description':c.description,'filed_at':c.filed_at,'resolved_at':c.resolved_at})
    return out
@router.post('')
def create_claim(payload:ClaimCreate,db:Session=Depends(get_db)):
    if not db.get(Shipment,payload.shipment_id): raise HTTPException(404,'Shipment not found')
    n=db.query(Claim).count()+1;row=Claim(claim_number=f'VFC-{datetime.utcnow():%y%m%d}-{n:04d}',**payload.model_dump());db.add(row);db.commit();db.refresh(row);return {'id':row.id,'claim_number':row.claim_number}
@router.post('/{claim_id}/resolve')
def resolve(claim_id:int,db:Session=Depends(get_db)):
    row=db.get(Claim,claim_id)
    if not row: raise HTTPException(404,'Claim not found')
    row.status='resolved';row.resolved_at=datetime.utcnow();db.commit();return {'ok':True}
