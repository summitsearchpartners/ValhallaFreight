from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user
from app.api.permissions import require_muse_admin
from app.domains.customers import service
from app.schemas.muse import MuseAccountStatus, MuseAccountUpdate
from app.services.muse import account_status, set_account_status
from app.domains.customers.schemas import CustomerCreate, CustomerUpdate, CustomerSummary, Customer360, LocationCreate, LocationOut, ContactCreate, ContactOut, ActivityCreate, ActivityOut, MarginProtectionUpdate, MarginProtectionOut

router = APIRouter(prefix="/customers", tags=["Customer 360"])

@router.get("", response_model=list[CustomerSummary])
def list_customers(include_workspace:bool=False,db: Session = Depends(get_db)):
    return service.list_customers(db,include_workspace)

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

@router.patch("/{customer_id}/locations/{location_id}", response_model=LocationOut)
def update_location(customer_id: int, location_id: int, payload: LocationCreate, db: Session = Depends(get_db)):
    return service.update_location(db, customer_id, location_id, payload)

@router.post("/{customer_id}/contacts", response_model=ContactOut, status_code=201)
def add_contact(customer_id: int, payload: ContactCreate, db: Session = Depends(get_db)):
    return service.add_contact(db, customer_id, payload)

@router.post("/{customer_id}/activities", response_model=ActivityOut, status_code=201)
def add_activity(customer_id: int, payload: ActivityCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    return service.add_activity(db, customer_id, payload, current_user.full_name)


@router.patch('/{customer_id}/margin-protection', response_model=MarginProtectionOut)
def update_margin_protection(customer_id: int, payload: MarginProtectionUpdate, db: Session = Depends(get_db)):
    return service.update_margin_protection(db, customer_id, payload)


@router.get('/{customer_id}/muse-account', response_model=MuseAccountStatus, dependencies=[Depends(require_muse_admin)])
def get_muse_account(customer_id: int, db: Session = Depends(get_db)):
    return account_status(db, customer_id)


@router.put('/{customer_id}/muse-account', response_model=MuseAccountStatus, dependencies=[Depends(require_muse_admin)])
def update_muse_account(customer_id: int, payload: MuseAccountUpdate, db: Session = Depends(get_db)):
    return set_account_status(db, customer_id, payload.account_verified)
