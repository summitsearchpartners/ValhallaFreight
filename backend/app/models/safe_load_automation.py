from datetime import datetime
from sqlalchemy import String,Text,JSON,DateTime,ForeignKey
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
class SafeLoadCallProfile(Base):
    __tablename__='safe_load_call_profiles'
    scope_key:Mapped[str]=mapped_column(String(80),primary_key=True)
    customer_id:Mapped[int|None]=mapped_column(ForeignKey('customers.id'),nullable=True,unique=True)
    contact_name:Mapped[str]=mapped_column(String(180))
    phone:Mapped[str]=mapped_column(String(60))
    updated_by:Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    updated_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class SafeLoadPhotoExtraction(Base):
    __tablename__='safe_load_photo_extractions'
    attempt_id:Mapped[int]=mapped_column(ForeignKey('safe_load_photo_attempts.id'),primary_key=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    summary:Mapped[dict]=mapped_column(JSON)
    encrypted_data:Mapped[str]=mapped_column(Text)
