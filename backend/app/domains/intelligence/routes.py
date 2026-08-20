from fastapi import APIRouter,Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Shipment,Customer,Carrier,CarrierBill,Claim,Quote
router=APIRouter(prefix='/intelligence',tags=['Valhalla Intelligence'])
@router.get('/brief')
def brief(db:Session=Depends(get_db)):
    shipments=db.query(Shipment).all(); exceptions=db.query(CarrierBill).filter(CarrierBill.status=='exception').count(); claims=db.query(Claim).filter(Claim.status!='resolved').count()
    revenue=sum(float(s.customer_charge or 0) for s in shipments); cost=sum(float(s.final_carrier_cost if s.final_carrier_cost is not None else s.carrier_cost or 0) for s in shipments); gp=revenue-cost
    late=[s for s in shipments if s.delivered_at and s.requested_delivery_at and s.delivered_at>s.requested_delivery_at]
    by_customer={}
    for s in shipments: by_customer[s.customer_id]=by_customer.get(s.customer_id,0)+float(s.customer_charge or 0)
    top=None
    if by_customer:
      cid=max(by_customer,key=by_customer.get);c=db.get(Customer,cid);top={'customer':c.name if c else str(cid),'revenue':by_customer[cid]}
    insights=[]
    if exceptions: insights.append({'severity':'warning','title':f'{exceptions} freight-audit exceptions need review','detail':'Carrier invoice variance is above the configured review threshold.','path':'/finance'})
    if late: insights.append({'severity':'warning','title':f'{len(late)} shipments missed customer-required delivery','detail':'Review lanes, terminals and carriers contributing to service failures.','path':'/visibility'})
    if claims: insights.append({'severity':'danger','title':f'{claims} open claims require attention','detail':'Open cargo claims remain unresolved.','path':'/claims'})
    if top: insights.append({'severity':'info','title':f"{top['customer']} is the highest-revenue account",'detail':f"Recorded shipment revenue: ${top['revenue']:,.0f}.",'path':'/customers'})
    return {'shipments':len(shipments),'revenue':revenue,'gross_profit':gp,'margin_pct':(gp/revenue*100 if revenue else 0),'late_deliveries':len(late),'audit_exceptions':exceptions,'open_claims':claims,'insights':insights}
