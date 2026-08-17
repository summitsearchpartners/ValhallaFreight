from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Carrier
from app.schemas.entities import CarrierOut
router = APIRouter(prefix="/carriers", tags=["Carriers"])
@router.get("", response_model=list[CarrierOut])
def list_carriers(db: Session = Depends(get_db)): return db.query(Carrier).order_by(Carrier.name).all()
