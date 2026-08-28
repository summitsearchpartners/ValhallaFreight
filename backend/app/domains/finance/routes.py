from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import CarrierBill, Shipment, Carrier, Customer, CustomerProfile, MarginProtectionNotification
from app.domains.customers.models import CustomerActivity

router=APIRouter(prefix='/finance',tags=['Finance'])

class BillCreate(BaseModel):
    shipment_id:int
    bill_number:str
    invoice_cost:Decimal
    charge_breakdown:list[dict]=[]

class CarrierInvoiceIngest(BaseModel):
    bill_number:str
    invoice_cost:Decimal
    shipment_number:str|None=None
    bol_number:str|None=None
    pro_number:str|None=None
    carrier_scac:str|None=None
    source:str='carrier_api'
    charge_breakdown:list[dict]=Field(default_factory=list)


def _policy(db:Session, customer_id:int):
    p=db.query(CustomerProfile).filter(CustomerProfile.customer_id==customer_id).first()
    return {
        'threshold':Decimal(str(p.margin_protection_threshold if p and p.margin_protection_threshold is not None else 75)),
        'internal':bool(p.margin_protection_internal_notify if p else True),
        'customer':bool(p.margin_protection_customer_notify if p else True),
    }


def _create_notifications(db:Session,bill:CarrierBill,shipment:Shipment,customer:Customer,carrier:Carrier|None,policy:dict):
    variance=Decimal(str(bill.variance or 0)); threshold=Decimal(str(bill.threshold_at_audit or 0))
    carrier_name=carrier.name if carrier else 'Carrier'
    title='Carrier invoice variance needs review'
    body=(f'{carrier_name} invoice {bill.bill_number} for shipment {shipment.shipment_number} is '
          f'${abs(variance):,.2f} {"above" if variance>0 else "below"} the quoted carrier cost. '
          f'{customer.name} margin-protection threshold is ${threshold:,.2f}. Review the invoice and carrier charges before approval.')
    audiences=[]
    if policy['internal']: audiences.append('internal')
    if policy['customer']: audiences.append('customer')
    for audience in audiences:
        db.add(MarginProtectionNotification(customer_id=customer.id,shipment_id=shipment.id,carrier_bill_id=bill.id,audience=audience,title=title,body=body,severity='warning'))
    db.add(CustomerActivity(customer_id=customer.id,activity_type='margin_exception',subject=title,body=body,created_by='Valhalla Intelligence'))


def _audit_bill(db:Session,shipment:Shipment,bill_number:str,invoice_cost:Decimal,charge_breakdown:list[dict],source:str,matched_by:str):
    if db.query(CarrierBill).filter(CarrierBill.bill_number==bill_number).first():
        raise HTTPException(409,'Carrier bill number already exists')
    customer=db.get(Customer,shipment.customer_id)
    carrier=db.get(Carrier,shipment.carrier_id) if shipment.carrier_id else None
    policy=_policy(db,shipment.customer_id)
    quoted=Decimal(str(shipment.carrier_cost or 0)); variance=invoice_cost-quoted
    threshold=policy['threshold']
    is_exception=abs(variance)>threshold
    reason=None
    if is_exception:
        reason=f'Absolute carrier-cost variance ${abs(variance):.2f} exceeds {customer.name if customer else "customer"} threshold ${threshold:.2f}.'
    bill=CarrierBill(
        bill_number=bill_number,shipment_id=shipment.id,carrier_id=shipment.carrier_id,
        quoted_cost=quoted,invoice_cost=invoice_cost,variance=variance,
        status='exception' if is_exception else 'matched',charge_breakdown=charge_breakdown,
        threshold_at_audit=threshold,invoice_source=source,matched_by=matched_by,exception_reason=reason,
    )
    db.add(bill);db.flush()
    if is_exception and customer:
        _create_notifications(db,bill,shipment,customer,carrier,policy)
    db.commit();db.refresh(bill)
    return bill

@router.get('/audit')
def audit_queue(db:Session=Depends(get_db)):
    rows=db.query(CarrierBill).order_by(CarrierBill.created_at.desc()).all();out=[]
    for b in rows:
        s=db.get(Shipment,b.shipment_id); c=db.get(Carrier,b.carrier_id) if b.carrier_id else None; customer=db.get(Customer,s.customer_id) if s else None
        out.append({
            'id':b.id,'bill_number':b.bill_number,'shipment_id':b.shipment_id,'shipment_number':s.shipment_number if s else None,
            'customer_id':customer.id if customer else None,'customer':customer.name if customer else None,'carrier':c.name if c else None,
            'quoted_cost':float(b.quoted_cost),'invoice_cost':float(b.invoice_cost),'variance':float(b.variance),'threshold':float(b.threshold_at_audit or 75),
            'status':b.status,'charge_breakdown':b.charge_breakdown,'source':b.invoice_source,'matched_by':b.matched_by,
            'exception_reason':b.exception_reason,'created_at':b.created_at
        })
    return out

@router.post('/audit')
def create_bill(payload:BillCreate,db:Session=Depends(get_db)):
    s=db.get(Shipment,payload.shipment_id)
    if not s: raise HTTPException(404,'Shipment not found')
    b=_audit_bill(db,s,payload.bill_number,payload.invoice_cost,payload.charge_breakdown,'manual','shipment_id')
    return {'id':b.id,'variance':float(b.variance),'threshold':float(b.threshold_at_audit),'status':b.status}

@router.post('/ingest/carrier-invoice')
def ingest_carrier_invoice(payload:CarrierInvoiceIngest,db:Session=Depends(get_db)):
    shipment=None; matched_by=None
    if payload.shipment_number:
        shipment=db.query(Shipment).filter(Shipment.shipment_number==payload.shipment_number).first(); matched_by='shipment_number' if shipment else None
    if not shipment and payload.bol_number:
        shipment=db.query(Shipment).filter(Shipment.bol_number==payload.bol_number).first(); matched_by='bol_number' if shipment else None
    if not shipment and payload.pro_number:
        shipment=db.query(Shipment).filter(Shipment.pro_number==payload.pro_number).first(); matched_by='pro_number' if shipment else None
    if not shipment:
        raise HTTPException(404,'Unable to match carrier invoice to a Valhalla shipment. Provide shipment number, BOL number, or PRO number.')
    if payload.carrier_scac:
        carrier=db.query(Carrier).filter(Carrier.scac==payload.carrier_scac).first()
        if carrier and shipment.carrier_id and carrier.id!=shipment.carrier_id:
            raise HTTPException(409,f'Invoice carrier {payload.carrier_scac} does not match shipment carrier.')
    b=_audit_bill(db,shipment,payload.bill_number,payload.invoice_cost,payload.charge_breakdown,payload.source,matched_by or 'unknown')
    return {'id':b.id,'shipment_id':shipment.id,'shipment_number':shipment.shipment_number,'variance':float(b.variance),'threshold':float(b.threshold_at_audit),'status':b.status,'matched_by':b.matched_by}

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

@router.get('/notifications')
def notifications(audience:str=Query('internal'),customer_id:int|None=None,db:Session=Depends(get_db)):
    q=db.query(MarginProtectionNotification).filter(MarginProtectionNotification.audience==audience)
    if customer_id is not None:q=q.filter(MarginProtectionNotification.customer_id==customer_id)
    rows=q.order_by(MarginProtectionNotification.created_at.desc()).limit(50).all()
    return [{'id':n.id,'customer_id':n.customer_id,'shipment_id':n.shipment_id,'carrier_bill_id':n.carrier_bill_id,'audience':n.audience,'severity':n.severity,'title':n.title,'body':n.body,'status':n.status,'created_at':n.created_at} for n in rows]

@router.post('/notifications/{notification_id}/read')
def mark_notification_read(notification_id:int,db:Session=Depends(get_db)):
    n=db.get(MarginProtectionNotification,notification_id)
    if not n:raise HTTPException(404,'Notification not found')
    n.status='read';n.read_at=datetime.utcnow();db.commit();return {'ok':True}
