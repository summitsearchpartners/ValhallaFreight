from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, DateTime, Date, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    status: Mapped[str] = mapped_column(String(30), default="active")
    industry: Mapped[str | None] = mapped_column(String(100))
    billing_email: Mapped[str | None] = mapped_column(String(180))
    default_markup_pct: Mapped[Decimal] = mapped_column(Numeric(7,2), default=Decimal("15.00"))
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal("0"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    shipments = relationship("Shipment", back_populates="customer")

class Carrier(Base):
    __tablename__ = "carriers"
    id: Mapped[int] = mapped_column(primary_key=True)
    scac: Mapped[str] = mapped_column(String(10), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180))
    mode: Mapped[str] = mapped_column(String(30), default="LTL")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    api_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    on_time_pct: Mapped[Decimal] = mapped_column(Numeric(5,2), default=Decimal("0"))
    claims_pct: Mapped[Decimal] = mapped_column(Numeric(5,2), default=Decimal("0"))

class PricingRule(Base):
    __tablename__ = "pricing_rules"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(180))
    priority: Mapped[int] = mapped_column(Integer, default=100)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    customer_id: Mapped[int | None] = mapped_column(ForeignKey("customers.id"))
    carrier_id: Mapped[int | None] = mapped_column(ForeignKey("carriers.id"))
    origin_zip_prefix: Mapped[str | None] = mapped_column(String(10))
    destination_zip_prefix: Mapped[str | None] = mapped_column(String(10))
    min_weight: Mapped[int | None] = mapped_column(Integer)
    max_weight: Mapped[int | None] = mapped_column(Integer)
    freight_class: Mapped[str | None] = mapped_column(String(20))
    rule_type: Mapped[str] = mapped_column(String(30), default="markup_pct")
    value: Mapped[Decimal] = mapped_column(Numeric(10,2), default=Decimal("15"))
    minimum_margin: Mapped[Decimal] = mapped_column(Numeric(10,2), default=Decimal("0"))

class Quote(Base):
    __tablename__ = "quotes"
    id: Mapped[int] = mapped_column(primary_key=True)
    quote_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    status: Mapped[str] = mapped_column(String(30), default="open")
    origin: Mapped[dict] = mapped_column(JSON)
    destination: Mapped[dict] = mapped_column(JSON)
    handling_units: Mapped[list] = mapped_column(JSON)
    accessorials: Mapped[list] = mapped_column(JSON, default=list)
    options: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

class Shipment(Base):
    __tablename__ = "shipments"
    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_number: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    carrier_id: Mapped[int | None] = mapped_column(ForeignKey("carriers.id"))
    quote_id: Mapped[int | None] = mapped_column(ForeignKey("quotes.id"))
    status: Mapped[str] = mapped_column(String(40), default="booked", index=True)
    pro_number: Mapped[str | None] = mapped_column(String(60), index=True)
    bol_number: Mapped[str | None] = mapped_column(String(60))
    origin: Mapped[dict] = mapped_column(JSON)
    destination: Mapped[dict] = mapped_column(JSON)
    handling_units: Mapped[list] = mapped_column(JSON)
    accessorials: Mapped[list] = mapped_column(JSON, default=list)
    carrier_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal("0"))
    customer_charge: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal("0"))
    final_carrier_cost: Mapped[Decimal | None] = mapped_column(Numeric(12,2))
    pickup_date: Mapped[date | None] = mapped_column(Date)
    estimated_delivery: Mapped[date | None] = mapped_column(Date)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    customer = relationship("Customer", back_populates="shipments")
    carrier = relationship("Carrier")

class TrackingEvent(Base):
    __tablename__ = "tracking_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"), index=True)
    code: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(80))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(180))
    event_time: Mapped[datetime] = mapped_column(DateTime)
    source: Mapped[str] = mapped_column(String(40), default="manual")

class Invoice(Base):
    __tablename__ = "invoices"
    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_number: Mapped[str] = mapped_column(String(40), unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"))
    shipment_id: Mapped[int] = mapped_column(ForeignKey("shipments.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    status: Mapped[str] = mapped_column(String(30), default="draft")
    due_date: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(180))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(40), default="admin")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
