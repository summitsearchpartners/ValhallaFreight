from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Customer
from app.schemas.entities import CustomerCreate, CustomerOut
router = APIRouter(prefix="/customers", tags=["Customers"])
@router.get("", response_model=list[CustomerOut])
def list_customers(db: Session = Depends(get_db)): return db.query(Customer).order_by(Customer.name).all()
@router.post("", response_model=CustomerOut)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    item = Customer(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item
