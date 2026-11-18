from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Numeric, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base

class SafeLoadCase(Base):
    __tablename__='safe_load_cases'
    shipment=relationship('Shipment')
    shipment_id:Mapped[int]=mapped_column(ForeignKey('shipments.id'),primary_key=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    status:Mapped[str]=mapped_column(String(40),default='awaiting_assignment',index=True)
    revision:Mapped[int]=mapped_column(Integer,default=0)
    driver_name:Mapped[str|None]=mapped_column(String(180))
    license_digest:Mapped[str|None]=mapped_column(String(64))
    license_last4:Mapped[str|None]=mapped_column(String(4))
    issuing_state:Mapped[str|None]=mapped_column(String(3))
    license_expires:Mapped[datetime|None]=mapped_column(DateTime)
    vin:Mapped[str|None]=mapped_column(String(17))
    photo_path:Mapped[str|None]=mapped_column(Text)
    photo_type:Mapped[str|None]=mapped_column(String(60))
    invite_digest:Mapped[str|None]=mapped_column(String(64),index=True,unique=True)
    invite_expires:Mapped[datetime|None]=mapped_column(DateTime)
    approved_by:Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    verified_by:Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    verified_until:Mapped[datetime|None]=mapped_column(DateTime)
    released_by:Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    released_at:Mapped[datetime|None]=mapped_column(DateTime)
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class SafeLoadEvent(Base):
    __tablename__='safe_load_events'
    id:Mapped[int]=mapped_column(primary_key=True)
    shipment_id:Mapped[int]=mapped_column(ForeignKey('shipments.id'),index=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    action:Mapped[str]=mapped_column(String(60))
    actor:Mapped[str]=mapped_column(String(180))
    detail:Mapped[str]=mapped_column(Text)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class TruckloadOrder(Base):
    __tablename__='truckload_orders'
    id:Mapped[int]=mapped_column(primary_key=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    shipment_id:Mapped[int|None]=mapped_column(ForeignKey('shipments.id'),unique=True,index=True)
    reference:Mapped[str]=mapped_column(String(120),default='')
    status:Mapped[str]=mapped_column(String(40),default='draft')
    equipment:Mapped[str]=mapped_column(String(40))
    commodity:Mapped[str]=mapped_column(String(240))
    weight_lbs:Mapped[int]=mapped_column(Integer)
    packages:Mapped[int]=mapped_column(Integer)
    temperature_min:Mapped[int|None]=mapped_column(Integer)
    temperature_max:Mapped[int|None]=mapped_column(Integer)
    stops:Mapped[list]=mapped_column(JSON)
    customer_price:Mapped[float]=mapped_column(Numeric(12,2),default=0)
    selected_bid_id:Mapped[int|None]=mapped_column(Integer)
    notes:Mapped[str]=mapped_column(Text,default='')
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class TruckloadBid(Base):
    __tablename__='truckload_bids'
    id:Mapped[int]=mapped_column(primary_key=True)
    order_id:Mapped[int]=mapped_column(ForeignKey('truckload_orders.id'),index=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    carrier_id:Mapped[int]=mapped_column(ForeignKey('carriers.id'))
    carrier_cost:Mapped[float]=mapped_column(Numeric(12,2))
    expires_at:Mapped[datetime]=mapped_column(DateTime)
    note:Mapped[str]=mapped_column(Text,default='')
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
