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
    legal_name: Mapped[str | None] = mapped_column(String(180))
    website: Mapped[str | None] = mapped_column(String(220))
    main_phone: Mapped[str | None] = mapped_column(String(50))
    dispatch_email: Mapped[str | None] = mapped_column(String(180))
    billing_email: Mapped[str | None] = mapped_column(String(180))
    address1: Mapped[str | None] = mapped_column(String(220))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(30))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country: Mapped[str] = mapped_column(String(60), default='USA')
    onboarding_status: Mapped[str] = mapped_column(String(40), default='approved')
    safety_rating: Mapped[str] = mapped_column(String(40), default='satisfactory')
    preferred_rank: Mapped[int | None] = mapped_column(Integer)
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
    document_name: Mapped[str | None] = mapped_column(String(255))
    document_content_type: Mapped[str | None] = mapped_column(String(120))
    document_size_bytes: Mapped[int | None] = mapped_column(Integer)
    document_uploaded_at: Mapped[datetime | None] = mapped_column(DateTime)


class CarrierComplianceDocumentVersion(Base):
    __tablename__ = 'carrier_compliance_document_versions'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), index=True)
    compliance_id: Mapped[int] = mapped_column(ForeignKey('carrier_compliance.id'), index=True)
    version_number: Mapped[int] = mapped_column(Integer, default=1)
    original_name: Mapped[str] = mapped_column(String(255))
    stored_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(120))
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[str] = mapped_column(String(180), default='Valhalla Freight')
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True)


class CarrierServiceCapability(Base):
    __tablename__ = 'carrier_service_capabilities'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), index=True)
    mode: Mapped[str] = mapped_column(String(40), default='LTL')
    service_level: Mapped[str] = mapped_column(String(80), default='Standard')
    equipment: Mapped[str | None] = mapped_column(String(80))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class CarrierServiceArea(Base):
    __tablename__ = 'carrier_service_areas'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), index=True)
    area_type: Mapped[str] = mapped_column(String(40), default='state')
    value: Mapped[str] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(240))
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class CarrierLane(Base):
    __tablename__ = 'carrier_lanes'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), index=True)
    origin_region: Mapped[str] = mapped_column(String(120))
    destination_region: Mapped[str] = mapped_column(String(120))
    mode: Mapped[str] = mapped_column(String(40), default='LTL')
    service_level: Mapped[str] = mapped_column(String(80), default='Standard')
    target_cost: Mapped[Decimal | None] = mapped_column(Numeric(12,2))
    avg_transit_days: Mapped[int | None] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    notes: Mapped[str | None] = mapped_column(Text)

class CarrierContract(Base):
    __tablename__ = 'carrier_contracts'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), index=True)
    name: Mapped[str] = mapped_column(String(180))
    contract_type: Mapped[str] = mapped_column(String(60), default='Transportation Agreement')
    reference_number: Mapped[str | None] = mapped_column(String(80))
    effective_date: Mapped[date | None] = mapped_column(Date)
    expiration_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default='active')
    document_url: Mapped[str | None] = mapped_column(String(500))
    notes: Mapped[str | None] = mapped_column(Text)

class CarrierDocument(Base):
    __tablename__ = 'carrier_documents'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), index=True)
    document_type: Mapped[str] = mapped_column(String(60), default='Other')
    name: Mapped[str] = mapped_column(String(180))
    file_url: Mapped[str | None] = mapped_column(String(500))
    expires_at: Mapped[date | None] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(30), default='current')
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class CarrierActivity(Base):
    __tablename__ = 'carrier_activities'
    id: Mapped[int] = mapped_column(primary_key=True)
    carrier_id: Mapped[int] = mapped_column(ForeignKey('carriers.id'), index=True)
    activity_type: Mapped[str] = mapped_column(String(40), default='note')
    subject: Mapped[str] = mapped_column(String(180))
    body: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str] = mapped_column(String(180), default='Valhalla Freight')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

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
