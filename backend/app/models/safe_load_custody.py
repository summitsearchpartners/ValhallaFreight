from datetime import datetime
from sqlalchemy import ForeignKey,String,DateTime,JSON
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
class SafeLoadCustodySnapshot(Base):
    __tablename__='safe_load_custody_snapshots'
    id:Mapped[int]=mapped_column(primary_key=True)
    shipment_id:Mapped[int]=mapped_column(ForeignKey('shipments.id'),index=True)
    customer_id:Mapped[int]=mapped_column(ForeignKey('customers.id'),index=True)
    revision:Mapped[int]
    action:Mapped[str]=mapped_column(String(60))
    phase:Mapped[str]=mapped_column(String(40))
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    payload:Mapped[dict]=mapped_column(JSON)
    previous_digest:Mapped[str]=mapped_column(String(64))
    digest:Mapped[str]=mapped_column(String(64))
