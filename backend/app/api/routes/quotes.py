from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import Quote
from app.schemas.entities import QuoteRequest, QuoteResponse
from app.services.rating import RatingEngine
router = APIRouter(prefix="/quotes", tags=["Quotes"])
@router.post("/rate", response_model=QuoteResponse)
def rate(payload: QuoteRequest, db: Session = Depends(get_db)):
    try: options = RatingEngine(db).get_rates(payload)
    except ValueError as e: raise HTTPException(status_code=404, detail=str(e))
    number = f"FFQ-{datetime.utcnow():%y%m%d%H%M%S%f}"[-22:]
    expires = datetime.utcnow() + timedelta(hours=24)
    q = Quote(quote_number=number, customer_id=payload.customer_id, origin=payload.origin.model_dump(), destination=payload.destination.model_dump(),
              handling_units=[u.model_dump() for u in payload.handling_units], accessorials=payload.accessorials,
              options=[o.model_dump(mode="json") for o in options], expires_at=expires)
    db.add(q); db.commit()
    return QuoteResponse(quote_number=number, options=options, expires_at=expires)
