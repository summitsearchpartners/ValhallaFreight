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
