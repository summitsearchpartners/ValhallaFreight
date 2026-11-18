from datetime import datetime
from sqlalchemy import ForeignKey, String, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class AdminPortalSecurity(Base):
    __tablename__='admin_portal_security'
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),primary_key=True)
    totp_secret:Mapped[str|None]=mapped_column(Text)
    pending_secret:Mapped[str|None]=mapped_column(Text)
    pending_expires_at:Mapped[datetime|None]=mapped_column(DateTime)
    last_counter:Mapped[int]=mapped_column(Integer,default=-1)
    failed_attempts:Mapped[int]=mapped_column(Integer,default=0)
    locked_until:Mapped[datetime|None]=mapped_column(DateTime)

class AdminPortalSession(Base):
    __tablename__='admin_portal_sessions'
    id:Mapped[str]=mapped_column(String(64),primary_key=True)
    user_id:Mapped[int]=mapped_column(ForeignKey('users.id',ondelete='CASCADE'),index=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    portal_type:Mapped[str]=mapped_column(String(20),nullable=False,default='customer',server_default='customer')
    ticket_hash:Mapped[str]=mapped_column(String(64),unique=True)
    ticket_expires_at:Mapped[datetime]=mapped_column(DateTime)
    expires_at:Mapped[datetime]=mapped_column(DateTime)
    redeemed_at:Mapped[datetime|None]=mapped_column(DateTime)
    revoked_at:Mapped[datetime|None]=mapped_column(DateTime)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
