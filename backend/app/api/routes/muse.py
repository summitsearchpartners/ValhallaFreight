from datetime import date
import re
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field, StrictBool, ConfigDict, model_validator
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.api.permissions import require_muse_admin
from app.core.roles import MANUFACTURER_ROLES
from app.services.muse_partner import has_access
from app.models import (Customer, MuseEnrollment, MuseCreditApplication, MuseBooking, Quote, Carrier,
                        Shipment, CarrierSubmission, OperationalNotification, MusePartnerCompany)
from app.schemas.muse import MuseRateInput
from app.services import muse, muse_enrollment as access
from app.services.muse_credit import FIELDS, BUSINESS, TEMPLATE_SHA256, filled_pdf
from app.integrations.secrets import decrypt_secret_payload

router=APIRouter(prefix="/muse",tags=["Muse Freight"])


def applicant(user=Depends(get_current_user)):
    if user.role not in MANUFACTURER_ROLES | {"admin"}:raise HTTPException(403,"Manufacturer account required")
    return user


def partner(request:Request,db:Session=Depends(get_db),user=Depends(get_current_user)):
    if not has_access(db,user) or getattr(request.state,"support_company_id",None) is not None:
        raise HTTPException(403,"Muse Freight Admin required")
    db.info["muse_partner_request"]=True
    return user


def require_company(db,user,customer_id):
    root=access.manufacturer(db,customer_id)
    if user.role!="admin" and root.id!=user.customer_id:raise HTTPException(404,"Manufacturer not found")
    return root


class OptIn(BaseModel):
    enabled: StrictBool


class CreditInput(BaseModel):
    model_config=ConfigDict(extra="forbid")
    values: dict[str,str]
    business_type: Literal["corporation","partnership","sole_proprietor","other"]
    consent: Literal[True]
    @model_validator(mode="after")
    def valid(self):
        keys={f[0] for f in FIELDS}
        if set(self.values)-keys:raise ValueError("Unknown application field")
        from reportlab.pdfbase.pdfmetrics import stringWidth
        for key,label,_,_,width,_,required in FIELDS:
            value=self.values.get(key,"").strip()
            if required and not value:raise ValueError(f"{label} is required")
            if len(value)>120 or any(ord(c)<32 or ord(c)>126 for c in value):
                raise ValueError(f"{label}: use up to 120 printable English characters")
            if stringWidth(value,"Helvetica",4)>width:raise ValueError(f"{label}: shorten the entry to fit the original form blank")
            self.values[key]=value
        if self.business_type=="other" and not self.values["other_business"]:raise ValueError("Specify the other business type")
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+",self.values["ap_email"]):raise ValueError("Enter a valid accounts payable email")
        try:date.fromisoformat(self.values["date"])
        except ValueError:raise ValueError("Use YYYY-MM-DD for the signature date")
        return self


class Decision(BaseModel):
    decision: Literal["approved","declined"]
    note: str=Field(default="",max_length=1000)
    @model_validator(mode="after")
    def reason(self):
        self.note=self.note.strip()
        if self.decision=="declined" and not self.note:raise ValueError("A reason is required for a declined application")
        return self


class ConfirmBooking(BaseModel):
    provider_reference: str=Field(min_length=1,max_length=120)
    pro_number: str=Field(min_length=1,max_length=60)
    @model_validator(mode="after")
    def clean(self):
        self.provider_reference=self.provider_reference.strip();self.pro_number=self.pro_number.strip()
        if not self.provider_reference or not self.pro_number:raise ValueError("Booking reference and PRO are required")
        return self


@router.get("/enrollment/{customer_id}")
def get_enrollment(customer_id:int,db:Session=Depends(get_db),user=Depends(applicant)):
    require_company(db,user,customer_id)
    return access.status(db,customer_id)


@router.put("/enrollment/{customer_id}/opt-in",dependencies=[Depends(require_muse_admin)])
def opt_in(customer_id:int,payload:OptIn,db:Session=Depends(get_db)):
    return access.set_enabled(db,customer_id,payload.enabled)


@router.get("/credit-form")
def credit_form(user=Depends(applicant)):
    return {"fields":[dict(zip(("key","label","x","top","width","height","required"),f)) for f in FIELDS],
            "business_types":[{"value":k,"x":x,"top":y} for k,(x,y) in BUSINESS.items()],
            "template_sha256":TEMPLATE_SHA256}


@router.post("/enrollment/{customer_id}/application",status_code=201)
def apply(customer_id:int,payload:CreditInput,db:Session=Depends(get_db),user=Depends(applicant)):
    require_company(db,user,customer_id)
    return access.submit_application(db,customer_id,{**payload.values,"business_type":payload.business_type,"consent":payload.consent},user)


def authorized_application(db,user,application_id):
    app=db.get(MuseCreditApplication,application_id)
    if not app:raise HTTPException(404,"Application not found")
    if user.role!="admin" and db.info.get("muse_partner_request"):access.require_enabled(db,app.customer_id)
    elif user.role!="admin":require_company(db,user,app.customer_id)
    return app


@router.get("/applications/{application_id}/pdf")
def application_pdf(application_id:int,request:Request,db:Session=Depends(get_db),user=Depends(get_current_user)):
    if user.role in {"broker_admin","muse_admin"}:partner(request,db,user)
    elif user.role not in MANUFACTURER_ROLES | {"admin"}:raise HTTPException(403,"Application access denied")
    app=authorized_application(db,user,application_id)
    data=decrypt_secret_payload(app.encrypted_payload)
    if not data or app.template_sha256!=TEMPLATE_SHA256:raise HTTPException(409,"Application document cannot be opened")
    return Response(filled_pdf(data),media_type="application/pdf",headers={
        "Content-Disposition":f'inline; filename="Muse-Credit-Application-{app.id}.pdf"',
        "Cache-Control":"no-store","X-Content-Type-Options":"nosniff"})


@router.get("/manufacturers")
def manufacturers(db:Session=Depends(get_db),user=Depends(partner)):
    rows=db.query(Customer).join(MuseEnrollment,MuseEnrollment.customer_id==Customer.id).filter(MuseEnrollment.enabled.is_(True)).order_by(Customer.name).all()
    return [access.status(db,r.id) for r in rows]


@router.get("/manufacturers/{manufacturer_id}")
def manufacturer_profile(manufacturer_id:int,db:Session=Depends(get_db),user=Depends(partner)):
    root,_=access.require_enabled(db,manufacturer_id)
    apps=db.query(MuseCreditApplication).filter_by(customer_id=root.id).order_by(MuseCreditApplication.id.desc()).all()
    return {**access.status(db,root.id),"applications":[
        {"id":a.id,"status":a.status,"created_at":a.created_at,"reviewed_at":a.reviewed_at,"decision_note":a.decision_note}
        for a in apps]}


@router.post("/applications/{application_id}/decision")
def decide(application_id:int,payload:Decision,db:Session=Depends(get_db),user=Depends(partner)):
    return access.decide(db,application_id,payload.decision,payload.note,user)


@router.get("/quotes")
def quotes(db:Session=Depends(get_db),user=Depends(partner)):
    rows=db.query(Quote).join(Customer,Customer.id==Quote.customer_id).filter(
        (Customer.id.in_(db.query(MuseEnrollment.customer_id).filter(MuseEnrollment.enabled.is_(True)))) |
        (Customer.manufacturer_id.in_(db.query(MuseEnrollment.customer_id).filter(MuseEnrollment.enabled.is_(True))))
    ).order_by(Quote.id.desc()).limit(200).all()
    result=[]
    for q in rows:
        preview=muse.available_preview(q,db)
        if preview is None:continue
        root=access.manufacturer(db,q.customer_id)
        carrier_ids={int(o.get("carrier_id",0)) for o in q.options or [] if o.get("provider")!="muse_freight"}
        carriers=db.query(Carrier).filter(Carrier.id.in_(carrier_ids),Carrier.active.is_(True)).all()
        result.append({"id":q.id,"quote_number":q.quote_number,"manufacturer_name":root.name,
            "origin_zip":q.origin.get("postal_code"),"destination_zip":q.destination.get("postal_code"),
            "handling_units":q.handling_units,"accessorials":q.accessorials,"pickup":q.requested_pickup_at,
            "muse_preview":preview,"carriers":[{"id":c.id,"name":c.name} for c in carriers if c.customer_id in (None,root.id)]})
    return result


@router.put("/quotes/{quote_id}/rate")
def set_rate(quote_id:int,payload:MuseRateInput,db:Session=Depends(get_db),user=Depends(partner)):
    return muse.save_rate(db,quote_id,payload)


@router.delete("/quotes/{quote_id}/rate")
def withdraw_rate(quote_id:int,db:Session=Depends(get_db),user=Depends(partner)):
    return muse.save_rate(db,quote_id,None)


@router.get("/bookings")
def bookings(db:Session=Depends(get_db),user=Depends(partner)):
    result=[]
    for b in db.query(MuseBooking).order_by(MuseBooking.id.desc()).limit(200).all():
        s=db.get(Shipment,b.shipment_id)
        root=access.manufacturer(db,b.customer_id)
        result.append({"id":b.id,"status":b.status,"manufacturer_name":root.name,"shipment_id":s.id,
            "shipment_number":s.shipment_number,"bol_number":s.bol_number,"carrier_name":s.carrier_name,
            "origin":s.origin,"destination":s.destination,"handling_units":s.handling_units,
            "accessorials":s.accessorials,"pickup":s.scheduled_pickup_at,"created_at":b.created_at,
            "carrier_cost":s.carrier_cost,"customer_price":s.customer_charge,
            "provider_reference":b.provider_reference,"pro_number":s.pro_number})
    return result


@router.post("/bookings/{booking_id}/confirm")
def confirm(booking_id:int,payload:ConfirmBooking,db:Session=Depends(get_db),user=Depends(partner)):
    b=db.query(MuseBooking).filter_by(id=booking_id).with_for_update().first()
    if not b:raise HTTPException(404,"Muse booking not found")
    if b.status!="requested":raise HTTPException(409,"Booking already confirmed")
    s=db.get(Shipment,b.shipment_id)
    b.status="confirmed";b.provider_reference=payload.provider_reference;b.confirmed_by=user.id;b.confirmed_at=access.now()
    s.pro_number=payload.pro_number;s.status="booked"
    submission=db.query(CarrierSubmission).filter_by(shipment_id=s.id,status="pending_muse_confirmation").first()
    if submission:
        submission.status="submitted";submission.pro_number=payload.pro_number;submission.provider_reference=payload.provider_reference
    db.add(OperationalNotification(audience="internal",notification_type="muse_booking_confirmed",customer_id=s.customer_id,shipment_id=s.id,
        severity="success",title="Muse booking confirmed",body=f"{s.shipment_number} · PRO {payload.pro_number}",target_path=f"/shipments/{s.id}"))
    db.commit()
    return {"ok":True}


@router.get("/bookings/{booking_id}/detail")
def booking_bol(booking_id:int,db:Session=Depends(get_db),user=Depends(partner)):
    b=db.get(MuseBooking,booking_id)
    if not b:raise HTTPException(404,"Muse booking not found")
    from app.api.routes.shipments import shipment_detail
    return shipment_detail(b.shipment_id,db)
