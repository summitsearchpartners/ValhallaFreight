from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from sqlalchemy import or_
from sqlalchemy.orm import Session
from app.models import Carrier, Customer, PricingRule, IntegrationConnection, CarrierRateControl
from app.db.tenant_scope import broker_workspace, tenant
from app.schemas.entities import QuoteRequest, RateOption
from app.integrations.carriers.dayton import DaytonAdapter
from app.integrations.carriers.dayton.rating import get_rate as get_dayton_rate
from app.integrations.carriers.dayton.client import DaytonClient
from app.integrations.base.exceptions import CarrierIntegrationError

TWOPLACES = Decimal("0.01")

def _dayton_terms(value: str | None) -> str:
    return {
        'Prepaid':'Prepaid',
        'Collect':'Collect',
        'Third Party':'ThirdPartyPrepaid',
        'Third Party Prepaid':'ThirdPartyPrepaid',
        'Third Party Collect':'ThirdPartyCollect',
    }.get(value or 'Prepaid','Prepaid')

def money(v): return Decimal(v).quantize(TWOPLACES, rounding=ROUND_HALF_UP)

def _region_matches(value: str | None, address) -> bool:
    if not value or value.strip() in {"", "*", "All", "ALL"}: return True
    wanted=value.strip().lower()
    candidates=[str(getattr(address,k,None) or '').strip().lower() for k in ('city','state','postal_code')]
    # A region can be a city, state, ZIP, or ZIP prefix. This keeps Carrier 360 lane controls useful
    # without requiring a separate geographic master table.
    return any(c == wanted or (c and c.startswith(wanted)) for c in candidates)

def _rate_policy(db: Session, carrier_id: int, request) -> dict:
    now=datetime.utcnow()
    rows=db.query(CarrierRateControl).filter(CarrierRateControl.carrier_id==carrier_id, CarrierRateControl.active.is_(True)).all()
    applicable=[]
    for row in rows:
        if row.starts_at and row.starts_at > now: continue
        if row.ends_at and row.ends_at < now: continue
        if row.scope == 'lane':
            if not _region_matches(row.origin_region, request.origin): continue
            if not _region_matches(row.destination_region, request.destination): continue
        applicable.append(row)
    return {
        'hide_rates': any(x.hide_rates for x in applicable),
        'direct_only': any(x.direct_only for x in applicable),
        'controls': applicable,
    }

class RatingEngine:
    def __init__(self, db: Session): self.db = db

    def _rule_price(self, customer, carrier, request, carrier_cost: Decimal):
        # Quote Studio can apply an explicit one-quote pricing override without changing
        # the customer's saved pricing rules. Flat = dollars added to carrier cost;
        # Margin = target gross margin percentage of the customer sell rate.
        mode = (getattr(request, "quote_pricing_mode", None) or "").lower()
        raw = getattr(request, "quote_pricing_value", None)
        if raw is not None and mode in {"flat", "margin"}:
            value = Decimal(str(raw))
            if mode == "flat":
                return money(carrier_cost + max(value, Decimal("0")))
            if value >= 100:
                value = Decimal("99.99")
            if value < 0:
                value = Decimal("0")
            return money(carrier_cost / (Decimal("1") - value / Decimal("100")))
        total_weight = sum(u.weight_lbs * u.quantity for u in request.handling_units)
        rules = self.db.query(PricingRule).filter(PricingRule.active.is_(True)).order_by(PricingRule.priority.asc()).all()
        eligible_customers={customer.id}
        if broker_workspace(self.db):eligible_customers.add(tenant(self.db))
        for r in rules:
            if r.customer_id and r.customer_id not in eligible_customers: continue
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

    async def get_rates(self, request: QuoteRequest):
        from app.services.commercial_privacy import protect_pricing_request
        protect_pricing_request(self.db,request)
        customer = self.db.get(Customer, request.customer_id)
        if not customer: raise ValueError("Customer not found")
        company = customer.manufacturer_id or customer.id
        carriers = self.db.query(Carrier).filter(
            Carrier.active.is_(True), or_(Carrier.customer_id.is_(None), Carrier.customer_id == company, Carrier.customer_id == tenant(self.db) if broker_workspace(self.db) else Carrier.customer_id == company)
        ).all()
        total_weight = Decimal(str(sum(u.weight_lbs * u.quantity for u in request.handling_units)))
        pallet_count = sum(u.quantity for u in request.handling_units)
        accessorial_cost = Decimal(str(len(request.accessorials) * 38))
        options = []
        for idx, c in enumerate(carriers):
            policy = _rate_policy(self.db, c.id, request)
            # Carrier 360 controls are evaluated before a carrier is asked to quote. A carrier can be
            # hidden globally or only for a matching lane, with optional start/end dates.
            if policy['hide_rates']:
                continue
            # Dayton Freight becomes a real direct API rate automatically when credentials are configured.
            if c.scac == "DAFG" and DaytonAdapter(self.db).configured():
                try:
                    from app.integrations.service import get_dayton_connection
                    connection=get_dayton_connection(self.db)
                    cfg=(connection.settings or {}) if connection else {}
                    # Ask the live carrier for the lane quote and let its response identify whether the
                    # movement is Direct or Indirect. Carrier 360 then decides whether that returned
                    # service type is eligible to be shown. This avoids Valhalla guessing coverage.
                    live, _, _ = await get_dayton_rate(request, account=cfg.get("account"), direct_only=bool(cfg.get("direct_only",False)), terms=_dayton_terms(getattr(request,"payment_terms",None)), client=DaytonClient.from_db(self.db))
                    if policy['direct_only'] and (live.movement_type or '').lower() != 'direct':
                        continue
                    carrier_cost = money(live.carrier_cost)
                    price = self._rule_price(customer, c, request, carrier_cost)
                    gp = money(price - carrier_cost)
                    margin = money((gp / price * Decimal("100")) if price else 0)
                    options.append(RateOption(
                        carrier_id=c.id, carrier_name=c.name, scac=c.scac, service=live.service,
                        transit_days=live.transit_days or 1, base_charge=money(live.base_charge), fuel=money(live.fuel),
                        accessorials=money(live.accessorials), carrier_cost=carrier_cost, customer_price=price,
                        gross_profit=gp, margin_pct=margin, source="live_api", provider_quote_id=live.provider_quote_id,
                        movement_type=live.movement_type, warnings=live.warnings
                    ))
                    continue
                except (CarrierIntegrationError, ValueError):
                    # Preserve Quote Studio availability if Dayton is configured incorrectly; Integration Hub shows the error.
                    pass
            # A direct-only control is intentionally fail-closed. If no live carrier API can verify
            # that this lane is direct, Valhalla does not publish a simulated/unverified rate.
            if policy['direct_only']:
                continue
            base = Decimal("110") + total_weight * (Decimal("0.115") + Decimal(idx) * Decimal("0.008")) + Decimal(pallet_count * 18)
            fuel = base * Decimal("0.285")
            carrier_cost = money(base + fuel + accessorial_cost)
            price = self._rule_price(customer, c, request, carrier_cost)
            gp = money(price - carrier_cost)
            margin = money((gp / price * Decimal("100")) if price else 0)
            options.append(RateOption(carrier_id=c.id, carrier_name=c.name, scac=c.scac, service="Standard LTL",
                transit_days=2 + (idx % 4), base_charge=money(base), fuel=money(fuel), accessorials=money(accessorial_cost),
                carrier_cost=carrier_cost, customer_price=price, gross_profit=gp, margin_pct=margin, source="simulation"))
        return sorted(options, key=lambda x: x.customer_price)

