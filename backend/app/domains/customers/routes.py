from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.domains.customers import service
from app.domains.customers.schemas import CustomerCreate, CustomerUpdate, CustomerSummary, Customer360, LocationCreate, LocationOut, ContactCreate, ContactOut, ActivityCreate, ActivityOut

router = APIRouter(prefix="/customers", tags=["Customer 360"])

@router.get("", response_model=list[CustomerSummary])
def list_customers(db: Session = Depends(get_db)):
    return service.list_customers(db)

@router.post("", response_model=CustomerSummary, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)):
    return service.create_customer(db, payload)

@router.get("/{customer_id}/360", response_model=Customer360)
def get_customer_360(customer_id: int, db: Session = Depends(get_db)):
    return service.get_customer_360(db, customer_id)

@router.patch("/{customer_id}", response_model=CustomerSummary)
def update_customer(customer_id: int, payload: CustomerUpdate, db: Session = Depends(get_db)):
    return service.update_customer(db, customer_id, payload)

@router.post("/{customer_id}/locations", response_model=LocationOut, status_code=201)
def add_location(customer_id: int, payload: LocationCreate, db: Session = Depends(get_db)):
    return service.add_location(db, customer_id, payload)

@router.post("/{customer_id}/contacts", response_model=ContactOut, status_code=201)
def add_contact(customer_id: int, payload: ContactCreate, db: Session = Depends(get_db)):
    return service.add_contact(db, customer_id, payload)

@router.post("/{customer_id}/activities", response_model=ActivityOut, status_code=201)
def add_activity(customer_id: int, payload: ActivityCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.add_activity(db, customer_id, payload, current_user.full_name)
