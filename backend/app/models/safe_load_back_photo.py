from sqlalchemy import ForeignKey,String
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
class SafeLoadBackPhoto(Base):
    __tablename__='safe_load_back_photos'
    attempt_id:Mapped[int]=mapped_column(ForeignKey('safe_load_photo_attempts.id'),primary_key=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    path:Mapped[str]=mapped_column(String(500))
