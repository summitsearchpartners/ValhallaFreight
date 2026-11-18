from datetime import datetime
from sqlalchemy import ForeignKey,String,Text,DateTime,JSON
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
class SafeLoadBrokerContact(Base):
    __tablename__='safe_load_broker_contacts'
    shipment_id:Mapped[int]=mapped_column(ForeignKey('shipments.id'),primary_key=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    broker_name:Mapped[str]=mapped_column(String(180))
    phone:Mapped[str]=mapped_column(String(60))
class SafeLoadPhotoAttempt(Base):
    __tablename__='safe_load_photo_attempts'
    id:Mapped[int]=mapped_column(primary_key=True)
    shipment_id:Mapped[int]=mapped_column(ForeignKey('shipments.id'),index=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    revision:Mapped[int]
    operator_id:Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    license_path:Mapped[str]=mapped_column(Text)
    vin_path:Mapped[str]=mapped_column(Text)
    status:Mapped[str]=mapped_column(String(40))
    reasons:Mapped[list]=mapped_column(JSON)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
