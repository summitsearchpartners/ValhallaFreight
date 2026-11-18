from datetime import datetime,timedelta
from decimal import Decimal
from io import BytesIO
from copy import deepcopy
from uuid import uuid4
from fastapi import APIRouter,Depends,HTTPException,Request
from fastapi.responses import Response
from pydantic import BaseModel,Field,model_validator,field_validator
from sqlalchemy.orm import Session
from app.api.deps import get_current_user,get_db
from app.models import TruckloadOrder,TruckloadBid,Customer,Carrier,Shipment,Quote,CarrierSubmission,TrackingEvent,SafeLoadCase

router=APIRouter(prefix='/truckload',tags=['Truckload'])

def brokers(request:Request,user=Depends(get_current_user)):
    if user.role not in {'admin','broker','broker_admin'} or getattr(request.state,'support_company_id',None) is not None:raise HTTPException(403,'Truckload operations require Broker or Super Admin access')
    return user

STATES = {'AL': 'Alabama', 'AK': 'Alaska', 'AZ': 'Arizona', 'AR': 'Arkansas', 'CA': 'California', 'CO': 'Colorado', 'CT': 'Connecticut', 'DE': 'Delaware', 'DC': 'District of Columbia', 'FL': 'Florida', 'GA': 'Georgia', 'HI': 'Hawaii', 'ID': 'Idaho', 'IL': 'Illinois', 'IN': 'Indiana', 'IA': 'Iowa', 'KS': 'Kansas', 'KY': 'Kentucky', 'LA': 'Louisiana', 'ME': 'Maine', 'MD': 'Maryland', 'MA': 'Massachusetts', 'MI': 'Michigan', 'MN': 'Minnesota', 'MS': 'Mississippi', 'MO': 'Missouri', 'MT': 'Montana', 'NE': 'Nebraska', 'NV': 'Nevada', 'NH': 'New Hampshire', 'NJ': 'New Jersey', 'NM': 'New Mexico', 'NY': 'New York', 'NC': 'North Carolina', 'ND': 'North Dakota', 'OH': 'Ohio', 'OK': 'Oklahoma', 'OR': 'Oregon', 'PA': 'Pennsylvania', 'RI': 'Rhode Island', 'SC': 'South Carolina', 'SD': 'South Dakota', 'TN': 'Tennessee', 'TX': 'Texas', 'UT': 'Utah', 'VT': 'Vermont', 'VA': 'Virginia', 'WA': 'Washington', 'WV': 'West Virginia', 'WI': 'Wisconsin', 'WY': 'Wyoming', 'PR': 'Puerto Rico', 'VI': 'Virgin Islands', 'GU': 'Guam', 'AS': 'American Samoa', 'MP': 'Northern Mariana Islands'}

class Stop(BaseModel):
    @field_validator("state", mode="before")
    @classmethod
    def normalize_state(cls, value):
        text = str(value).strip().upper()
        normalized = next((code for code,name in STATES.items() if name.upper() == text), text)
        if normalized not in STATES:
            raise ValueError("Choose a US state, for example Kansas (KS)")
        return normalized

    kind:str
    name:str=Field(min_length=2,max_length=120)
    address1:str=Field(min_length=3,max_length=180)
    city:str=Field(min_length=2,max_length=80)
    state:str=Field(min_length=2,max_length=3)
    postal_code:str=Field(min_length=5,max_length=12)
    appointment_at:datetime
    contact:str=Field(default='',max_length=180)
    phone:str=Field(default='',max_length=40)
    instructions:str=Field(default='',max_length=1000)
    @model_validator(mode='after')
    def valid(self):
        if any(not getattr(self,key).strip() for key in ('name','address1','city','state','postal_code')):raise ValueError('Each stop requires a complete facility and street address')
        if self.kind not in {'pickup','delivery'}:raise ValueError('Stop type must be pickup or delivery')
        if self.appointment_at.tzinfo is not None:raise ValueError('Enter facility appointment time without a timezone offset')
        return self
class OrderIn(BaseModel):
    customer_id:int
    reference:str=Field(default='',max_length=120)
    equipment:str
    commodity:str=Field(min_length=2,max_length=240)
    weight_lbs:int=Field(ge=1,le=200000)
    packages:int=Field(ge=1,le=100000)
    temperature_min:int|None=None
    temperature_max:int|None=None
    stops:list[Stop]=Field(min_length=2,max_length=20)
    customer_price:Decimal=Field(gt=0,max_digits=12,decimal_places=2)
    notes:str=Field(default='',max_length=4000)
    @model_validator(mode='after')
    def valid(self):
        if self.equipment not in {'Dry van','Reefer','Flatbed','Step deck','Power only','Box truck'}:raise ValueError('Choose supported equipment')
        if any(stop.kind=='pickup' for stop in self.stops[1:]):raise ValueError('Safe Load currently supports one pickup per shipment. Create a separate shipment for each additional warehouse pickup.')
        if self.stops[0].kind!='pickup' or self.stops[-1].kind!='delivery':raise ValueError('Begin with pickup and end with delivery')
        if any(b.appointment_at<a.appointment_at for a,b in zip(self.stops,self.stops[1:])):raise ValueError('Stop appointments must be in route order')
        if self.equipment=='Reefer' and (self.temperature_min is None or self.temperature_max is None or self.temperature_min>self.temperature_max):raise ValueError('Reefer loads require a valid Fahrenheit temperature range')
        return self
class BidIn(BaseModel):
    carrier_id:int
    carrier_cost:Decimal=Field(gt=0,max_digits=12,decimal_places=2)
    expires_at:datetime
    note:str=Field(default='',max_length=1000)
    @model_validator(mode='after')
    def valid(self):
        if self.expires_at.tzinfo or self.expires_at<=datetime.utcnow():raise ValueError('Bid expiry must be a future UTC date/time without offset')
        return self
class SelectBid(BaseModel):bid_id:int

def order(db,oid,lock=False):
    q=db.query(TruckloadOrder).filter_by(id=oid)
    row=(q.with_for_update() if lock else q).first()
    if not row:raise HTTPException(404,'Truckload order not found')
    return row

def output(db,row):
    bids=db.query(TruckloadBid).filter_by(order_id=row.id).order_by(TruckloadBid.carrier_cost).all()
    ship=db.get(Shipment,row.shipment_id) if row.shipment_id else None
    safe=db.get(SafeLoadCase,row.shipment_id) if row.shipment_id else None
    return {k:getattr(row,k) for k in ['id','customer_id','reference','status','equipment','commodity','weight_lbs','packages','temperature_min','temperature_max','stops','customer_price','selected_bid_id','notes','shipment_id','created_at']}|{
        'status':('delivered' if ship and ship.status=='delivered' else 'in_transit' if ship and ship.status in {'picked_up','in_transit','out_for_delivery','at_destination_terminal'} else 'cancelled' if ship and ship.status in {'cancelled','canceled'} else row.status),'safe_load_status':safe.status if safe else None,'customer_name':db.get(Customer,row.customer_id).name,'shipment_number':ship.shipment_number if ship else None,'shipment_status':ship.status if ship else None,
        'bids':[{'id':b.id,'carrier_id':b.carrier_id,'carrier_name':db.get(Carrier,b.carrier_id).name,'carrier_cost':b.carrier_cost,'expires_at':b.expires_at,'note':b.note,'gross_profit':row.customer_price-b.carrier_cost} for b in bids]}

@router.get('')
def list_orders(user=Depends(brokers),db:Session=Depends(get_db)):
    return [output(db,r) for r in db.query(TruckloadOrder).order_by(TruckloadOrder.created_at.desc()).limit(300)]

@router.post('')
def create(p:OrderIn,user=Depends(brokers),db:Session=Depends(get_db)):
    if not db.get(Customer,p.customer_id):raise HTTPException(404,'Customer not found')
    row=TruckloadOrder(**p.model_dump(exclude={'stops'}),stops=[s.model_dump(mode='json') for s in p.stops],status='quoted')
    db.add(row);db.commit();return output(db,row)

@router.patch('/{oid}')
def edit(oid:int,p:OrderIn,user=Depends(brokers),db:Session=Depends(get_db)):
    row=order(db,oid,True)
    if row.shipment_id:raise HTTPException(409,'Booked truckload quotes are locked')
    if not db.get(Customer,p.customer_id):raise HTTPException(404,'Customer not found')
    for field,value in p.model_dump(exclude={'stops'}).items():setattr(row,field,value)
    row.stops=[stop.model_dump(mode='json') for stop in p.stops]
    row.selected_bid_id=None
    for bid in db.query(TruckloadBid).filter_by(order_id=oid).all():bid.expires_at=datetime.utcnow()
    db.commit();return output(db,row)

@router.get('/{oid}')
def detail(oid:int,user=Depends(brokers),db:Session=Depends(get_db)):return output(db,order(db,oid))

@router.get('/{oid}/lane-history')
def history(oid:int,user=Depends(brokers),db:Session=Depends(get_db)):
    row=order(db,oid)
    matches=[r for r in db.query(TruckloadOrder).filter(TruckloadOrder.shipment_id.is_not(None),TruckloadOrder.id!=oid).all() if r.equipment==row.equipment and r.stops[0]['postal_code'][:3]==row.stops[0]['postal_code'][:3] and r.stops[-1]['postal_code'][:3]==row.stops[-1]['postal_code'][:3]]
    costs=[]
    for r in matches:
        ship=db.get(Shipment,r.shipment_id)
        if ship:costs.append(float(ship.carrier_cost))
    return {'sample_size':len(costs),'source':'Your booked truckload history · matching equipment and 3-digit ZIP regions','carrier_cost_low':min(costs) if costs else None,'carrier_cost_high':max(costs) if costs else None,'carrier_cost_average':sum(costs)/len(costs) if costs else None,'market_feed_connected':False}

@router.post('/{oid}/bids')
def bid(oid:int,p:BidIn,user=Depends(brokers),db:Session=Depends(get_db)):
    row=order(db,oid,True)
    if row.shipment_id:raise HTTPException(409,'Booked rates are locked')
    carrier=db.get(Carrier,p.carrier_id)
    if not carrier or not carrier.active:raise HTTPException(404,'Active carrier not found')
    db.add(TruckloadBid(order_id=oid,customer_id=row.customer_id,**p.model_dump()));db.commit();return output(db,row)

@router.post('/{oid}/select')
def select(oid:int,p:SelectBid,user=Depends(brokers),db:Session=Depends(get_db)):
    row=order(db,oid,True);bid=db.get(TruckloadBid,p.bid_id)
    if row.shipment_id:raise HTTPException(409,'Booked rates are locked')
    if not bid or bid.order_id!=oid or bid.expires_at<=datetime.utcnow():raise HTTPException(409,'Choose a current carrier bid')
    row.selected_bid_id=bid.id;db.commit();return output(db,row)

@router.post('/{oid}/book')
def book(oid:int,user=Depends(brokers),db:Session=Depends(get_db)):
    row=order(db,oid,True)
    if row.shipment_id:return output(db,row)
    bid=db.get(TruckloadBid,row.selected_bid_id) if row.selected_bid_id else None
    if not bid or bid.expires_at<=datetime.utcnow():raise HTTPException(409,'Select a current carrier bid before booking')
    first,last=row.stops[0],row.stops[-1]
    origin={**first,'country':'US','contact_name':first.get('contact')};destination={**last,'country':'US','contact_name':last.get('contact')}
    units=[{'quantity':row.packages,'type':'Package','weight_lbs':float(row.weight_lbs)/row.packages,'freight_class':'Truckload','description':row.commodity}]
    number='FTL-'+uuid4().hex[:14].upper()
    carrier=db.get(Carrier,bid.carrier_id)
    if not carrier or not carrier.active:raise HTTPException(409,'The selected carrier is no longer active. Choose another current bid.')
    q=Quote(quote_number=number,customer_id=row.customer_id,status='booked',origin=origin,destination=destination,handling_units=units,accessorials=[],options=[{'carrier_id':bid.carrier_id,'carrier_name':carrier.name,'scac':carrier.scac,'service':'Truckload','gross_profit':str(row.customer_price-bid.carrier_cost),'margin_pct':str((row.customer_price-bid.carrier_cost)/row.customer_price*100),'carrier_cost':str(bid.carrier_cost),'customer_price':str(row.customer_price),'selected':True,'provider':'truckload','transit_days':0}],requested_pickup_at=datetime.fromisoformat(first['appointment_at']),requested_delivery_at=datetime.fromisoformat(last['appointment_at']))
    db.add(q);db.flush()
    ship=Shipment(shipment_number=number,quote_id=q.id,customer_id=row.customer_id,carrier_id=bid.carrier_id,status='booked',origin=origin,destination=destination,handling_units=units,accessorials=[],carrier_cost=bid.carrier_cost,customer_charge=row.customer_price,commodity_description=row.commodity,package_count=row.packages,package_type='Package',scheduled_pickup_at=q.requested_pickup_at,requested_delivery_at=q.requested_delivery_at,customer_reference=row.reference)
    db.add(ship);db.flush()
    from app.api.routes.shipments import _assign_bol_number
    ship.bol_number=_assign_bol_number(db,ship);row.shipment_id=ship.id;row.status='booked'
    db.add(CarrierSubmission(shipment_id=ship.id,carrier_id=bid.carrier_id,status='manual_tender_pending',request_summary={'provider':'truckload'}))
    db.commit();return output(db,row)

@router.post('/{oid}/stops/{index}/complete')
def complete(oid:int,index:int,user=Depends(brokers),db:Session=Depends(get_db)):
    row=order(db,oid,True)
    if not row.shipment_id:raise HTTPException(409,'Book the load first')
    from app.services.safe_load import case
    if case(db,row.shipment_id,True).status!='released':raise HTTPException(409,'Safe Load release is required')
    stops=deepcopy(row.stops)
    if not 0<=index<len(stops) or any(not s.get('completed_at') for s in stops[:index]):raise HTTPException(409,'Complete stops in route order')
    if stops[index].get('completed_at'):return output(db,row)
    stops[index]['completed_at']=datetime.utcnow().isoformat();row.stops=stops
    ship=db.get(Shipment,row.shipment_id)
    final=index==len(stops)-1
    ship.status='delivered' if final else 'in_transit'
    if final:ship.delivered_at=datetime.utcnow();row.status='delivered'
    else:row.status='in_transit'
    db.add(TrackingEvent(shipment_id=ship.id,status='DELIVERED' if final else 'IN_TRANSIT',code='FTL_STOP',description=f"Stop {index+1} completed: {stops[index]['name']}",source='manual',event_time=datetime.utcnow()))
    db.commit();return output(db,row)

@router.get('/{oid}/rate-confirmation')
def rate_confirmation(oid:int,user=Depends(brokers),db:Session=Depends(get_db)):
    row=order(db,oid);bid=db.get(TruckloadBid,row.selected_bid_id) if row.selected_bid_id else None
    if not bid:raise HTTPException(409,'Select a carrier bid first')
    from reportlab.pdfgen import canvas
    from reportlab.lib.utils import simpleSplit
    output=BytesIO();pdf=canvas.Canvas(output,pagesize=(612,792));y=750
    lines=['VALHALLA FREIGHT · CARRIER RATE CONFIRMATION',f'Load FTL-{row.id} · Reference {row.reference}',f'Carrier: {db.get(Carrier,bid.carrier_id).name}',f'Equipment: {row.equipment} · Weight: {row.weight_lbs} lb · Packages: {row.packages}',f'Commodity: {row.commodity}',f'Agreed carrier rate: ${bid.carrier_cost:,.2f}','Tender acceptance must be confirmed directly with the carrier.','SAFE LOAD: Warehouse release requires approved driver, license photo, license scan and matching truck VIN.']
    for i,s in enumerate(row.stops):lines.append(f"STOP {i+1} {s['kind'].upper()}: {s['name']} · {s['address1']}, {s['city']} {s['state']} {s['postal_code']} · Facility local appointment {s['appointment_at']} · {s['contact']} {s['phone']}")
    for text in lines:
        for line in simpleSplit(text,'Helvetica',10,520):
            if y<60:pdf.showPage();y=750
            pdf.setFont('Helvetica',10);pdf.drawString(45,y,line);y-=17
        y-=10
    pdf.save();return Response(output.getvalue(),media_type='application/pdf',headers={'Content-Disposition':f'attachment; filename=FTL-{oid}-rate-confirmation.pdf'})
