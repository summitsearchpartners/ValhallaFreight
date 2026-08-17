from datetime import date, datetime
from decimal import Decimal
from pydantic import BaseModel

class DashboardSummary(BaseModel):
    active_shipments: int
    active_shipments_previous: int
    active_shipments_delta_pct: Decimal | None = None
    revenue_month: Decimal
    revenue_previous_month: Decimal
    revenue_delta_pct: Decimal | None = None
    gross_profit_month: Decimal
    gross_profit_previous_month: Decimal
    gross_profit_delta_pct: Decimal | None = None
    carrier_cost_month: Decimal
    avg_margin_pct: Decimal
    delivered_on_time_pct: Decimal | None = None
    delivered_on_time_previous_pct: Decimal | None = None
    delivered_on_time_delta_points: Decimal | None = None
    delivered_qualifying_shipments: int
    open_quotes: int

class PerformancePoint(BaseModel):
    period_start: date
    label: str
    revenue: Decimal
    gross_profit: Decimal
    carrier_cost: Decimal
    shipments: int

class PerformanceResponse(BaseModel):
    start_date: date
    end_date: date
    bucket: str
    points: list[PerformancePoint]

class RecentShipment(BaseModel):
    id: int
    shipment_number: str
    customer_name: str
    customer_id: int
    carrier_name: str | None = None
    carrier_scac: str | None = None
    origin: dict
    destination: dict
    customer_charge: Decimal
    status: str
    pro_number: str | None = None
    created_at: datetime

class MarginException(BaseModel):
    shipment_id: int
    shipment_number: str
    customer_name: str
    carrier_name: str | None = None
    expected_carrier_cost: Decimal
    final_carrier_cost: Decimal
    variance: Decimal
    expected_gp: Decimal
    final_gp: Decimal
    gp_impact: Decimal

class SavingsOpportunity(BaseModel):
    quote_id: int
    quote_number: str
    customer_name: str
    lowest_customer_price: Decimal
    highest_customer_price: Decimal
    savings_amount: Decimal
    savings_pct: Decimal
    created_at: datetime

class IntelligenceSummary(BaseModel):
    margin_exception_count: int
    protected_gp: Decimal
    margin_exceptions: list[MarginException]
    avg_opportunity_savings_pct: Decimal
    opportunity_count: int
    savings_opportunities: list[SavingsOpportunity]
