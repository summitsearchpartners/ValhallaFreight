from datetime import datetime
from decimal import Decimal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import CapacityLoad, CapacityOffer, Carrier

router=APIRouter(prefix='/capacity',tags=['Capacity'])
class LoadCreate(BaseModel):
    mode:str='FTL';equipment:str='Dry Van';origin:dict;destination:dict;pickup_at:datetime|None=None;delivery_at:datetime|None=None;customer_revenue:Decimal=Decimal('0');target_buy:Decimal=Decimal('0');market_rate:Decimal=Decimal('0')
class OfferCreate(BaseModel):
    carrier_id:int|None=None;carrier_name:str;amount:Decimal;source:str='Private Network'

@router.get('')
def list_loads(db:Session=Depends(get_db)):
    loads=db.query(CapacityLoad).order_by(CapacityLoad.created_at.desc()).all();out=[]
    for l in loads:
        offers=db.query(CapacityOffer).filter(CapacityOffer.load_id==l.id).order_by(CapacityOffer.amount).all()
        out.append({'id':l.id,'mode':l.mode,'equipment':l.equipment,'origin':l.origin,'destination':l.destination,'pickup_at':l.pickup_at,'delivery_at':l.delivery_at,'customer_revenue':float(l.customer_revenue),'target_buy':float(l.target_buy),'market_rate':float(l.market_rate),'status':l.status,'posted_to':l.posted_to,'offer_count':len(offers),'best_offer':float(offers[0].amount) if offers else None})
    return out
@router.post('')
def create_load(payload:LoadCreate,db:Session=Depends(get_db)):
    row=CapacityLoad(**payload.model_dump());db.add(row);db.commit();db.refresh(row);return {'id':row.id}
@router.get('/{load_id}')
def detail(load_id:int,db:Session=Depends(get_db)):
    l=db.get(CapacityLoad,load_id)
    if not l: raise HTTPException(404,'Load not found')
    offers=db.query(CapacityOffer).filter(CapacityOffer.load_id==load_id).order_by(CapacityOffer.amount).all()
    return {'load':{'id':l.id,'mode':l.mode,'equipment':l.equipment,'origin':l.origin,'destination':l.destination,'pickup_at':l.pickup_at,'delivery_at':l.delivery_at,'customer_revenue':float(l.customer_revenue),'target_buy':float(l.target_buy),'market_rate':float(l.market_rate),'status':l.status,'posted_to':l.posted_to},'offers':[{'id':o.id,'carrier_id':o.carrier_id,'carrier_name':o.carrier_name,'amount':float(o.amount),'source':o.source,'status':o.status,'created_at':o.created_at} for o in offers]}
@router.post('/{load_id}/offers')
def add_offer(load_id:int,payload:OfferCreate,db:Session=Depends(get_db)):
    if not db.get(CapacityLoad,load_id): raise HTTPException(404,'Load not found')
    row=CapacityOffer(load_id=load_id,**payload.model_dump());db.add(row);db.commit();db.refresh(row);return {'id':row.id}
@router.post('/{load_id}/post/{provider}')
def post_load(load_id:int,provider:str,db:Session=Depends(get_db)):
    l=db.get(CapacityLoad,load_id)
    if not l: raise HTTPException(404,'Load not found')
    arr=list(l.posted_to or []); name=provider.upper()
    if name not in arr: arr.append(name)
    l.posted_to=arr;db.commit();return {'ok':True,'posted_to':arr,'note':'Development adapter recorded the posting. Live provider transmission requires configured credentials.'}
