from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import String, Integer, Numeric, DateTime, Date, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class CarrierProfile(Base):
    __tablename__ = 'carrier_profiles'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), unique=True, index=True)
    mc_number: Mapped[str | None] = mapped_column(String(30))
    dot_number: Mapped[str | None] = mapped_column(String(30))
    authority_status: Mapped[str] = mapped_column(String(30), default='active')
    payment_terms: Mapped[str] = mapped_column(String(30), default='Net 30')
    factoring_company: Mapped[str | None] = mapped_column(String(120))
    cargo_limit: Mapped[Decimal] = mapped_column(Numeric(14,2), default=Decimal('100000'))
    auto_liability_limit: Mapped[Decimal] = mapped_column(Numeric(14,2), default=Decimal('1000000'))
    insurance_expires_at: Mapped[date | None] = mapped_column(Date)
    preferred: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[str | None] = mapped_column(Text)

class CarrierContact(Base):
    __tablename__ = 'carrier_contacts'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), index=True)
    name: Mapped[str] = mapped_column(String(120))
    role: Mapped[str] = mapped_column(String(60), default='Operations')
    email: Mapped[str | None] = mapped_column(String(180))
    phone: Mapped[str | None] = mapped_column(String(50))
    primary: Mapped[bool] = mapped_column(Boolean, default=False)

class CarrierTerminal(Base):
    __tablename__ = 'carrier_terminals'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), index=True)
    name: Mapped[str] = mapped_column(String(140))
    city: Mapped[str] = mapped_column(String(100))
    state: Mapped[str] = mapped_column(String(30))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    phone: Mapped[str | None] = mapped_column(String(50))

class CarrierCompliance(Base):
    __tablename__ = 'carrier_compliance'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), index=True)
    item_type: Mapped[str] = mapped_column(String(60))
    status: Mapped[str] = mapped_column(String(30), default='valid')
    expires_at: Mapped[date | None] = mapped_column(Date)
    document_url: Mapped[str | None] = mapped_column(String(500))
    verified_at: Mapped[datetime | None] = mapped_column(DateTime)

class CapacityLoad(Base):
    __tablename__ = 'capacity_loads'
    id: Mapped[int] = mapped_column(primary_key=True)
    shipment_id: Mapped[int | None] = mapped_column(ForeignKey('shipments.id'), index=True)
    mode: Mapped[str] = mapped_column(String(30), default='FTL')
    equipment: Mapped[str] = mapped_column(String(60), default='Dry Van')
    origin: Mapped[dict] = mapped_column(JSON)
    destination: Mapped[dict] = mapped_column(JSON)
    pickup_at: Mapped[datetime | None] = mapped_column(DateTime)
    delivery_at: Mapped[datetime | None] = mapped_column(DateTime)
    customer_revenue: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal('0'))
    target_buy: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal('0'))
    market_rate: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal('0'))
    status: Mapped[str] = mapped_column(String(30), default='open')
    posted_to: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CapacityOffer(Base):
    __tablename__ = 'capacity_offers'
    id: Mapped[int] = mapped_column(primary_key=True)
    load_id: Mapped[int] = mapped_column(ForeignKey('capacity_loads.id'), index=True)
    carrier_id: Mapped[int | None] = mapped_column(ForeignKey('carriers.id'))
    carrier_name: Mapped[str] = mapped_column(String(180))
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2))
    source: Mapped[str] = mapped_column(String(60), default='Private Network')
    status: Mapped[str] = mapped_column(String(30), default='offered')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Claim(Base):
    __tablename__ = 'claims'
    id: Mapped[int] = mapped_column(primary_key=True)
    claim_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey('shipments.id'), index=True)
    claim_type: Mapped[str] = mapped_column(String(40), default='damage')
    amount: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal('0'))
    status: Mapped[str] = mapped_column(String(30), default='open')
    description: Mapped[str | None] = mapped_column(Text)
    filed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime)

class CarrierBill(Base):
    __tablename__ = 'carrier_bills'
    id: Mapped[int] = mapped_column(primary_key=True)
    bill_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    shipment_id: Mapped[int] = mapped_column(ForeignKey('shipments.id'), index=True)
    carrier_id: Mapped[int | None] = mapped_column(ForeignKey('carriers.id'))
    quoted_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal('0'))
    invoice_cost: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal('0'))
    variance: Mapped[Decimal] = mapped_column(Numeric(12,2), default=Decimal('0'))
    status: Mapped[str] = mapped_column(String(30), default='pending_review')
    charge_breakdown: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class IntegrationConnection(Base):
    __tablename__ = 'integration_connections'
    id: Mapped[int] = mapped_column(primary_key=True)
    provider: Mapped[str] = mapped_column(String(100), index=True)
    category: Mapped[str] = mapped_column(String(60), index=True)
    status: Mapped[str] = mapped_column(String(30), default='available')
    environment: Mapped[str] = mapped_column(String(30), default='sandbox')
    capabilities: Mapped[list] = mapped_column(JSON, default=list)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime)
    last_error: Mapped[str | None] = mapped_column(Text)
    settings: Mapped[dict] = mapped_column(JSON, default=dict)

class AuditEvent(Base):
    __tablename__ = 'audit_events'
    id: Mapped[int] = mapped_column(primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(60), index=True)
    entity_id: Mapped[str] = mapped_column(String(60), index=True)
    action: Mapped[str] = mapped_column(String(80))
    actor: Mapped[str] = mapped_column(String(180), default='system')
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
