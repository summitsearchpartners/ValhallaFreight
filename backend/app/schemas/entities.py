from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel
from app.schemas.common import ORMModel, Address, HandlingUnit

class CustomerCreate(BaseModel):
    code: str
    name: str
    industry: str | None = None
    billing_email: str | None = None
    default_markup_pct: Decimal = Decimal("15")

class CustomerOut(ORMModel):
    id: int; code: str; name: str; status: str; industry: str | None = None
    billing_email: str | None = None; default_markup_pct: Decimal; credit_limit: Decimal

class CarrierOut(ORMModel):
    id: int; scac: str; name: str; mode: str; active: bool; api_enabled: bool
    on_time_pct: Decimal; claims_pct: Decimal

class PricingRuleCreate(BaseModel):
    name: str; priority: int = 100; customer_id: int | None = None; carrier_id: int | None = None
    origin_zip_prefix: str | None = None; destination_zip_prefix: str | None = None
    min_weight: int | None = None; max_weight: int | None = None; freight_class: str | None = None
    rule_type: str = "markup_pct"; value: Decimal = Decimal("15"); minimum_margin: Decimal = Decimal("0")

class PricingRuleOut(PricingRuleCreate, ORMModel):
    id: int; active: bool

class QuoteRequest(BaseModel):
    customer_id: int
    origin: Address
    destination: Address
    handling_units: list[HandlingUnit]
    accessorials: list[str] = []

class RateOption(BaseModel):
    carrier_id: int
    carrier_name: str
    scac: str
    service: str
    transit_days: int
    base_charge: Decimal
    fuel: Decimal
    accessorials: Decimal
    carrier_cost: Decimal
    customer_price: Decimal
    gross_profit: Decimal
    margin_pct: Decimal

class QuoteResponse(BaseModel):
    quote_number: str
    options: list[RateOption]
    expires_at: datetime


class DirectShipmentCreate(QuoteRequest):
    carrier_id: int
    pickup_date: date | None = None

class ShipmentCreate(BaseModel):
    quote_number: str
    carrier_id: int
    option_index: int = 0
    pickup_date: date | None = None

class ShipmentOut(ORMModel):
    id: int; shipment_number: str; customer_id: int; carrier_id: int | None; quote_id: int | None
    status: str; pro_number: str | None; bol_number: str | None
    origin: dict; destination: dict; handling_units: list; accessorials: list
    carrier_cost: Decimal; customer_charge: Decimal; final_carrier_cost: Decimal | None
    pickup_date: date | None; estimated_delivery: date | None; delivered_at: datetime | None; created_at: datetime

class TrackingEventCreate(BaseModel):
    code: str; status: str; description: str | None = None; location: str | None = None
    event_time: datetime; source: str = "manual"

class DashboardSummary(BaseModel):
    open_quotes: int; active_shipments: int; delivered_month: int; revenue_month: Decimal
    carrier_cost_month: Decimal; gross_profit_month: Decimal; avg_margin_pct: Decimal
