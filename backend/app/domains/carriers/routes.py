from datetime import date, datetime, timedelta
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Carrier, CarrierProfile, CarrierContact, CarrierTerminal, CarrierCompliance, Shipment, Claim

router=APIRouter(prefix='/carrier-360',tags=['Carrier 360'])

class CarrierUpdate(BaseModel):
    preferred: bool | None=None
    authority_status: str | None=None
    payment_terms: str | None=None
    factoring_company: str | None=None
    cargo_limit: Decimal | None=None
    auto_liability_limit: Decimal | None=None
    insurance_expires_at: date | None=None
    notes: str | None=None

class ContactCreate(BaseModel):
    name:str; role:str='Operations'; email:str|None=None; phone:str|None=None; primary:bool=False

@router.get('')
def list_carrier_360(db:Session=Depends(get_db)):
    carriers=db.query(Carrier).order_by(Carrier.name).all()
    result=[]
    for c in carriers:
        p=db.query(CarrierProfile).filter(CarrierProfile.carrier_id==c.id).first()
        shipments=db.query(Shipment).filter(Shipment.carrier_id==c.id).count()
        revenue,cost=db.query(func.coalesce(func.sum(Shipment.customer_charge),0),func.coalesce(func.sum(func.coalesce(Shipment.final_carrier_cost,Shipment.carrier_cost)),0)).filter(Shipment.carrier_id==c.id).one()
        result.append({'id':c.id,'scac':c.scac,'name':c.name,'mode':c.mode,'active':c.active,'api_enabled':c.api_enabled,'on_time_pct':float(c.on_time_pct or 0),'claims_pct':float(c.claims_pct or 0),'preferred':bool(p.preferred) if p else False,'authority_status':p.authority_status if p else 'pending','shipments':shipments,'revenue':float(revenue or 0),'carrier_cost':float(cost or 0)})
    return result

@router.get('/{carrier_id}')
def carrier_detail(carrier_id:int,db:Session=Depends(get_db)):
    c=db.get(Carrier,carrier_id)
    if not c: raise HTTPException(404,'Carrier not found')
    p=db.query(CarrierProfile).filter(CarrierProfile.carrier_id==carrier_id).first()
    contacts=db.query(CarrierContact).filter(CarrierContact.carrier_id==carrier_id).order_by(CarrierContact.primary.desc(),CarrierContact.name).all()
    terminals=db.query(CarrierTerminal).filter(CarrierTerminal.carrier_id==carrier_id).all()
    compliance=db.query(CarrierCompliance).filter(CarrierCompliance.carrier_id==carrier_id).all()
    shipments=db.query(Shipment).filter(Shipment.carrier_id==carrier_id).order_by(Shipment.created_at.desc()).limit(12).all()
    claim_count=db.query(Claim).join(Shipment,Claim.shipment_id==Shipment.id).filter(Shipment.carrier_id==carrier_id).count()
    delivered=[s for s in shipments if s.delivered_at]
    gp=sum(float(s.customer_charge or 0)-float(s.final_carrier_cost if s.final_carrier_cost is not None else s.carrier_cost or 0) for s in shipments)
    spend=sum(float(s.final_carrier_cost if s.final_carrier_cost is not None else s.carrier_cost or 0) for s in shipments)
    return {
      'carrier':{'id':c.id,'scac':c.scac,'name':c.name,'mode':c.mode,'active':c.active,'api_enabled':c.api_enabled,'on_time_pct':float(c.on_time_pct or 0),'claims_pct':float(c.claims_pct or 0)},
      'profile':None if not p else {'mc_number':p.mc_number,'dot_number':p.dot_number,'authority_status':p.authority_status,'payment_terms':p.payment_terms,'factoring_company':p.factoring_company,'cargo_limit':float(p.cargo_limit or 0),'auto_liability_limit':float(p.auto_liability_limit or 0),'insurance_expires_at':p.insurance_expires_at,'preferred':p.preferred,'notes':p.notes},
      'contacts':[{'id':x.id,'name':x.name,'role':x.role,'email':x.email,'phone':x.phone,'primary':x.primary} for x in contacts],
      'terminals':[{'id':x.id,'name':x.name,'city':x.city,'state':x.state,'postal_code':x.postal_code,'phone':x.phone} for x in terminals],
      'compliance':[{'id':x.id,'item_type':x.item_type,'status':x.status,'expires_at':x.expires_at,'verified_at':x.verified_at,'document_url':x.document_url} for x in compliance],
      'performance':{'shipments':db.query(Shipment).filter(Shipment.carrier_id==carrier_id).count(),'recent_deliveries':len(delivered),'recent_spend':spend,'recent_gp':gp,'claims':claim_count,'on_time_pct':float(c.on_time_pct or 0)},
      'recent_shipments':[{'id':s.id,'shipment_number':s.shipment_number,'status':s.status,'origin':s.origin,'destination':s.destination,'customer_charge':float(s.customer_charge or 0),'carrier_cost':float(s.final_carrier_cost if s.final_carrier_cost is not None else s.carrier_cost or 0),'created_at':s.created_at} for s in shipments]
    }

@router.patch('/{carrier_id}')
def update_carrier(carrier_id:int,payload:CarrierUpdate,db:Session=Depends(get_db)):
    c=db.get(Carrier,carrier_id)
    if not c: raise HTTPException(404,'Carrier not found')
    p=db.query(CarrierProfile).filter(CarrierProfile.carrier_id==carrier_id).first()
    if not p:
        p=CarrierProfile(carrier_id=carrier_id);db.add(p)
    for k,v in payload.model_dump(exclude_unset=True).items(): setattr(p,k,v)
    db.commit(); return {'ok':True}

@router.post('/{carrier_id}/contacts')
def add_contact(carrier_id:int,payload:ContactCreate,db:Session=Depends(get_db)):
    if not db.get(Carrier,carrier_id): raise HTTPException(404,'Carrier not found')
    row=CarrierContact(carrier_id=carrier_id,**payload.model_dump());db.add(row);db.commit();db.refresh(row)
    return {'id':row.id,'name':row.name,'role':row.role,'email':row.email,'phone':row.phone,'primary':row.primary}
