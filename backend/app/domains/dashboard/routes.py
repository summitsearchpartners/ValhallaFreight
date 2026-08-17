from datetime import date, timedelta
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.domains.dashboard import service
from app.domains.dashboard.schemas import DashboardSummary, PerformanceResponse, RecentShipment, IntelligenceSummary

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
