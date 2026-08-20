from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import CarrierBill, Shipment, Carrier, Invoice
router=APIRouter(prefix='/finance',tags=['Finance'])
class BillCreate(BaseModel):
    shipment_id:int;bill_number:str;invoice_cost:Decimal;charge_breakdown:list[dict]=[]
@router.get('/audit')
def audit_queue(db:Session=Depends(get_db)):
    rows=db.query(CarrierBill).order_by(CarrierBill.created_at.desc()).all();out=[]
    for b in rows:
        s=db.get(Shipment,b.shipment_id); c=db.get(Carrier,b.carrier_id) if b.carrier_id else None
        out.append({'id':b.id,'bill_number':b.bill_number,'shipment_id':b.shipment_id,'shipment_number':s.shipment_number if s else None,'carrier':c.name if c else None,'quoted_cost':float(b.quoted_cost),'invoice_cost':float(b.invoice_cost),'variance':float(b.variance),'status':b.status,'charge_breakdown':b.charge_breakdown,'created_at':b.created_at})
    return out
@router.post('/audit')
def create_bill(payload:BillCreate,db:Session=Depends(get_db)):
    s=db.get(Shipment,payload.shipment_id)
    if not s: raise HTTPException(404,'Shipment not found')
    quoted=Decimal(str(s.carrier_cost or 0));variance=payload.invoice_cost-quoted
    b=CarrierBill(bill_number=payload.bill_number,shipment_id=s.id,carrier_id=s.carrier_id,quoted_cost=quoted,invoice_cost=payload.invoice_cost,variance=variance,status='exception' if abs(variance)>Decimal('25') else 'matched',charge_breakdown=payload.charge_breakdown)
    db.add(b);db.commit();db.refresh(b);return {'id':b.id,'variance':float(b.variance),'status':b.status}
@router.post('/audit/{bill_id}/{action}')
def resolve_bill(bill_id:int,action:str,db:Session=Depends(get_db)):
    b=db.get(CarrierBill,bill_id)
    if not b: raise HTTPException(404,'Bill not found')
    if action not in {'approve','dispute'}: raise HTTPException(400,'Action must be approve or dispute')
    b.status='approved' if action=='approve' else 'disputed'
    if action=='approve':
        s=db.get(Shipment,b.shipment_id)
        if s: s.final_carrier_cost=b.invoice_cost
    db.commit();return {'ok':True,'status':b.status}
