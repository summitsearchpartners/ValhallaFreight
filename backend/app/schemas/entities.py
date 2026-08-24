from datetime import datetime, date
from decimal import Decimal
from pydantic import BaseModel, model_validator
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
    requested_pickup_at: datetime | None = None
    requested_delivery_at: datetime | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.requested_pickup_at and self.requested_delivery_at and self.requested_delivery_at < self.requested_pickup_at:
            raise ValueError("Required delivery date/time must be after the requested pickup date/time")
        return self

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
    scheduled_pickup_at: datetime | None = None
    requested_delivery_at: datetime | None = None
    origin: Address | None = None
    destination: Address | None = None
    origin_location_id: int | None = None
    destination_location_id: int | None = None
    accessorials: list[str] | None = None

class ShipmentOut(ORMModel):
    id: int; shipment_number: str; customer_id: int; carrier_id: int | None; quote_id: int | None
    status: str; pro_number: str | None; bol_number: str | None
    po_number: str | None; customer_reference: str | None; package_count: int | None; package_type: str | None
    commodity_description: str | None; nmfc_number: str | None; hazmat_emergency_contact: str | None
    hazmat_emergency_phone: str | None; declared_value: Decimal | None
    origin: dict; destination: dict; handling_units: list; accessorials: list
    carrier_cost: Decimal; customer_charge: Decimal; final_carrier_cost: Decimal | None
    pickup_date: date | None; estimated_delivery: date | None
    scheduled_pickup_at: datetime | None; requested_delivery_at: datetime | None; actual_pickup_at: datetime | None
    delivered_at: datetime | None; created_at: datetime


class ShipmentUpdate(BaseModel):
    # BOL number is system-assigned when the shipment is created and is immutable.
    pro_number: str | None = None
    po_number: str | None = None
    customer_reference: str | None = None
    package_count: int | None = None
    package_type: str | None = None
    commodity_description: str | None = None
    nmfc_number: str | None = None
    hazmat_emergency_contact: str | None = None
    hazmat_emergency_phone: str | None = None
    declared_value: Decimal | None = None
    scheduled_pickup_at: datetime | None = None
    requested_delivery_at: datetime | None = None
    actual_pickup_at: datetime | None = None
    delivered_at: datetime | None = None
    status: str | None = None

class TrackingEventCreate(BaseModel):
    code: str; status: str; description: str | None = None; location: str | None = None
    event_time: datetime; source: str = "manual"

class DashboardSummary(BaseModel):
    open_quotes: int; active_shipments: int; delivered_month: int; revenue_month: Decimal
    carrier_cost_month: Decimal; gross_profit_month: Decimal; avg_margin_pct: Decimal
