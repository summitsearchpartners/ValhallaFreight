from typing import Any
from pydantic import BaseModel, ConfigDict, Field

class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

class Address(BaseModel):
    name: str | None = None
    address1: str
    address2: str | None = None
    city: str
    state: str
    postal_code: str
    country: str = "US"
    contact_name: str | None = None
    phone: str | None = None
    email: str | None = None
    instructions: str | None = None
    dock_hours: str | None = None
    location_id: int | None = None
    # Original ZIP returned by the verified address source (Google Places or saved location).
    # Shipment approval compares this to the ZIP that was actually rated.
    verified_postal_code: str | None = None
    # City/state returned by the verified address source. These let booking verify
    # that the user did not alter the locality after selecting a Google result.
    verified_city: str | None = None
    verified_state: str | None = None

class HandlingUnit(BaseModel):
    quantity: int = Field(default=1, ge=1)
    type: str = "Pallet"
    weight_lbs: float = Field(gt=0)
    length_in: float = Field(gt=0)
    width_in: float = Field(gt=0)
    height_in: float = Field(gt=0)
    freight_class: str
    nmfc: str | None = None
    description: str | None = None
