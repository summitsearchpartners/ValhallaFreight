from decimal import Decimal
from sqlalchemy.orm import Session
from app.models import Customer, Carrier, PricingRule, Shipment

def seed(db: Session):
    if db.query(Customer).count(): return
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
    db.add_all(customers + carriers); db.flush()
    db.add(PricingRule(name="Acme strategic pricing", priority=10, customer_id=customers[0].id, rule_type="markup_pct", value=Decimal("13"), minimum_margin=Decimal("45")))
    db.commit()
