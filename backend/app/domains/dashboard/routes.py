from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.db.session import get_db
from app.domains.dashboard import service
from app.domains.dashboard.schemas import DashboardSummary, PerformanceResponse, RecentShipment, IntelligenceSummary
from app.models import Shipment,Carrier,Customer,Claim

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    return service.summary(db)

@router.get("/performance", response_model=PerformanceResponse)
def performance(start_date: date | None = None, end_date: date | None = None, db: Session = Depends(get_db)):
    end = end_date or date.today()
    start = start_date or (end - timedelta(days=365))
    return service.performance(db,start,end)

@router.get("/recent-shipments", response_model=list[RecentShipment])
def recent_shipments(limit: int = Query(8,ge=1,le=50), db: Session = Depends(get_db)):
    return service.recent_shipments(db,limit)

@router.get("/intelligence", response_model=IntelligenceSummary)
def intelligence(db: Session = Depends(get_db)):
    return service.intelligence(db)


@router.get('/carrier-kpis')
def carrier_kpis(db:Session=Depends(get_db)):
    carriers=db.query(Carrier).order_by(Carrier.name).all(); out=[]
    for c in carriers:
        rows=db.query(Shipment).filter(Shipment.carrier_id==c.id).all()
        if not rows: continue
        revenue=sum(float(x.customer_charge or 0) for x in rows); cost=sum(float(x.final_carrier_cost if x.final_carrier_cost is not None else x.carrier_cost or 0) for x in rows)
        delivered=[x for x in rows if x.delivered_at]; due=[x for x in delivered if x.requested_delivery_at or x.estimated_delivery]
        ontime=sum(1 for x in due if (x.requested_delivery_at and x.delivered_at<=x.requested_delivery_at) or (not x.requested_delivery_at and x.estimated_delivery and x.delivered_at.date()<=x.estimated_delivery))
        pickup_due=[x for x in rows if x.actual_pickup_at and x.scheduled_pickup_at]; pickup_on=sum(1 for x in pickup_due if x.actual_pickup_at<=x.scheduled_pickup_at)
        claims=db.query(Claim).join(Shipment,Claim.shipment_id==Shipment.id).filter(Shipment.carrier_id==c.id).count()
        out.append({'carrier_id':c.id,'carrier':c.name,'scac':c.scac,'shipments':len(rows),'revenue':revenue,'carrier_cost':cost,'gross_profit':revenue-cost,'margin_pct':((revenue-cost)/revenue*100 if revenue else 0),'on_time_delivery_pct':(ontime/len(due)*100 if due else None),'on_time_pickup_pct':(pickup_on/len(pickup_due)*100 if pickup_due else None),'claims':claims})
    return out

@router.get('/customer-kpis')
def customer_kpis(db:Session=Depends(get_db)):
    customers=db.query(Customer).order_by(Customer.name).all();out=[]
    for c in customers:
        rows=db.query(Shipment).filter(Shipment.customer_id==c.id).all()
        if not rows: continue
        revenue=sum(float(x.customer_charge or 0) for x in rows);cost=sum(float(x.final_carrier_cost if x.final_carrier_cost is not None else x.carrier_cost or 0) for x in rows)
        delivered=[x for x in rows if x.delivered_at];due=[x for x in delivered if x.requested_delivery_at or x.estimated_delivery]
        ontime=sum(1 for x in due if (x.requested_delivery_at and x.delivered_at<=x.requested_delivery_at) or (not x.requested_delivery_at and x.estimated_delivery and x.delivered_at.date()<=x.estimated_delivery))
        out.append({'customer_id':c.id,'customer':c.name,'shipments':len(rows),'revenue':revenue,'carrier_cost':cost,'gross_profit':revenue-cost,'margin_pct':((revenue-cost)/revenue*100 if revenue else 0),'on_time_delivery_pct':(ontime/len(due)*100 if due else None)})
    return out


@router.get('/carrier-customer-kpis')
def carrier_customer_kpis(db:Session=Depends(get_db)):
    rows=db.query(Shipment).all();groups={}
    for x in rows:
        key=(x.carrier_id,x.customer_id);groups.setdefault(key,[]).append(x)
    out=[]
    for (carrier_id,customer_id),items in groups.items():
        carrier=db.get(Carrier,carrier_id) if carrier_id else None;customer=db.get(Customer,customer_id)
        revenue=sum(float(x.customer_charge or 0) for x in items);cost=sum(float(x.final_carrier_cost if x.final_carrier_cost is not None else x.carrier_cost or 0) for x in items)
        due=[x for x in items if x.delivered_at and (x.requested_delivery_at or x.estimated_delivery)]
        ontime=sum(1 for x in due if (x.requested_delivery_at and x.delivered_at<=x.requested_delivery_at) or (not x.requested_delivery_at and x.estimated_delivery and x.delivered_at.date()<=x.estimated_delivery))
        out.append({'carrier_id':carrier_id,'carrier':carrier.name if carrier else 'Unassigned','scac':carrier.scac if carrier else '—','customer_id':customer_id,'customer':customer.name if customer else 'Unknown','shipments':len(items),'revenue':revenue,'carrier_cost':cost,'gross_profit':revenue-cost,'margin_pct':((revenue-cost)/revenue*100 if revenue else 0),'on_time_delivery_pct':(ontime/len(due)*100 if due else None)})
    return sorted(out,key=lambda x:(x['carrier'],x['customer']))
