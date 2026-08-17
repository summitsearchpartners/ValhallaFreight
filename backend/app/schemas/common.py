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
