from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Quote, Shipment
from app.schemas.entities import DashboardSummary
router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
@router.get("/summary", response_model=DashboardSummary)
def summary(db: Session = Depends(get_db)):
    start = datetime.utcnow().replace(day=1,hour=0,minute=0,second=0,microsecond=0)
    open_quotes=db.query(func.count(Quote.id)).filter(Quote.status=="open").scalar() or 0
    active=db.query(func.count(Shipment.id)).filter(~Shipment.status.in_(["delivered","cancelled"])).scalar() or 0
    delivered=db.query(func.count(Shipment.id)).filter(Shipment.status=="delivered", Shipment.created_at>=start).scalar() or 0
    revenue=db.query(func.coalesce(func.sum(Shipment.customer_charge),0)).filter(Shipment.created_at>=start).scalar() or 0
    cost=db.query(func.coalesce(func.sum(Shipment.carrier_cost),0)).filter(Shipment.created_at>=start).scalar() or 0
    gp=Decimal(revenue)-Decimal(cost); margin=(gp/Decimal(revenue)*100) if Decimal(revenue) else Decimal(0)
    return DashboardSummary(open_quotes=open_quotes,active_shipments=active,delivered_month=delivered,revenue_month=revenue,carrier_cost_month=cost,gross_profit_month=gp,avg_margin_pct=margin)
