from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.api.deps import get_db
from app.api.permissions import require_muse_admin
from app.models import MusePartnerCompany, Customer
from app.services.user_activity import add_activity

router=APIRouter(prefix="/admin/muse-partner",tags=["Muse Partner Designation"],
                 dependencies=[Depends(require_muse_admin)])


class PartnerInput(BaseModel):
    company_id: int | None = Field(default=None,gt=0)


def current(db):
    row=db.get(MusePartnerCompany,1)
    company=db.get(Customer,row.company_id) if row and row.company_id else None
    return {"company_id":row.company_id if row else None,"company_name":company.name if company else None}


@router.get("")
def designation(db:Session=Depends(get_db)):
    return current(db)


@router.put("")
def assign(payload:PartnerInput,db:Session=Depends(get_db),user=Depends(require_muse_admin)):
    if payload.company_id:
        company=db.get(Customer,payload.company_id)
        if not company or company.manufacturer_id is not None:raise HTTPException(422,"Choose a parent company workspace")
    row=db.query(MusePartnerCompany).filter_by(id=1).with_for_update().first()
    if row is None:
        row=MusePartnerCompany(id=1);db.add(row)
    previous=row.company_id
    row.company_id=payload.company_id
    add_activity(db,user,"muse_partner_company_changed",details={"previous_company_id":previous,"company_id":payload.company_id})
    db.commit()
    return current(db)
