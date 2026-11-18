from datetime import datetime
from sqlalchemy import ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class BrokerCustomerAssignment(Base):
    """An explicit, single broker workspace for an existing customer company.

    This leaves manufacturer workspace ownership and user accounts intact.
    """
    __tablename__ = 'broker_customer_assignments'
    customer_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), primary_key=True)
    broker_company_id: Mapped[int] = mapped_column(ForeignKey('customers.id'), index=True)
    assigned_by: Mapped[int | None] = mapped_column(ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
