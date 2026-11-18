from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Shipment, TrackingEvent
from app.schemas.entities import ShipmentUpdate


def update_shipment(db: Session, shipment: Shipment, payload: ShipmentUpdate) -> Shipment:
    fields = payload.model_fields_set
    previous_actual_pickup = shipment.actual_pickup_at
    previous_delivered = shipment.delivered_at

    if "pro_number" in fields:
        shipment.pro_number = (payload.pro_number or "").strip() or None
    if "po_number" in fields:
        shipment.po_number = (payload.po_number or "").strip() or None
    if "customer_reference" in fields:
        shipment.customer_reference = (payload.customer_reference or "").strip() or None
    if "package_count" in fields:
        if shipment.quote_id:
            from app.services.freight_totals import confirmed_package_count
            shipment.package_count = confirmed_package_count(shipment.handling_units, payload.package_count)
        else:
            shipment.package_count = payload.package_count
    if "package_type" in fields:
        shipment.package_type = (payload.package_type or "").strip() or None
    if "commodity_description" in fields:
        shipment.commodity_description = (payload.commodity_description or "").strip() or None
    if "nmfc_number" in fields:
        shipment.nmfc_number = (payload.nmfc_number or "").strip() or None
    if "hazmat_emergency_contact" in fields:
        shipment.hazmat_emergency_contact = (payload.hazmat_emergency_contact or "").strip() or None
    if "hazmat_emergency_phone" in fields:
        shipment.hazmat_emergency_phone = (payload.hazmat_emergency_phone or "").strip() or None
    if "declared_value" in fields:
        shipment.declared_value = payload.declared_value
    if "scheduled_pickup_at" in fields:
        shipment.scheduled_pickup_at = payload.scheduled_pickup_at
        shipment.pickup_date = payload.scheduled_pickup_at.date() if payload.scheduled_pickup_at else None
    if "requested_delivery_at" in fields:
        shipment.requested_delivery_at = payload.requested_delivery_at
    if "actual_pickup_at" in fields:
        shipment.actual_pickup_at = payload.actual_pickup_at
    if "delivered_at" in fields:
        shipment.delivered_at = payload.delivered_at
    if "status" in fields and payload.status:
        shipment.status = payload.status

    # Operational timestamps can advance the shipment automatically. Users may still
    # explicitly select a different status through the status control when needed.
    if shipment.delivered_at:
        shipment.status = "delivered"
    elif shipment.actual_pickup_at and shipment.status in {"booked", "pickup_requested", "dispatched"}:
        shipment.status = "picked_up"

    if previous_actual_pickup is None and shipment.actual_pickup_at is not None:
        db.add(TrackingEvent(
            shipment_id=shipment.id,
            code="PICKED_UP",
            status="Picked Up",
            description="Actual pickup recorded in Valhalla Freight.",
            location=_location(shipment.origin),
            event_time=shipment.actual_pickup_at,
            source="manual",
        ))
    if previous_delivered is None and shipment.delivered_at is not None:
        db.add(TrackingEvent(
            shipment_id=shipment.id,
            code="DELIVERED",
            status="Delivered",
            description="Actual delivery recorded in Valhalla Freight.",
            location=_location(shipment.destination),
            event_time=shipment.delivered_at,
            source="manual",
        ))

    db.commit()
    db.refresh(shipment)
    return shipment


def _location(address: dict | None) -> str | None:
    if not address:
        return None
    city = address.get("city")
    state = address.get("state")
    if city and state:
        return f"{city}, {state}"
    return city or state
