from datetime import datetime
from sqlalchemy import ForeignKey,String,DateTime,Integer,Boolean
from sqlalchemy.orm import Mapped,mapped_column
from app.db.base import Base
class OperationRun(Base):
    __tablename__='operation_runs'
    id:Mapped[int]=mapped_column(primary_key=True)
    customer_id:Mapped[int|None]=mapped_column(ForeignKey('customers.id'),index=True)
    integration_id:Mapped[int|None]=mapped_column(Integer)
    shipment_id:Mapped[int|None]=mapped_column(ForeignKey('shipments.id'),index=True)
    kind:Mapped[str]=mapped_column(String(40))
    status:Mapped[str]=mapped_column(String(30))
    summary:Mapped[str]=mapped_column(String(250))
    started_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    finished_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    retryable:Mapped[bool]=mapped_column(Boolean,default=False)
