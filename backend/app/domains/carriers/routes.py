from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from uuid import uuid4
import re
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.config import settings
from app.models import (
    Carrier,
    CarrierActivity,
    CarrierCompliance,
    CarrierComplianceDocumentVersion,
    CarrierContact,
    CarrierContract,
    CarrierDocument,
    CarrierLane,
    CarrierProfile,
    CarrierServiceArea,
    CarrierServiceCapability,
    CarrierTerminal,
    Claim,
    PricingRule,
    Shipment,
)

router = APIRouter(prefix="/carrier-360", tags=["Carrier 360"])

ALLOWED_COMPLIANCE_EXTENSIONS = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
ALLOWED_COMPLIANCE_CONTENT_TYPES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/jpeg",
    "image/png",
}

def _safe_filename(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", Path(name).name).strip("._")
    return cleaned or "compliance-document"

def _compliance_storage_dir(carrier_id: int, compliance_id: int) -> Path:
    root = Path(settings.document_storage_path).resolve()
    dest = root / "carriers" / str(carrier_id) / "compliance" / str(compliance_id)
    dest.mkdir(parents=True, exist_ok=True)
    return dest

def _current_compliance_version(db: Session, carrier_id: int, compliance_id: int):
    return (db.query(CarrierComplianceDocumentVersion)
        .filter(CarrierComplianceDocumentVersion.carrier_id == carrier_id,
                CarrierComplianceDocumentVersion.compliance_id == compliance_id,
                CarrierComplianceDocumentVersion.is_current.is_(True))
        .order_by(CarrierComplianceDocumentVersion.version_number.desc())
        .first())


class CarrierCreate(BaseModel):
    name: str
    scac: str = Field(min_length=2, max_length=10)
    mode: str = "LTL"
    active: bool = True
    api_enabled: bool = False
    mc_number: str | None = None
    dot_number: str | None = None
    authority_status: str = "pending"
    preferred: bool = False


class CarrierUpdate(BaseModel):
    name: str | None = None
    scac: str | None = None
    mode: str | None = None
    active: bool | None = None
    api_enabled: bool | None = None
    on_time_pct: Decimal | None = None
    claims_pct: Decimal | None = None
    preferred: bool | None = None
    authority_status: str | None = None
    payment_terms: str | None = None
    factoring_company: str | None = None
    cargo_limit: Decimal | None = None
    auto_liability_limit: Decimal | None = None
    insurance_expires_at: date | None = None
    mc_number: str | None = None
    dot_number: str | None = None
    legal_name: str | None = None
    website: str | None = None
    main_phone: str | None = None
    dispatch_email: str | None = None
    billing_email: str | None = None
    address1: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str | None = None
    onboarding_status: str | None = None
    safety_rating: str | None = None
    preferred_rank: int | None = None
    notes: str | None = None


class ContactPayload(BaseModel):
    name: str
    role: str = "Operations"
    email: str | None = None
    phone: str | None = None
    primary: bool = False


class TerminalPayload(BaseModel):
    name: str
    city: str
    state: str
    postal_code: str | None = None
    phone: str | None = None


class CompliancePayload(BaseModel):
    item_type: str
    status: str = "valid"
    expires_at: date | None = None
    document_url: str | None = None
    verified_at: datetime | None = None


class CapabilityPayload(BaseModel):
    mode: str = "LTL"
    service_level: str = "Standard"
    equipment: str | None = None
    active: bool = True


class ServiceAreaPayload(BaseModel):
    area_type: str = "state"
    value: str
    description: str | None = None
    active: bool = True


class LanePayload(BaseModel):
    origin_region: str
    destination_region: str
    mode: str = "LTL"
    service_level: str = "Standard"
    target_cost: Decimal | None = None
    avg_transit_days: int | None = None
    active: bool = True
    notes: str | None = None


class ContractPayload(BaseModel):
    name: str
    contract_type: str = "Transportation Agreement"
    reference_number: str | None = None
    effective_date: date | None = None
    expiration_date: date | None = None
    status: str = "active"
    document_url: str | None = None
    notes: str | None = None


class DocumentPayload(BaseModel):
    document_type: str = "Other"
    name: str
    file_url: str | None = None
    expires_at: date | None = None
    status: str = "current"


class ActivityPayload(BaseModel):
    activity_type: str = "note"
    subject: str
    body: str | None = None
    created_by: str = "Valhalla Freight"


def _carrier(db: Session, carrier_id: int) -> Carrier:
    row = db.get(Carrier, carrier_id)
    if not row:
        raise HTTPException(404, "Carrier not found")
    return row


def _profile(db: Session, carrier_id: int) -> CarrierProfile:
    row = db.query(CarrierProfile).filter(CarrierProfile.carrier_id == carrier_id).first()
    if not row:
        row = CarrierProfile(carrier_id=carrier_id)
        db.add(row)
        db.flush()
    return row


def _status_tone(status: str | None) -> str:
    s = (status or "").lower()
    if s in {"active", "valid", "current", "approved", "satisfactory"}:
        return "success"
    if s in {"pending", "review", "expiring", "conditional"}:
        return "warning"
    if s in {"inactive", "expired", "revoked", "blocked", "unsatisfactory"}:
        return "danger"
    return "neutral"


def _performance(db: Session, carrier: Carrier) -> dict[str, Any]:
    shipments = db.query(Shipment).filter(Shipment.carrier_id == carrier.id).all()
    total = len(shipments)
    delivered = [s for s in shipments if s.delivered_at]
    scheduled_pickups = [s for s in shipments if s.actual_pickup_at and s.scheduled_pickup_at]
    delivery_commitments = [s for s in delivered if s.requested_delivery_at or s.estimated_delivery]

    on_time_delivery = 0
    for s in delivery_commitments:
        target = s.requested_delivery_at
        if target is None and s.estimated_delivery:
            target = datetime.combine(s.estimated_delivery, datetime.max.time())
        if target and s.delivered_at and s.delivered_at <= target:
            on_time_delivery += 1

    on_time_pickup = sum(1 for s in scheduled_pickups if s.actual_pickup_at <= s.scheduled_pickup_at)
    cost = sum(float(s.final_carrier_cost if s.final_carrier_cost is not None else s.carrier_cost or 0) for s in shipments)
    revenue = sum(float(s.customer_charge or 0) for s in shipments)
    gp = revenue - cost
    claim_count = db.query(Claim).join(Shipment, Claim.shipment_id == Shipment.id).filter(Shipment.carrier_id == carrier.id).count()
    claim_amount = db.query(func.coalesce(func.sum(Claim.amount), 0)).join(Shipment, Claim.shipment_id == Shipment.id).filter(Shipment.carrier_id == carrier.id).scalar() or 0

    transit_days = []
    for s in delivered:
        start = s.actual_pickup_at or s.scheduled_pickup_at
        if start and s.delivered_at:
            transit_days.append(max(0, (s.delivered_at - start).total_seconds() / 86400))

    return {
        "shipments": total,
        "delivered_shipments": len(delivered),
        "on_time_delivery_pct": round((on_time_delivery / len(delivery_commitments) * 100), 1) if delivery_commitments else float(carrier.on_time_pct or 0),
        "on_time_pickup_pct": round((on_time_pickup / len(scheduled_pickups) * 100), 1) if scheduled_pickups else 0.0,
        "avg_transit_days": round(sum(transit_days) / len(transit_days), 1) if transit_days else 0.0,
        "carrier_spend": round(cost, 2),
        "customer_revenue": round(revenue, 2),
        "gross_profit": round(gp, 2),
        "margin_pct": round((gp / revenue * 100), 1) if revenue else 0.0,
        "avg_cost": round(cost / total, 2) if total else 0.0,
        "claims": claim_count,
        "claim_amount": float(claim_amount),
        "claims_pct": round((claim_count / total * 100), 2) if total else float(carrier.claims_pct or 0),
    }


def _lane_rollup(shipments: list[Shipment]) -> list[dict[str, Any]]:
    agg: dict[str, dict[str, Any]] = {}
    for s in shipments:
        o = s.origin or {}
        d = s.destination or {}
        origin = ", ".join(x for x in [o.get("city"), o.get("state")] if x) or o.get("postal_code") or "Origin"
        dest = ", ".join(x for x in [d.get("city"), d.get("state")] if x) or d.get("postal_code") or "Destination"
        key = f"{origin} → {dest}"
        cost = float(s.final_carrier_cost if s.final_carrier_cost is not None else s.carrier_cost or 0)
        row = agg.setdefault(key, {"lane": key, "shipments": 0, "carrier_cost": 0.0, "revenue": 0.0})
        row["shipments"] += 1
        row["carrier_cost"] += cost
        row["revenue"] += float(s.customer_charge or 0)
    rows = []
    for row in agg.values():
        row["avg_cost"] = round(row["carrier_cost"] / row["shipments"], 2) if row["shipments"] else 0
        row["gross_profit"] = round(row["revenue"] - row["carrier_cost"], 2)
        rows.append(row)
    return sorted(rows, key=lambda x: x["shipments"], reverse=True)[:10]


@router.get("")
def list_carrier_360(db: Session = Depends(get_db)):
    carriers = db.query(Carrier).order_by(Carrier.name).all()
    result = []
    for c in carriers:
        p = db.query(CarrierProfile).filter(CarrierProfile.carrier_id == c.id).first()
        perf = _performance(db, c)
        compliance = db.query(CarrierCompliance).filter(CarrierCompliance.carrier_id == c.id).all()
        compliance_ok = all((x.status or "").lower() == "valid" and (not x.expires_at or x.expires_at >= date.today()) for x in compliance) if compliance else False
        modes = [x.mode for x in db.query(CarrierServiceCapability).filter(CarrierServiceCapability.carrier_id == c.id, CarrierServiceCapability.active.is_(True)).all()]
        result.append({
            "id": c.id,
            "scac": c.scac,
            "name": c.name,
            "mode": c.mode,
            "modes": modes or [c.mode],
            "active": c.active,
            "api_enabled": c.api_enabled,
            "preferred": bool(p.preferred) if p else False,
            "preferred_rank": p.preferred_rank if p else None,
            "authority_status": p.authority_status if p else "pending",
            "onboarding_status": p.onboarding_status if p else "pending",
            "safety_rating": p.safety_rating if p else "unknown",
            "compliance_ok": compliance_ok,
            **perf,
        })
    return result


@router.post("")
def create_carrier(payload: CarrierCreate, db: Session = Depends(get_db)):
    scac = payload.scac.strip().upper()
    if db.query(Carrier).filter(func.upper(Carrier.scac) == scac).first():
        raise HTTPException(409, "A carrier with this SCAC already exists")
    carrier = Carrier(name=payload.name.strip(), scac=scac, mode=payload.mode, active=payload.active, api_enabled=payload.api_enabled)
    db.add(carrier)
    db.flush()
    db.add(CarrierProfile(carrier_id=carrier.id, mc_number=payload.mc_number, dot_number=payload.dot_number, authority_status=payload.authority_status, preferred=payload.preferred, legal_name=payload.name.strip(), onboarding_status="review"))
    db.add(CarrierServiceCapability(carrier_id=carrier.id, mode=payload.mode, service_level="Standard", active=True))
    db.add(CarrierActivity(carrier_id=carrier.id, activity_type="system", subject="Carrier created", body="Carrier master record created in Valhalla Freight.", created_by="Valhalla Freight"))
    db.commit()
    db.refresh(carrier)
    return {"id": carrier.id, "scac": carrier.scac, "name": carrier.name}


@router.get("/{carrier_id}")
def carrier_detail(carrier_id: int, db: Session = Depends(get_db)):
    c = _carrier(db, carrier_id)
    p = _profile(db, carrier_id)
    contacts = db.query(CarrierContact).filter(CarrierContact.carrier_id == carrier_id).order_by(CarrierContact.primary.desc(), CarrierContact.name).all()
    terminals = db.query(CarrierTerminal).filter(CarrierTerminal.carrier_id == carrier_id).order_by(CarrierTerminal.state, CarrierTerminal.city).all()
    compliance = db.query(CarrierCompliance).filter(CarrierCompliance.carrier_id == carrier_id).order_by(CarrierCompliance.item_type).all()
    capabilities = db.query(CarrierServiceCapability).filter(CarrierServiceCapability.carrier_id == carrier_id).order_by(CarrierServiceCapability.mode, CarrierServiceCapability.service_level).all()
    service_areas = db.query(CarrierServiceArea).filter(CarrierServiceArea.carrier_id == carrier_id).order_by(CarrierServiceArea.area_type, CarrierServiceArea.value).all()
    lanes = db.query(CarrierLane).filter(CarrierLane.carrier_id == carrier_id).order_by(CarrierLane.origin_region, CarrierLane.destination_region).all()
    contracts = db.query(CarrierContract).filter(CarrierContract.carrier_id == carrier_id).order_by(CarrierContract.status, CarrierContract.expiration_date.desc()).all()
    documents = db.query(CarrierDocument).filter(CarrierDocument.carrier_id == carrier_id).order_by(CarrierDocument.uploaded_at.desc()).all()
    activities = db.query(CarrierActivity).filter(CarrierActivity.carrier_id == carrier_id).order_by(CarrierActivity.created_at.desc()).limit(75).all()
    shipments = db.query(Shipment).filter(Shipment.carrier_id == carrier_id).order_by(Shipment.created_at.desc()).all()
    pricing_rules = db.query(PricingRule).filter(PricingRule.carrier_id == carrier_id).order_by(PricingRule.priority).all()
    perf = _performance(db, c)

    return {
        "carrier": {"id": c.id, "scac": c.scac, "name": c.name, "mode": c.mode, "active": c.active, "api_enabled": c.api_enabled},
        "profile": {
            "mc_number": p.mc_number, "dot_number": p.dot_number, "authority_status": p.authority_status,
            "payment_terms": p.payment_terms, "factoring_company": p.factoring_company,
            "cargo_limit": float(p.cargo_limit or 0), "auto_liability_limit": float(p.auto_liability_limit or 0),
            "insurance_expires_at": p.insurance_expires_at, "preferred": p.preferred,
            "legal_name": p.legal_name, "website": p.website, "main_phone": p.main_phone,
            "dispatch_email": p.dispatch_email, "billing_email": p.billing_email,
            "address1": p.address1, "city": p.city, "state": p.state, "postal_code": p.postal_code,
            "country": p.country, "onboarding_status": p.onboarding_status, "safety_rating": p.safety_rating,
            "preferred_rank": p.preferred_rank, "notes": p.notes,
        },
        "contacts": [{"id": x.id, "name": x.name, "role": x.role, "email": x.email, "phone": x.phone, "primary": x.primary} for x in contacts],
        "terminals": [{"id": x.id, "name": x.name, "city": x.city, "state": x.state, "postal_code": x.postal_code, "phone": x.phone} for x in terminals],
        "compliance": [{
            "id": x.id, "item_type": x.item_type, "status": x.status, "status_tone": _status_tone(x.status),
            "expires_at": x.expires_at, "verified_at": x.verified_at,
            "document_name": x.document_name, "document_content_type": x.document_content_type,
            "document_size_bytes": x.document_size_bytes, "document_uploaded_at": x.document_uploaded_at,
            "has_document": bool(x.document_name),
            "version_count": db.query(CarrierComplianceDocumentVersion).filter(CarrierComplianceDocumentVersion.compliance_id == x.id).count(),
        } for x in compliance],
        "capabilities": [{"id": x.id, "mode": x.mode, "service_level": x.service_level, "equipment": x.equipment, "active": x.active} for x in capabilities],
        "service_areas": [{"id": x.id, "area_type": x.area_type, "value": x.value, "description": x.description, "active": x.active} for x in service_areas],
        "lanes": [{"id": x.id, "origin_region": x.origin_region, "destination_region": x.destination_region, "mode": x.mode, "service_level": x.service_level, "target_cost": float(x.target_cost) if x.target_cost is not None else None, "avg_transit_days": x.avg_transit_days, "active": x.active, "notes": x.notes} for x in lanes],
        "contracts": [{"id": x.id, "name": x.name, "contract_type": x.contract_type, "reference_number": x.reference_number, "effective_date": x.effective_date, "expiration_date": x.expiration_date, "status": x.status, "document_url": x.document_url, "notes": x.notes} for x in contracts],
        "documents": [{"id": x.id, "document_type": x.document_type, "name": x.name, "file_url": x.file_url, "expires_at": x.expires_at, "status": x.status, "uploaded_at": x.uploaded_at} for x in documents],
        "activities": [{"id": x.id, "activity_type": x.activity_type, "subject": x.subject, "body": x.body, "created_by": x.created_by, "created_at": x.created_at} for x in activities],
        "pricing_rules": [{"id": x.id, "name": x.name, "priority": x.priority, "rule_type": x.rule_type, "value": float(x.value or 0), "minimum_margin": float(x.minimum_margin or 0), "origin_zip_prefix": x.origin_zip_prefix, "destination_zip_prefix": x.destination_zip_prefix, "freight_class": x.freight_class, "active": x.active} for x in pricing_rules],
        "performance": perf,
        "lane_rollup": _lane_rollup(shipments),
        "recent_shipments": [{"id": s.id, "shipment_number": s.shipment_number, "status": s.status, "origin": s.origin, "destination": s.destination, "customer_charge": float(s.customer_charge or 0), "carrier_cost": float(s.final_carrier_cost if s.final_carrier_cost is not None else s.carrier_cost or 0), "created_at": s.created_at, "delivered_at": s.delivered_at} for s in shipments[:20]],
    }


@router.patch("/{carrier_id}")
def update_carrier(carrier_id: int, payload: CarrierUpdate, db: Session = Depends(get_db)):
    c = _carrier(db, carrier_id)
    p = _profile(db, carrier_id)
    data = payload.model_dump(exclude_unset=True)
    core_fields = {"name", "scac", "mode", "active", "api_enabled", "on_time_pct", "claims_pct"}
    for key, value in data.items():
        if key in core_fields:
            if key == "scac" and value:
                value = value.upper()
            setattr(c, key, value)
        else:
            setattr(p, key, value)
    db.add(CarrierActivity(carrier_id=carrier_id, activity_type="update", subject="Carrier profile updated", body="Carrier master/profile information was updated.", created_by="Valhalla Freight"))
    db.commit()
    return {"ok": True}


def _create_child(db: Session, model, carrier_id: int, payload: BaseModel, subject: str):
    _carrier(db, carrier_id)
    row = model(carrier_id=carrier_id, **payload.model_dump())
    db.add(row)
    db.flush()
    db.add(CarrierActivity(carrier_id=carrier_id, activity_type="update", subject=subject, body=f"{model.__name__} record added.", created_by="Valhalla Freight"))
    db.commit()
    db.refresh(row)
    return row


def _patch_child(db: Session, model, carrier_id: int, row_id: int, payload: BaseModel):
    _carrier(db, carrier_id)
    row = db.query(model).filter(model.id == row_id, model.carrier_id == carrier_id).first()
    if not row:
        raise HTTPException(404, "Record not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(row, key, value)
    db.commit()
    return {"ok": True}


def _delete_child(db: Session, model, carrier_id: int, row_id: int):
    _carrier(db, carrier_id)
    row = db.query(model).filter(model.id == row_id, model.carrier_id == carrier_id).first()
    if not row:
        raise HTTPException(404, "Record not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/{carrier_id}/contacts")
def add_contact(carrier_id: int, payload: ContactPayload, db: Session = Depends(get_db)):
    row = _create_child(db, CarrierContact, carrier_id, payload, "Carrier contact added")
    return {"id": row.id}


@router.patch("/{carrier_id}/contacts/{row_id}")
def edit_contact(carrier_id: int, row_id: int, payload: ContactPayload, db: Session = Depends(get_db)):
    return _patch_child(db, CarrierContact, carrier_id, row_id, payload)


@router.delete("/{carrier_id}/contacts/{row_id}")
def delete_contact(carrier_id: int, row_id: int, db: Session = Depends(get_db)):
    return _delete_child(db, CarrierContact, carrier_id, row_id)


@router.post("/{carrier_id}/terminals")
def add_terminal(carrier_id: int, payload: TerminalPayload, db: Session = Depends(get_db)):
    row = _create_child(db, CarrierTerminal, carrier_id, payload, "Carrier terminal added")
    return {"id": row.id}


@router.patch("/{carrier_id}/terminals/{row_id}")
def edit_terminal(carrier_id: int, row_id: int, payload: TerminalPayload, db: Session = Depends(get_db)):
    return _patch_child(db, CarrierTerminal, carrier_id, row_id, payload)


@router.delete("/{carrier_id}/terminals/{row_id}")
def delete_terminal(carrier_id: int, row_id: int, db: Session = Depends(get_db)):
    return _delete_child(db, CarrierTerminal, carrier_id, row_id)


@router.post("/{carrier_id}/compliance")
def add_compliance(carrier_id: int, payload: CompliancePayload, db: Session = Depends(get_db)):
    data = payload.model_copy(update={"verified_at": payload.verified_at or datetime.utcnow()})
    row = _create_child(db, CarrierCompliance, carrier_id, data, "Compliance record added")
    return {"id": row.id}


@router.patch("/{carrier_id}/compliance/{row_id}")
def edit_compliance(carrier_id: int, row_id: int, payload: CompliancePayload, db: Session = Depends(get_db)):
    return _patch_child(db, CarrierCompliance, carrier_id, row_id, payload)


@router.delete("/{carrier_id}/compliance/{row_id}")
def delete_compliance(carrier_id: int, row_id: int, db: Session = Depends(get_db)):
    return _delete_child(db, CarrierCompliance, carrier_id, row_id)


@router.post("/{carrier_id}/compliance/{row_id}/document")
async def upload_compliance_document(carrier_id: int, row_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    _carrier(db, carrier_id)
    compliance = db.query(CarrierCompliance).filter(CarrierCompliance.id == row_id, CarrierCompliance.carrier_id == carrier_id).first()
    if not compliance:
        raise HTTPException(404, "Compliance record not found")

    original_name = _safe_filename(file.filename or "compliance-document")
    ext = Path(original_name).suffix.lower()
    content_type = (file.content_type or "").lower()
    if ext not in ALLOWED_COMPLIANCE_EXTENSIONS:
        raise HTTPException(400, "Unsupported file type. Upload PDF, DOC, DOCX, JPG, JPEG, or PNG files.")
    if content_type and content_type not in ALLOWED_COMPLIANCE_CONTENT_TYPES:
        raise HTTPException(400, "Unsupported document content type.")

    max_bytes = settings.max_compliance_document_mb * 1024 * 1024
    content = await file.read(max_bytes + 1)
    if len(content) > max_bytes:
        raise HTTPException(413, f"Document exceeds the {settings.max_compliance_document_mb} MB upload limit.")
    if not content:
        raise HTTPException(400, "The uploaded document is empty.")

    prior = db.query(CarrierComplianceDocumentVersion).filter(
        CarrierComplianceDocumentVersion.carrier_id == carrier_id,
        CarrierComplianceDocumentVersion.compliance_id == row_id,
    ).order_by(CarrierComplianceDocumentVersion.version_number.desc()).first()
    version_number = (prior.version_number + 1) if prior else 1
    for previous in db.query(CarrierComplianceDocumentVersion).filter(
        CarrierComplianceDocumentVersion.carrier_id == carrier_id,
        CarrierComplianceDocumentVersion.compliance_id == row_id,
        CarrierComplianceDocumentVersion.is_current.is_(True),
    ).all():
        previous.is_current = False

    stored_name = f"v{version_number}_{uuid4().hex}{ext}"
    destination = _compliance_storage_dir(carrier_id, row_id) / stored_name
    destination.write_bytes(content)
    now = datetime.utcnow()
    version = CarrierComplianceDocumentVersion(
        carrier_id=carrier_id, compliance_id=row_id, version_number=version_number,
        original_name=original_name, stored_name=stored_name, content_type=content_type or None,
        size_bytes=len(content), uploaded_by="Valhalla Freight", uploaded_at=now, is_current=True,
    )
    db.add(version)
    compliance.document_name = original_name
    compliance.document_content_type = content_type or None
    compliance.document_size_bytes = len(content)
    compliance.document_uploaded_at = now
    compliance.document_url = f"/api/v1/carrier-360/{carrier_id}/compliance/{row_id}/document"
    compliance.verified_at = compliance.verified_at or now
    db.add(CarrierActivity(
        carrier_id=carrier_id, activity_type="compliance",
        subject=f"{compliance.item_type} document uploaded",
        body=f"Uploaded {original_name} as compliance document version {version_number}.",
        created_by="Valhalla Freight",
    ))
    db.commit()
    return {"ok": True, "name": original_name, "size_bytes": len(content), "version": version_number}


@router.get("/{carrier_id}/compliance/{row_id}/document")
def get_compliance_document(carrier_id: int, row_id: int, db: Session = Depends(get_db)):
    _carrier(db, carrier_id)
    compliance = db.query(CarrierCompliance).filter(CarrierCompliance.id == row_id, CarrierCompliance.carrier_id == carrier_id).first()
    if not compliance:
        raise HTTPException(404, "Compliance record not found")
    version = _current_compliance_version(db, carrier_id, row_id)
    if not version:
        raise HTTPException(404, "No compliance document has been uploaded")
    path = _compliance_storage_dir(carrier_id, row_id) / version.stored_name
    if not path.exists():
        raise HTTPException(404, "Stored compliance document is unavailable")
    return FileResponse(path, media_type=version.content_type or "application/octet-stream", filename=version.original_name)


@router.get("/{carrier_id}/compliance/{row_id}/document-versions")
def get_compliance_document_versions(carrier_id: int, row_id: int, db: Session = Depends(get_db)):
    _carrier(db, carrier_id)
    rows = db.query(CarrierComplianceDocumentVersion).filter(
        CarrierComplianceDocumentVersion.carrier_id == carrier_id,
        CarrierComplianceDocumentVersion.compliance_id == row_id,
    ).order_by(CarrierComplianceDocumentVersion.version_number.desc()).all()
    return [{
        "id": x.id, "version_number": x.version_number, "name": x.original_name,
        "content_type": x.content_type, "size_bytes": x.size_bytes, "uploaded_by": x.uploaded_by,
        "uploaded_at": x.uploaded_at, "is_current": x.is_current,
    } for x in rows]


@router.post("/{carrier_id}/capabilities")
def add_capability(carrier_id: int, payload: CapabilityPayload, db: Session = Depends(get_db)):
    row = _create_child(db, CarrierServiceCapability, carrier_id, payload, "Service capability added")
    return {"id": row.id}


@router.patch("/{carrier_id}/capabilities/{row_id}")
def edit_capability(carrier_id: int, row_id: int, payload: CapabilityPayload, db: Session = Depends(get_db)):
    return _patch_child(db, CarrierServiceCapability, carrier_id, row_id, payload)


@router.delete("/{carrier_id}/capabilities/{row_id}")
def delete_capability(carrier_id: int, row_id: int, db: Session = Depends(get_db)):
    return _delete_child(db, CarrierServiceCapability, carrier_id, row_id)


@router.post("/{carrier_id}/service-areas")
def add_service_area(carrier_id: int, payload: ServiceAreaPayload, db: Session = Depends(get_db)):
    row = _create_child(db, CarrierServiceArea, carrier_id, payload, "Service area added")
    return {"id": row.id}


@router.patch("/{carrier_id}/service-areas/{row_id}")
def edit_service_area(carrier_id: int, row_id: int, payload: ServiceAreaPayload, db: Session = Depends(get_db)):
    return _patch_child(db, CarrierServiceArea, carrier_id, row_id, payload)


@router.delete("/{carrier_id}/service-areas/{row_id}")
def delete_service_area(carrier_id: int, row_id: int, db: Session = Depends(get_db)):
    return _delete_child(db, CarrierServiceArea, carrier_id, row_id)


@router.post("/{carrier_id}/lanes")
def add_lane(carrier_id: int, payload: LanePayload, db: Session = Depends(get_db)):
    row = _create_child(db, CarrierLane, carrier_id, payload, "Strategic lane added")
    return {"id": row.id}


@router.patch("/{carrier_id}/lanes/{row_id}")
def edit_lane(carrier_id: int, row_id: int, payload: LanePayload, db: Session = Depends(get_db)):
    return _patch_child(db, CarrierLane, carrier_id, row_id, payload)


@router.delete("/{carrier_id}/lanes/{row_id}")
def delete_lane(carrier_id: int, row_id: int, db: Session = Depends(get_db)):
    return _delete_child(db, CarrierLane, carrier_id, row_id)


@router.post("/{carrier_id}/contracts")
def add_contract(carrier_id: int, payload: ContractPayload, db: Session = Depends(get_db)):
    row = _create_child(db, CarrierContract, carrier_id, payload, "Carrier contract added")
    return {"id": row.id}


@router.patch("/{carrier_id}/contracts/{row_id}")
def edit_contract(carrier_id: int, row_id: int, payload: ContractPayload, db: Session = Depends(get_db)):
    return _patch_child(db, CarrierContract, carrier_id, row_id, payload)


@router.delete("/{carrier_id}/contracts/{row_id}")
def delete_contract(carrier_id: int, row_id: int, db: Session = Depends(get_db)):
    return _delete_child(db, CarrierContract, carrier_id, row_id)


@router.post("/{carrier_id}/documents")
def add_document(carrier_id: int, payload: DocumentPayload, db: Session = Depends(get_db)):
    row = _create_child(db, CarrierDocument, carrier_id, payload, "Carrier document added")
    return {"id": row.id}


@router.patch("/{carrier_id}/documents/{row_id}")
def edit_document(carrier_id: int, row_id: int, payload: DocumentPayload, db: Session = Depends(get_db)):
    return _patch_child(db, CarrierDocument, carrier_id, row_id, payload)


@router.delete("/{carrier_id}/documents/{row_id}")
def delete_document(carrier_id: int, row_id: int, db: Session = Depends(get_db)):
    return _delete_child(db, CarrierDocument, carrier_id, row_id)


@router.post("/{carrier_id}/activities")
def add_activity(carrier_id: int, payload: ActivityPayload, db: Session = Depends(get_db)):
    _carrier(db, carrier_id)
    row = CarrierActivity(carrier_id=carrier_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id}
