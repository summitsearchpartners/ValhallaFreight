from decimal import Decimal
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models import Customer, Carrier, PricingRule, User
from app.services.auth import hash_password

def seed(db: Session):
    if not db.query(User).filter(User.email == settings.default_admin_email.lower()).first():
        db.add(User(
            email=settings.default_admin_email.lower(),
            full_name="Valhalla Freight Administrator",
            password_hash=hash_password(settings.default_admin_password),
            role="admin",
            active=True,
        ))
        db.commit()

    if db.query(Customer).count():
        seed_customer_360(db)
        seed_platform_expansion(db)
        return

    customers = [
        Customer(code="ACM-001", name="Acme Industrial", industry="Manufacturing", billing_email="ap@acme.example", default_markup_pct=Decimal("15")),
        Customer(code="BLU-002", name="Blue River Foods", industry="Food & Beverage", billing_email="billing@blueriver.example", default_markup_pct=Decimal("12")),
        Customer(code="NVS-003", name="Nova Supply Co.", industry="Distribution", billing_email="finance@nova.example", default_markup_pct=Decimal("18")),
    ]
    carriers = [
        Carrier(scac="EXLA", name="Estes Express Lines", api_enabled=True, on_time_pct=Decimal("96.2"), claims_pct=Decimal("0.45")),
        Carrier(scac="ODFL", name="Old Dominion Freight Line", api_enabled=True, on_time_pct=Decimal("97.8"), claims_pct=Decimal("0.31")),
        Carrier(scac="SAIA", name="Saia LTL Freight", api_enabled=True, on_time_pct=Decimal("95.9"), claims_pct=Decimal("0.52")),
        Carrier(scac="FXFE", name="FedEx Freight", api_enabled=False, on_time_pct=Decimal("94.8"), claims_pct=Decimal("0.60")),
    ]
    db.add_all(customers + carriers)
    db.flush()
    db.add(PricingRule(name="Acme strategic pricing", priority=10, customer_id=customers[0].id, rule_type="markup_pct", value=Decimal("13"), minimum_margin=Decimal("45")))
    db.commit()
    seed_customer_360(db)
    seed_platform_expansion(db)


def seed_customer_360(db: Session):
    from app.domains.customers.models import CustomerProfile, CustomerLocation, CustomerContact, CustomerActivity
    samples = [
        ("ACM-001", {"legal_name":"Acme Industrial Manufacturing, Inc.","website":"https://acme.example","phone":"816-555-0148","account_manager":"Valhalla Operations","sales_owner":"House Account","payment_terms":"Net 30","billing_address":{"address1":"4100 Front Street","city":"Kansas City","state":"MO","postal_code":"64120","country":"USA"}},
         [("Kansas City Plant","plant","4100 Front Street","Kansas City","MO","64120",False),("Chicago DC","distribution","8150 Logistics Drive","Joliet","IL","60431",True)],
         [("Jordan","Miller","Logistics Manager","jordan.miller@acme.example","operations",True),("Avery","Cole","Accounts Payable","ap@acme.example","billing",False)]),
        ("BLU-002", {"legal_name":"Blue River Foods, LLC","website":"https://blueriver.example","phone":"913-555-0122","account_manager":"Valhalla Operations","sales_owner":"House Account","payment_terms":"Net 30","billing_address":{"address1":"1720 Harvest Way","city":"Olathe","state":"KS","postal_code":"66061","country":"USA"}},
         [("Olathe Distribution Center","distribution","1720 Harvest Way","Olathe","KS","66061",True)],
         [("Morgan","Reed","Transportation Manager","morgan.reed@blueriver.example","operations",True)]),
        ("NVS-003", {"legal_name":"Nova Supply Company","website":"https://nova.example","phone":"402-555-0199","account_manager":"Valhalla Operations","sales_owner":"House Account","payment_terms":"Net 45","billing_address":{"address1":"220 Commerce Park","city":"Omaha","state":"NE","postal_code":"68102","country":"USA"}},
         [("Omaha Warehouse","warehouse","220 Commerce Park","Omaha","NE","68102",False)],
         [("Taylor","Brooks","Supply Chain Director","taylor.brooks@nova.example","executive",True)])
    ]
    for code, profile_data, locations, contacts in samples:
        customer=db.query(Customer).filter(Customer.code==code).first()
        if not customer: continue
        if not db.query(CustomerProfile).filter(CustomerProfile.customer_id==customer.id).first():
            db.add(CustomerProfile(customer_id=customer.id, **profile_data))
        if db.query(CustomerLocation).filter(CustomerLocation.customer_id==customer.id).count()==0:
            for name,ltype,address1,city,state,postal,appt in locations:
                db.add(CustomerLocation(customer_id=customer.id,name=name,location_type=ltype,address1=address1,city=city,state=state,postal_code=postal,appointment_required=appt,dock_hours="07:00 - 16:00"))
        if db.query(CustomerContact).filter(CustomerContact.customer_id==customer.id).count()==0:
            for first,last,title,email,role,primary in contacts:
                db.add(CustomerContact(customer_id=customer.id,first_name=first,last_name=last,title=title,email=email,role=role,primary=primary,billing_contact=(role=="billing"),quote_contact=(role=="operations")))
        if db.query(CustomerActivity).filter(CustomerActivity.customer_id==customer.id).count()==0:
            db.add(CustomerActivity(customer_id=customer.id,activity_type="system",subject="Customer 360 profile initialized",body="Account profile, locations and contacts are ready for operational use.",created_by="Valhalla Freight"))
    db.commit()

# --- v0.6 platform expansion seed data ---
def seed_platform_expansion(db: Session):
    from datetime import date, timedelta
    from app.models import (CarrierProfile,CarrierContact,CarrierTerminal,CarrierCompliance,CarrierServiceCapability,CarrierServiceArea,CarrierLane,CarrierContract,CarrierDocument,CarrierActivity,IntegrationConnection,CapacityLoad,CapacityOffer,CarrierBill,Claim,Shipment,Carrier)
    dayton=db.query(Carrier).filter(Carrier.scac=='DAFG').first()
    if not dayton:
        dayton=Carrier(scac='DAFG',name='Dayton Freight Lines',api_enabled=True,on_time_pct=Decimal('0'),claims_pct=Decimal('0'))
        db.add(dayton); db.flush()
    carriers=db.query(Carrier).all()
    for i,c in enumerate(carriers):
        profile=db.query(CarrierProfile).filter(CarrierProfile.carrier_id==c.id).first()
        if not profile:
            profile=CarrierProfile(carrier_id=c.id,mc_number=f"MC{120000+i}",dot_number=f"DOT{2500000+i}",authority_status='active',payment_terms='Net 30',cargo_limit=Decimal('100000'),auto_liability_limit=Decimal('1000000'),insurance_expires_at=date.today()+timedelta(days=180+i*15),preferred=(c.scac in {'EXLA','ODFL'}))
            db.add(profile)
        # Enrich legacy carrier profiles without overwriting real user-entered values.
        if not profile.legal_name: profile.legal_name=c.name
        if not profile.website: profile.website='https://www.daytonfreight.com' if c.scac=='DAFG' else f"https://{c.scac.lower()}.example"
        if not profile.main_phone: profile.main_phone='800-860-5102' if c.scac=='DAFG' else '800-555-0100'
        if not profile.dispatch_email: profile.dispatch_email='apihelp@daytonfreight.com' if c.scac=='DAFG' else f"dispatch@{c.scac.lower()}.example"
        if not profile.billing_email: profile.billing_email=f"billing@{c.scac.lower()}.example"
        if not profile.address1: profile.address1='1000 Carrier Way'
        if not profile.city: profile.city='Kansas City'
        if not profile.state: profile.state='MO'
        if not profile.postal_code: profile.postal_code='64120'
        if not profile.country: profile.country='USA'
        if not profile.onboarding_status: profile.onboarding_status='approved'
        if not profile.safety_rating: profile.safety_rating='satisfactory'
        if profile.preferred and profile.preferred_rank is None: profile.preferred_rank=1 if c.scac=='ODFL' else 2
        if db.query(CarrierContact).filter(CarrierContact.carrier_id==c.id).count()==0:
            db.add(CarrierContact(carrier_id=c.id,name=f"{c.name} Operations",role='Operations',email=f"ops@{c.scac.lower()}.example",phone='800-555-0100',primary=True))
        if db.query(CarrierTerminal).filter(CarrierTerminal.carrier_id==c.id).count()==0:
            db.add(CarrierTerminal(carrier_id=c.id,name='Kansas City Service Center',city='Kansas City',state='MO',postal_code='64120',phone='816-555-0100'))
            db.add(CarrierTerminal(carrier_id=c.id,name='Chicago Service Center',city='Joliet',state='IL',postal_code='60431',phone='815-555-0100'))
        if db.query(CarrierCompliance).filter(CarrierCompliance.carrier_id==c.id).count()==0:
            for item in ['Operating Authority','Cargo Insurance','Auto Liability','W-9','Carrier Agreement']:
                db.add(CarrierCompliance(carrier_id=c.id,item_type=item,status='valid',expires_at=(date.today()+timedelta(days=180)) if 'Insurance' in item or 'Liability' in item else None))
        if db.query(CarrierServiceCapability).filter(CarrierServiceCapability.carrier_id==c.id).count()==0:
            db.add(CarrierServiceCapability(carrier_id=c.id,mode='LTL',service_level='Standard LTL',equipment='Dry / Palletized',active=True))
            db.add(CarrierServiceCapability(carrier_id=c.id,mode='Volume LTL',service_level='Volume / Spot',equipment='Dry',active=True))
        if db.query(CarrierServiceArea).filter(CarrierServiceArea.carrier_id==c.id).count()==0:
            for state in ['KS','MO','IL','TX','OK','NE']:
                db.add(CarrierServiceArea(carrier_id=c.id,area_type='state',value=state,description='Core service territory',active=True))
        if db.query(CarrierLane).filter(CarrierLane.carrier_id==c.id).count()==0:
            lane_samples=[('Kansas City, MO','Chicago, IL',Decimal('735')+Decimal(i*20),2),('Kansas City, MO','Dallas, TX',Decimal('805')+Decimal(i*25),2),('Chicago, IL','Atlanta, GA',Decimal('910')+Decimal(i*30),3)]
            for origin,dest,cost,days in lane_samples:
                db.add(CarrierLane(carrier_id=c.id,origin_region=origin,destination_region=dest,mode='LTL',service_level='Standard LTL',target_cost=cost,avg_transit_days=days,active=True,notes='Strategic development lane'))
        if db.query(CarrierContract).filter(CarrierContract.carrier_id==c.id).count()==0:
            db.add(CarrierContract(carrier_id=c.id,name=f'{c.name} Transportation Agreement',contract_type='Transportation Agreement',reference_number=f'VF-{c.scac}-MASTER',effective_date=date.today()-timedelta(days=90),expiration_date=date.today()+timedelta(days=275),status='active',notes='Master carrier agreement on file.'))
        if db.query(CarrierDocument).filter(CarrierDocument.carrier_id==c.id).count()==0:
            db.add(CarrierDocument(carrier_id=c.id,document_type='W-9',name=f'{c.scac} W-9',status='current'))
            db.add(CarrierDocument(carrier_id=c.id,document_type='Certificate of Insurance',name=f'{c.scac} COI',expires_at=date.today()+timedelta(days=180),status='current'))
        if db.query(CarrierActivity).filter(CarrierActivity.carrier_id==c.id).count()==0:
            db.add(CarrierActivity(carrier_id=c.id,activity_type='system',subject='Carrier 360 initialized',body='Compliance, service capabilities, strategic lanes, contract and document records initialized.',created_by='Valhalla Freight'))
    providers={
      'Carrier Connectivity':['CarrierDetails','Shipify','PC*Miler'],
      'Rate Intelligence':['Truckstop','DAT','FreightWaves SONAR','Cargo Chief','Triumph'],
      'Loadboards':['Truckstop','123Loadboard','DAT','dexFreight','LoadBoard Network','Motive'],
      'DFM Capacity':['Parade','Cargo Chief','DAT','Truckstop','Newtrul','Trucker Tools','MacroPoint','Motive'],
      'Shipment Visibility':['Trucker Tools','MacroPoint','FourKites','PC*Miler','project44','OpenTrack'],
      'Carrier Onboarding':['Truckstop','DAT','SaferWatch','RMIS','MyCarrierPortal','Highway'],
      'Accounting':['QuickBooks','MyCarrierPortal','Synergize','Microsoft Dynamics GP','Triumph','Authorize.Net'],
      'Factoring & Payments':['Triumph','Denim','RoadSync','Global Payments','CardConnect','Epay Manager','HaulPay','Relay','Authorize.Net'],
      'Claims & Insurance':['MyEZClaim.com','freightclaims.com','Global Logistics Solutions'],
      'Email & CRM':['Salesforce','Front'],
    }
    for category,names in providers.items():
        for name in names:
            if db.query(IntegrationConnection).filter(IntegrationConnection.provider==name, IntegrationConnection.category==category).first():
                continue
            caps=[]
            if category=='Shipment Visibility': caps=['tracking','eta','exceptions']
            elif category=='Loadboards': caps=['post_load','search_capacity']
            elif category=='Carrier Onboarding': caps=['compliance','insurance','authority']
            elif category=='Accounting': caps=['ar','ap','invoice_sync']
            elif category=='Factoring & Payments': caps=['payments','settlements']
            elif category=='Rate Intelligence': caps=['market_rates','benchmarking']
            elif category=='Carrier Connectivity': caps=['rating','dispatch','tracking']
            db.add(IntegrationConnection(provider=name,category=category,status='available',environment='sandbox',capabilities=caps))
    existing_dayton=db.query(IntegrationConnection).filter(IntegrationConnection.provider=='Dayton Freight').first()
    if not existing_dayton:
        db.add(IntegrationConnection(provider='Dayton Freight',category='Carrier Connectivity',status='available',environment='sandbox',capabilities=['rating','pickup','tracking','bol','documents','service'],settings={'scac':'DAFG','auth_type':'basic'}))
    db.commit()
