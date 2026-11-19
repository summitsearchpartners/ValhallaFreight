from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.api.deps import get_current_user, get_db
from app.domains.customers import service
from app.domains.customers.schemas import MarginProtectionUpdate
from app.models import MarginProtectionNotification


def super_admin(request:Request,user=Depends(get_current_user)):
    if user.role!="admin" or getattr(request.state,"support_company_id",None) is not None:
        raise HTTPException(403,"Valhalla TMS Super Admin required for Customer Portal administration")
    return user


router=APIRouter(prefix="/portal-administration",tags=["Customer Portal Administration"],dependencies=[Depends(super_admin)])


@router.get("/customers")
def customers(db:Session=Depends(get_db)):
    return service.list_customers(db)


@router.get("/customers/{customer_id}")
def customer(customer_id:int,db:Session=Depends(get_db)):
    data=service.get_customer_360(db,customer_id)
    rows=db.query(MarginProtectionNotification).filter_by(customer_id=customer_id,audience="customer").order_by(MarginProtectionNotification.created_at.desc()).limit(100).all()
    return {"customer":data,"notices":[{"id":n.id,"title":n.title,"body":n.body,"severity":n.severity,"status":n.status,"created_at":n.created_at} for n in rows]}


@router.patch("/customers/{customer_id}")
def save(customer_id:int,payload:MarginProtectionUpdate,db:Session=Depends(get_db)):
    return service.update_margin_protection(db,customer_id,payload)
