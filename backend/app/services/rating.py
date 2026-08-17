from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy.orm import Session
from app.models import Carrier, Customer, PricingRule
from app.schemas.entities import QuoteRequest, RateOption

TWOPLACES = Decimal("0.01")
def money(v): return Decimal(v).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

class RatingEngine:
    def __init__(self, db: Session): self.db = db

    def _rule_price(self, customer, carrier, request, carrier_cost: Decimal):
        total_weight = sum(u.weight_lbs * u.quantity for u in request.handling_units)
        rules = self.db.query(PricingRule).filter(PricingRule.active.is_(True)).order_by(PricingRule.priority.asc()).all()
        for r in rules:
            if r.customer_id and r.customer_id != customer.id: continue
            if r.carrier_id and r.carrier_id != carrier.id: continue
            if r.origin_zip_prefix and not request.origin.postal_code.startswith(r.origin_zip_prefix): continue
            if r.destination_zip_prefix and not request.destination.postal_code.startswith(r.destination_zip_prefix): continue
            if r.min_weight and total_weight < r.min_weight: continue
            if r.max_weight and total_weight > r.max_weight: continue
            if r.freight_class and not any(u.freight_class == r.freight_class for u in request.handling_units): continue
            if r.rule_type == "flat": price = carrier_cost + r.value
            else: price = carrier_cost * (Decimal("1") + r.value / Decimal("100"))
            price = max(price, carrier_cost + r.minimum_margin)
            return money(price)
        return money(carrier_cost * (Decimal("1") + customer.default_markup_pct / Decimal("100")))

    def get_rates(self, request: QuoteRequest):
        customer = self.db.get(Customer, request.customer_id)
        if not customer: raise ValueError("Customer not found")
        carriers = self.db.query(Carrier).filter(Carrier.active.is_(True)).all()
        total_weight = Decimal(str(sum(u.weight_lbs * u.quantity for u in request.handling_units)))
        pallet_count = sum(u.quantity for u in request.handling_units)
        accessorial_cost = Decimal(str(len(request.accessorials) * 38))
        options = []
        # Deterministic mock connector: replace this adapter with aggregator/direct carrier APIs.
        for idx, c in enumerate(carriers):
            base = Decimal("110") + total_weight * (Decimal("0.115") + Decimal(idx) * Decimal("0.008")) + Decimal(pallet_count * 18)
            fuel = base * Decimal("0.285")
            carrier_cost = money(base + fuel + accessorial_cost)
            price = self._rule_price(customer, c, request, carrier_cost)
            gp = money(price - carrier_cost)
            margin = money((gp / price * Decimal("100")) if price else 0)
            options.append(RateOption(carrier_id=c.id, carrier_name=c.name, scac=c.scac, service="Standard LTL",
                transit_days=2 + (idx % 4), base_charge=money(base), fuel=money(fuel), accessorials=money(accessorial_cost),
                carrier_cost=carrier_cost, customer_price=price, gross_profit=gp, margin_pct=margin))
        return sorted(options, key=lambda x: x.customer_price)
