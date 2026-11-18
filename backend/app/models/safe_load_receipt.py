from datetime import datetime
from sqlalchemy import ForeignKey,String,DateTime
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
class SafeLoadReleaseReceipt(Base):
    __tablename__='safe_load_release_receipts'
    shipment_id:Mapped[int]=mapped_column(ForeignKey('shipments.id'),primary_key=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    confirmation_number:Mapped[str]=mapped_column(String(50),unique=True)
    revision:Mapped[int]
    released_by:Mapped[int|None]=mapped_column(ForeignKey('users.id',ondelete='SET NULL'))
    released_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    method:Mapped[str]=mapped_column(String(40))
