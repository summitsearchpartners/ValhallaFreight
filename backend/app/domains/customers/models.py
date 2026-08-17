from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, Text, Boolean, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class CustomerProfile(Base):
    __tablename__ = "customer_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), unique=True, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(220))
    website: Mapped[str | None] = mapped_column(String(220))
    phone: Mapped[str | None] = mapped_column(String(40))
    account_manager: Mapped[str | None] = mapped_column(String(180))
    sales_owner: Mapped[str | None] = mapped_column(String(180))
    payment_terms: Mapped[str] = mapped_column(String(40), default="Net 30")
    tax_exempt: Mapped[bool] = mapped_column(Boolean, default=False)
    credit_hold: Mapped[bool] = mapped_column(Boolean, default=False)
    onboarding_status: Mapped[str] = mapped_column(String(40), default="active")
    preferred_contact_method: Mapped[str] = mapped_column(String(30), default="email")
    billing_address: Mapped[dict | None] = mapped_column(JSON)
    operating_preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    customer = relationship("Customer", back_populates="profile")


class CustomerLocation(Base):
    __tablename__ = "customer_locations"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(180))
    location_type: Mapped[str] = mapped_column(String(40), default="shipping")
    address1: Mapped[str] = mapped_column(String(220))
    address2: Mapped[str | None] = mapped_column(String(220))
    city: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(40))
    postal_code: Mapped[str] = mapped_column(String(20), index=True)
    country: Mapped[str] = mapped_column(String(3), default="USA")
    contact_name: Mapped[str | None] = mapped_column(String(180))
    phone: Mapped[str | None] = mapped_column(String(40))
    email: Mapped[str | None] = mapped_column(String(180))
    dock_hours: Mapped[str | None] = mapped_column(String(120))
    appointment_required: Mapped[bool] = mapped_column(Boolean, default=False)
    liftgate_default: Mapped[bool] = mapped_column(Boolean, default=False)
    residential: Mapped[bool] = mapped_column(Boolean, default=False)
    limited_access: Mapped[bool] = mapped_column(Boolean, default=False)
    instructions: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="locations")


class CustomerContact(Base):
    __tablename__ = "customer_contacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(140))
    email: Mapped[str | None] = mapped_column(String(180), index=True)
    phone: Mapped[str | None] = mapped_column(String(40))
    mobile: Mapped[str | None] = mapped_column(String(40))
    role: Mapped[str] = mapped_column(String(40), default="operations")
    primary: Mapped[bool] = mapped_column(Boolean, default=False)
    billing_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    quote_contact: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    customer = relationship("Customer", back_populates="contacts")


class CustomerActivity(Base):
    __tablename__ = "customer_activities"

    id: Mapped[int] = mapped_column(primary_key=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id", ondelete="CASCADE"), index=True)
    activity_type: Mapped[str] = mapped_column(String(40), default="note")
    subject: Mapped[str] = mapped_column(String(220))
    body: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[str | None] = mapped_column(String(180))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    customer = relationship("Customer", back_populates="activities")
