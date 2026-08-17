from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models import PricingRule
from app.schemas.entities import PricingRuleCreate, PricingRuleOut
router = APIRouter(prefix="/pricing-rules", tags=["Pricing"])
@router.get("", response_model=list[PricingRuleOut])
def list_rules(db: Session = Depends(get_db)): return db.query(PricingRule).order_by(PricingRule.priority).all()
@router.post("", response_model=PricingRuleOut)
def create_rule(payload: PricingRuleCreate, db: Session = Depends(get_db)):
    r = PricingRule(**payload.model_dump()); db.add(r); db.commit(); db.refresh(r); return r
