"""Muse quotes entered by Valhalla and customer onboarding."""
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Customer, MuseAccount, MuseQuoteRate, Quote, Carrier
from app.services import muse_enrollment as access

from app.schemas.muse import MuseAccountStatus, MusePreview, MusePreviewSelection, MuseRateInput, MuseRateOut


def _rate_out(row: MuseQuoteRate) -> MuseRateOut:
    return MuseRateOut(carrier_name=row.carrier_name, customer_price=row.customer_price, revision=row.revision, carrier_id=row.carrier_id,carrier_cost=row.carrier_cost,transit_days=row.transit_days)


def _active(quote: Quote) -> bool:
    return (
        quote.status != "booked"
        and (quote.expires_at is None or quote.expires_at > datetime.now(timezone.utc).replace(tzinfo=None))
        and bool(quote.handling_units)
        and all((address or {}).get("postal_code") for address in (quote.origin, quote.destination))
    )


def available_preview(quote: Quote, db: Session | None = None) -> MusePreview | None:
    if not _active(quote):
        return None
    if db is None:return None
    _,enrolled=access.enrollment(db,quote.customer_id)
    if not enrolled or not enrolled.enabled:return None
    rate = db.get(MuseQuoteRate, quote.id)
    return MusePreview(rate=_rate_out(rate) if rate else None)


def _locked_quote(db: Session, quote_id: int) -> Quote:
    statement = select(Quote).where(Quote.id == quote_id).with_for_update().execution_options(populate_existing=True)
    quote = db.execute(statement).scalar_one_or_none()
    if quote is None:
        raise HTTPException(404, "Quote not found")
    if not _active(quote):
        raise HTTPException(409, "Muse rates are available only on active, unbooked LTL quotes")
    return quote


def save_rate(db: Session, quote_id: int, payload: MuseRateInput | None) -> MusePreview:
    quote = _locked_quote(db, quote_id)
    access.require_enabled(db,quote.customer_id)
    row = db.get(MuseQuoteRate, quote_id)
    # Any edited or withdrawn offer invalidates its previous selection.
    quote.options=[dict(o,selected=False) if o.get("provider")=="muse_freight" else dict(o) for o in quote.options or []]
    if quote.status=="selected" and not any(o.get("selected") for o in quote.options):quote.status="open"
    if payload is None:
        if row is not None:
            db.delete(row)
        result = MusePreview()
    else:
        if row is None:
            row = MuseQuoteRate(quote_id=quote.id, customer_id=quote.customer_id)
            db.add(row)
        if payload.carrier_id is not None:
            carrier=db.get(Carrier,payload.carrier_id)
            company=access.manufacturer(db,quote.customer_id).id
            if not carrier or not carrier.active or carrier.customer_id not in (None,company):
                raise HTTPException(422,"Choose a carrier available to this manufacturer")
            row.carrier_name=carrier.name
        else:row.carrier_name = payload.carrier_name
        row.carrier_id=payload.carrier_id
        row.carrier_cost=payload.carrier_cost
        row.transit_days=payload.transit_days
        row.customer_price = payload.customer_price
        row.revision = str(uuid4())
        result = MusePreview(rate=_rate_out(row))
    db.commit()
    return result


def _customer(db: Session, customer_id: int, lock: bool = False) -> Customer:
    query = select(Customer).where(Customer.id == customer_id)
    if lock:
        # Serialize first-use recording and admin verification for this customer.
        query = query.with_for_update()
    customer = db.execute(query).scalar_one_or_none()
    if customer is None:
        raise HTTPException(404, "Customer not found")
    return customer


def account_status(db: Session, customer_id: int) -> MuseAccountStatus:
    state=access.status(db,customer_id)
    return MuseAccountStatus(account_verified=state["can_book"])


def _locked_account(db: Session, customer_id: int) -> MuseAccount:
    _customer(db, customer_id, lock=True)
    account = db.get(MuseAccount, customer_id)
    if account is None:
        account = MuseAccount(customer_id=customer_id, account_verified=False)
        db.add(account)
    return account


def set_account_status(db: Session, customer_id: int, verified: bool) -> MuseAccountStatus:
    raise HTTPException(409,"Muse approval now requires an application reviewed in the Muse Portal")


def select_rate(db: Session, quote_id: int, revision: str) -> MusePreviewSelection:
    quote = _locked_quote(db, quote_id)
    rate = db.get(MuseQuoteRate, quote.id)
    if rate is None or rate.revision != revision:
        raise HTTPException(409, "This Muse price has changed or is unavailable. Refresh Muse rate and try again.")
    selected_rate = _rate_out(rate)
    root,enrolled=access.require_enabled(db,quote.customer_id,lock=True)
    account = _locked_account(db, root.id)
    first_selection = account.first_preview_at is None
    verified = enrolled.status=="approved"
    if first_selection:
        account.first_preview_at = datetime.now(timezone.utc).replace(tzinfo=None)
    selected=False
    if verified:
        if rate.carrier_id is None or rate.carrier_cost is None or rate.transit_days is None:
            raise HTTPException(409,"Muse needs to finish the carrier, cost and transit details for this offer before booking")
        carrier=db.get(Carrier,rate.carrier_id)
        if not carrier or not carrier.active or carrier.customer_id not in (None,root.id):raise HTTPException(409,"This Muse carrier is no longer available")
        cost=rate.carrier_cost;price=rate.customer_price
        option={
            "carrier_id":rate.carrier_id,"carrier_name":rate.carrier_name,"scac":carrier.scac,
            "provider":"muse_freight","muse_revision":rate.revision,"source":"muse_quote",
            "service":"LTL Freight","transit_days":rate.transit_days,"carrier_cost":str(cost),
            "customer_price":str(price),"base_charge":str(cost),"fuel":"0","accessorials":"0",
            "gross_profit":str(price-cost),"margin_pct":str(round((price-cost)/price*100,2)),
            "selected":True,"selected_at":access.now().isoformat(),
        }
        quote.options=[dict(o,selected=False) for o in quote.options or [] if o.get("provider")!="muse_freight"]+[option]
        quote.status="selected";selected=True
    db.commit()
    return MusePreviewSelection(
        selected=selected, manufacturer_id=root.id,application_status=enrolled.status,
        rate=selected_rate,
        first_selection=first_selection,
        account_verified=verified,
        show_onboarding=first_selection or not verified,
    )
