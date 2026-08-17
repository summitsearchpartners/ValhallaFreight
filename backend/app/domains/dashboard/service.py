from collections import defaultdict
from calendar import month_abbr
from datetime import date, datetime, timedelta, time
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.models import Shipment, Quote, Customer, Carrier

ACTIVE_STATUSES = ["booked", "pickup_requested", "dispatched", "picked_up", "in_transit", "out_for_delivery"]
TERMINAL_STATUSES = ["delivered", "cancelled"]


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _pct_change(current: Decimal | int, previous: Decimal | int):
    current = Decimal(str(current or 0)); previous = Decimal(str(previous or 0))
    if previous == 0:
        return None if current == 0 else Decimal("100.0")
    return ((current - previous) / abs(previous) * Decimal("100")).quantize(Decimal("0.1"))


def _month_bounds(day: date):
    start = day.replace(day=1)
    if start.month == 12:
        next_start = date(start.year + 1, 1, 1)
    else:
        next_start = date(start.year, start.month + 1, 1)
    prev_end = start
    if start.month == 1:
        prev_start = date(start.year - 1, 12, 1)
    else:
        prev_start = date(start.year, start.month - 1, 1)
    return prev_start, prev_end, start, next_start


def _datetime_bounds(start: date, end_exclusive: date):
    return datetime.combine(start, time.min), datetime.combine(end_exclusive, time.min)


def _period_financials(db: Session, start: date, end_exclusive: date):
    start_dt, end_dt = _datetime_bounds(start, end_exclusive)
    rows = db.query(Shipment).filter(Shipment.created_at >= start_dt, Shipment.created_at < end_dt).all()
    revenue = sum((_money(s.customer_charge) for s in rows), Decimal("0"))
    carrier_cost = sum((_money(s.final_carrier_cost if s.final_carrier_cost is not None else s.carrier_cost) for s in rows), Decimal("0"))
    gp = revenue - carrier_cost
    margin = (gp / revenue * Decimal("100")) if revenue else Decimal("0")
    return {"rows": rows, "revenue": revenue, "carrier_cost": carrier_cost, "gp": gp, "margin": margin.quantize(Decimal("0.1"))}


def _on_time_for_period(db: Session, start: date, end_exclusive: date):
    start_dt, end_dt = _datetime_bounds(start, end_exclusive)
    rows = db.query(Shipment).filter(
        Shipment.delivered_at.is_not(None),
        Shipment.delivered_at >= start_dt,
        Shipment.delivered_at < end_dt,
    ).all()
    rows = [s for s in rows if s.requested_delivery_at is not None or s.estimated_delivery is not None]
    if not rows:
        return None, 0
    on_time = 0
    for s in rows:
        if s.requested_delivery_at is not None:
            if s.delivered_at <= s.requested_delivery_at:
                on_time += 1
        elif s.estimated_delivery is not None and s.delivered_at.date() <= s.estimated_delivery:
            on_time += 1
    return (Decimal(on_time) / Decimal(len(rows)) * Decimal("100")).quantize(Decimal("0.1")), len(rows)


def summary(db: Session):
    today = datetime.utcnow().date()
    prev_start, prev_end, month_start, next_month = _month_bounds(today)
    current = _period_financials(db, month_start, next_month)
    previous = _period_financials(db, prev_start, prev_end)

    active = db.query(func.count(Shipment.id)).filter(~Shipment.status.in_(TERMINAL_STATUSES)).scalar() or 0
    # We intentionally do not fabricate a historical active-shipment comparison.
    # Accurate prior-period active counts require status-history snapshots, which are not stored yet.
    prev_active = 0

    current_otp, current_qualifying = _on_time_for_period(db, month_start, next_month)
    prev_otp, _ = _on_time_for_period(db, prev_start, prev_end)
    otp_delta = None
    if current_otp is not None and prev_otp is not None:
        otp_delta = (current_otp - prev_otp).quantize(Decimal("0.1"))

    open_quotes = db.query(func.count(Quote.id)).filter(Quote.status == "open").scalar() or 0
    return {
        "active_shipments": active,
        "active_shipments_previous": prev_active,
        "active_shipments_delta_pct": None,
        "revenue_month": current["revenue"],
        "revenue_previous_month": previous["revenue"],
        "revenue_delta_pct": _pct_change(current["revenue"], previous["revenue"]),
        "gross_profit_month": current["gp"],
        "gross_profit_previous_month": previous["gp"],
        "gross_profit_delta_pct": _pct_change(current["gp"], previous["gp"]),
        "carrier_cost_month": current["carrier_cost"],
        "avg_margin_pct": current["margin"],
        "delivered_on_time_pct": current_otp,
        "delivered_on_time_previous_pct": prev_otp,
        "delivered_on_time_delta_points": otp_delta,
        "delivered_qualifying_shipments": current_qualifying,
        "open_quotes": open_quotes,
    }


def _bucket_for_range(start: date, end: date):
    days = (end - start).days + 1
    if days <= 45:
        return "day"
    if days <= 190:
        return "week"
    return "month"


def _bucket_start(day: date, bucket: str):
    if bucket == "day": return day
    if bucket == "week": return day - timedelta(days=day.weekday())
    return day.replace(day=1)


def _next_bucket(day: date, bucket: str):
    if bucket == "day": return day + timedelta(days=1)
    if bucket == "week": return day + timedelta(days=7)
    if day.month == 12: return date(day.year + 1, 1, 1)
    return date(day.year, day.month + 1, 1)


def _label(day: date, bucket: str):
    if bucket == "day": return day.strftime("%b %-d") if hasattr(day, 'strftime') else str(day)
    if bucket == "week": return f"Wk of {month_abbr[day.month]} {day.day}"
    return f"{month_abbr[day.month]} {str(day.year)[2:]}"


def performance(db: Session, start: date, end: date):
    if end < start:
        start, end = end, start
    bucket = _bucket_for_range(start, end)
    start_dt = datetime.combine(start, time.min)
    end_dt = datetime.combine(end + timedelta(days=1), time.min)
    rows = db.query(Shipment).filter(Shipment.created_at >= start_dt, Shipment.created_at < end_dt).all()
    grouped = defaultdict(lambda: {"revenue": Decimal("0"), "carrier_cost": Decimal("0"), "shipments": 0})
    for s in rows:
        key = _bucket_start(s.created_at.date(), bucket)
        grouped[key]["revenue"] += _money(s.customer_charge)
        grouped[key]["carrier_cost"] += _money(s.final_carrier_cost if s.final_carrier_cost is not None else s.carrier_cost)
        grouped[key]["shipments"] += 1
    points=[]
    cursor=_bucket_start(start,bucket)
    last=_bucket_start(end,bucket)
    while cursor <= last:
        data=grouped[cursor]
        revenue=data["revenue"]
        carrier_cost=data["carrier_cost"]
        points.append({
            "period_start":cursor,
            "label": _label(cursor,bucket),
            "revenue":revenue,
            "gross_profit":revenue-carrier_cost,
            "carrier_cost":carrier_cost,
            "shipments":data["shipments"],
        })
        cursor=_next_bucket(cursor,bucket)
    return {"start_date":start,"end_date":end,"bucket":bucket,"points":points}


def recent_shipments(db: Session, limit: int = 8):
    rows = db.query(Shipment, Customer, Carrier).join(Customer, Shipment.customer_id == Customer.id).outerjoin(Carrier, Shipment.carrier_id == Carrier.id).order_by(Shipment.created_at.desc()).limit(limit).all()
    return [{
        "id":s.id,
        "shipment_number":s.shipment_number,
        "customer_name":c.name,
        "customer_id":c.id,
        "carrier_name":carrier.name if carrier else None,
        "carrier_scac":carrier.scac if carrier else None,
        "origin":s.origin,
        "destination":s.destination,
        "customer_charge":_money(s.customer_charge),
        "status":s.status,
        "pro_number":s.pro_number,
        "created_at":s.created_at,
    } for s,c,carrier in rows]


def intelligence(db: Session, exception_threshold: Decimal = Decimal("75"), limit: int = 20):
    rows = db.query(Shipment, Customer, Carrier).join(Customer, Shipment.customer_id == Customer.id).outerjoin(Carrier, Shipment.carrier_id == Carrier.id).filter(Shipment.final_carrier_cost.is_not(None)).order_by(Shipment.created_at.desc()).all()
    exceptions=[]
    for s,c,carrier in rows:
        expected=_money(s.carrier_cost); final=_money(s.final_carrier_cost); variance=final-expected
        if variance <= exception_threshold: continue
        expected_gp=_money(s.customer_charge)-expected
        final_gp=_money(s.customer_charge)-final
        exceptions.append({
            "shipment_id":s.id,"shipment_number":s.shipment_number,"customer_name":c.name,
            "carrier_name":carrier.name if carrier else None,
            "expected_carrier_cost":expected,"final_carrier_cost":final,"variance":variance,
            "expected_gp":expected_gp,"final_gp":final_gp,"gp_impact":expected_gp-final_gp,
        })
    exceptions=exceptions[:limit]

    quote_rows=db.query(Quote,Customer).join(Customer,Quote.customer_id==Customer.id).order_by(Quote.created_at.desc()).limit(250).all()
    opportunities=[]
    for q,c in quote_rows:
        prices=[]
        for option in q.options or []:
            try: prices.append(_money(option.get("customer_price")))
            except Exception: pass
        if len(prices)<2: continue
        low=min(prices); high=max(prices)
        if high <= 0 or high == low: continue
        amount=high-low
        pct=(amount/high*Decimal("100")).quantize(Decimal("0.1"))
        opportunities.append({
            "quote_id":q.id,"quote_number":q.quote_number,"customer_name":c.name,
            "lowest_customer_price":low,"highest_customer_price":high,
            "savings_amount":amount,"savings_pct":pct,"created_at":q.created_at,
        })
    avg_pct=(sum((o["savings_pct"] for o in opportunities),Decimal("0"))/Decimal(len(opportunities))).quantize(Decimal("0.1")) if opportunities else Decimal("0")
    return {
        "margin_exception_count":len(exceptions),
        "protected_gp":sum((e["gp_impact"] for e in exceptions),Decimal("0")),
        "margin_exceptions":exceptions,
        "avg_opportunity_savings_pct":avg_pct,
        "opportunity_count":len(opportunities),
        "savings_opportunities":opportunities[:limit],
    }
