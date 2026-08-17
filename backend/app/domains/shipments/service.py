from datetime import datetime
from sqlalchemy.orm import Session
from app.models import Shipment, TrackingEvent
from app.schemas.entities import ShipmentUpdate


def update_shipment(db: Session, shipment: Shipment, payload: ShipmentUpdate) -> Shipment:
    fields = payload.model_fields_set
    previous_actual_pickup = shipment.actual_pickup_at
    previous_delivered = shipment.delivered_at

    if "bol_number" in fields:
        shipment.bol_number = (payload.bol_number or "").strip() or None
    if "pro_number" in fields:
        shipment.pro_number = (payload.pro_number or "").strip() or None
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
