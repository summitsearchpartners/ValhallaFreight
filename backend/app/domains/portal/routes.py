from decimal import Decimal
from fastapi import Request, APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from pathlib import Path
import os, uuid

from app.api.deps import get_db, get_current_user
from app.core.config import settings
from app.models import Customer, Quote, Shipment, Invoice, Carrier, TrackingEvent, CustomerProfile, CustomerLocation, ShipmentDocument, MarginProtectionNotification, User

router=APIRouter(prefix='/portal', tags=['Customer Portal'])


def portal_actor(request:Request, db:Session=Depends(get_db), user:User=Depends(get_current_user)):
    if user.role=='admin':
        from types import SimpleNamespace
        company_id=getattr(request.state,'integration_company_id',None)
        if not company_id:raise HTTPException(422,'Select a company portal')
        from app.services.portal_access import require_session
        session=require_session(db,user,request.headers.get('X-Portal-Session'),company_id,'customer')
        return SimpleNamespace(id=user.id,email=user.email,full_name=user.full_name,role='customer',actual_role='admin',customer_id=company_id,support_expires_at=session.expires_at)
    return user


def _portal_user(user:User)->User:
    if str(user.role).lower()!='customer' or not user.customer_id:
        raise HTTPException(status_code=403, detail='Customer portal access required')
    return user


def _shipment_row(s:Shipment):
    return {
        'id':s.id,'shipment_number':s.shipment_number,'status':s.status,'pro_number':s.pro_number,'bol_number':s.bol_number,
        'carrier_name':s.carrier_name,'carrier_scac':s.carrier_scac,'origin':s.origin,'destination':s.destination,
        'customer_charge':float(s.customer_charge or 0),'pickup_date':s.pickup_date,'estimated_delivery':s.estimated_delivery,
        'scheduled_pickup_at':s.scheduled_pickup_at,'requested_delivery_at':s.requested_delivery_at,'actual_pickup_at':s.actual_pickup_at,'delivered_at':s.delivered_at,
        'po_number':s.po_number,'customer_reference':s.customer_reference,'package_count':s.package_count,'package_type':s.package_type,
        'commodity_description':s.commodity_description,'payment_terms':s.payment_terms,'created_at':s.created_at,
    }

@router.get('/me')
def portal_me(db:Session=Depends(get_db), user:User=Depends(portal_actor)):
    user=_portal_user(user); customer=db.get(Customer,user.customer_id)
    if not customer: raise HTTPException(status_code=404,detail='Customer account not found')
    profile=db.query(CustomerProfile).filter(CustomerProfile.customer_id==customer.id).first()
    locations=db.query(CustomerLocation).filter(CustomerLocation.customer_id==customer.id,CustomerLocation.active.is_(True)).order_by(CustomerLocation.name).all()
    shipments=db.query(Shipment).filter(Shipment.customer_id==customer.id).order_by(Shipment.created_at.desc()).limit(100).all()
    quotes=db.query(Quote).filter(Quote.customer_id==customer.id).order_by(Quote.created_at.desc()).limit(100).all()
    invoices=db.query(Invoice).filter(Invoice.customer_id==customer.id).order_by(Invoice.created_at.desc()).limit(100).all()
    notices=db.query(MarginProtectionNotification).filter(MarginProtectionNotification.customer_id==customer.id,MarginProtectionNotification.audience=='customer').order_by(MarginProtectionNotification.created_at.desc()).limit(50).all()
    active=sum(1 for s in shipments if str(s.status).lower() not in {'delivered','cancelled','closed'})
    delivered=sum(1 for s in shipments if str(s.status).lower()=='delivered' or s.delivered_at)
    spend=sum(float(s.customer_charge or 0) for s in shipments)
    return {
      'user':{'id':user.id,'email':user.email,'full_name':user.full_name,'role':getattr(user,'actual_role',user.role)},
      'support_session':{'expires_at':user.support_expires_at} if hasattr(user,'support_expires_at') else None,
      'customer':{'id':customer.id,'code':customer.code,'name':customer.name,'industry':customer.industry,'billing_email':customer.billing_email},
      'profile':{'margin_protection_threshold':float(profile.margin_protection_threshold if profile else 75),'margin_protection_email_notify':bool(profile.margin_protection_email_notify if profile else False),'payment_terms':profile.payment_terms if profile else 'Net 30'},
      'kpis':{'active_shipments':active,'delivered_shipments':delivered,'total_shipments':len(shipments),'total_spend':spend,'open_alerts':sum(1 for n in notices if n.status=='unread'),'open_quotes':sum(1 for q in quotes if q.status in {'open','selected'})},
      'locations':[{'id':x.id,'name':x.name,'location_type':x.location_type,'address1':x.address1,'city':x.city,'state':x.state,'postal_code':x.postal_code,'appointment_required':x.appointment_required,'liftgate_default':x.liftgate_default,'residential':x.residential,'limited_access':x.limited_access} for x in locations],
      'shipments':[_shipment_row(s) for s in shipments],
      'quotes':[{'id':q.id,'quote_number':q.quote_number,'status':q.status,'origin':q.origin,'destination':q.destination,'created_at':q.created_at,'expires_at':q.expires_at,'payment_terms':q.payment_terms,'selected_option':next((o for o in (q.options or []) if o.get('selected')),None)} for q in quotes],
      'invoices':[{'id':i.id,'invoice_number':i.invoice_number,'shipment_id':i.shipment_id,'amount':float(i.amount or 0),'status':i.status,'due_date':i.due_date,'created_at':i.created_at} for i in invoices],
      'alerts':[{'id':n.id,'title':n.title,'body':n.body,'severity':n.severity,'status':n.status,'shipment_id':n.shipment_id,'created_at':n.created_at} for n in notices],
    }

@router.patch('/me/margin-protection')
def update_margin(payload:dict, db:Session=Depends(get_db), user:User=Depends(portal_actor)):
    user=_portal_user(user); profile=db.query(CustomerProfile).filter(CustomerProfile.customer_id==user.customer_id).first()
    if not profile: raise HTTPException(status_code=404,detail='Customer profile not found')
    threshold=max(Decimal('0'),Decimal(str(payload.get('threshold',profile.margin_protection_threshold))))
    profile.margin_protection_threshold=threshold
    profile.margin_protection_email_notify=bool(payload.get('email_notify',profile.margin_protection_email_notify))
    profile.margin_protection_customer_notify=True
    db.commit(); db.refresh(profile)
    return {'ok':True,'threshold':float(profile.margin_protection_threshold),'email_notify':profile.margin_protection_email_notify}

@router.get('/shipments/{shipment_id}')
def shipment_detail(shipment_id:int, db:Session=Depends(get_db), user:User=Depends(portal_actor)):
    user=_portal_user(user); s=db.get(Shipment,shipment_id)
    if not s or s.customer_id!=user.customer_id: raise HTTPException(status_code=404,detail='Shipment not found')
    events=db.query(TrackingEvent).filter(TrackingEvent.shipment_id==s.id).order_by(TrackingEvent.event_time.desc()).all()
    docs=db.query(ShipmentDocument).filter(ShipmentDocument.shipment_id==s.id).order_by(ShipmentDocument.created_at.desc()).all()
    row=_shipment_row(s)
    row['tracking']=[{'id':e.id,'status':e.status,'description':e.description,'location':e.location,'event_time':e.event_time,'source':e.source} for e in events]
    row['documents']=[{'id':d.id,'document_type':d.document_type,'name':d.original_name,'size_bytes':d.size_bytes,'created_at':d.created_at} for d in docs]
    return row

@router.get('/documents')
def list_documents(db:Session=Depends(get_db), user:User=Depends(portal_actor)):
    user=_portal_user(user)
    rows=db.query(ShipmentDocument,Shipment).join(Shipment,Shipment.id==ShipmentDocument.shipment_id).filter(Shipment.customer_id==user.customer_id).order_by(ShipmentDocument.created_at.desc()).limit(250).all()
    return [{'id':d.id,'shipment_id':s.id,'shipment_number':s.shipment_number,'document_type':d.document_type,'name':d.original_name,'size_bytes':d.size_bytes,'created_at':d.created_at} for d,s in rows]

@router.post('/shipments/{shipment_id}/documents')
async def upload_document(shipment_id:int, file:UploadFile=File(...), document_type:str=Form('Other'), db:Session=Depends(get_db), user:User=Depends(portal_actor)):
    user=_portal_user(user); s=db.get(Shipment,shipment_id)
    if not s or s.customer_id!=user.customer_id: raise HTTPException(status_code=404,detail='Shipment not found')
    content=await file.read(); max_bytes=settings.max_compliance_document_mb*1024*1024
    if len(content)>max_bytes: raise HTTPException(status_code=413,detail=f'File exceeds {settings.max_compliance_document_mb} MB limit')
    allowed={'application/pdf','image/jpeg','image/png','image/webp','application/msword','application/vnd.openxmlformats-officedocument.wordprocessingml.document'}
    if file.content_type and file.content_type not in allowed: raise HTTPException(status_code=400,detail='Unsupported document type')
    storage=Path(settings.document_storage_path)/'shipments'; storage.mkdir(parents=True,exist_ok=True)
    ext=Path(file.filename or '').suffix.lower(); stored=f'{uuid.uuid4().hex}{ext}'; (storage/stored).write_bytes(content)
    row=ShipmentDocument(shipment_id=s.id,document_type=document_type,original_name=file.filename or 'document',stored_name=stored,content_type=file.content_type,size_bytes=len(content),uploaded_by_role='customer',uploaded_by=user.full_name)
    db.add(row); db.commit(); db.refresh(row)
    return {'id':row.id,'name':row.original_name,'document_type':row.document_type,'created_at':row.created_at}

@router.get('/documents/{document_id}')
def download_document(document_id:int, db:Session=Depends(get_db), user:User=Depends(portal_actor)):
    user=_portal_user(user)
    row=db.query(ShipmentDocument,Shipment).join(Shipment,Shipment.id==ShipmentDocument.shipment_id).filter(ShipmentDocument.id==document_id,Shipment.customer_id==user.customer_id).first()
    if not row: raise HTTPException(status_code=404,detail='Document not found')
    d,s=row; path=Path(settings.document_storage_path)/'shipments'/d.stored_name
    if not path.exists(): raise HTTPException(status_code=404,detail='Stored file not found')
    return FileResponse(path,media_type=d.content_type or 'application/octet-stream',filename=d.original_name)
