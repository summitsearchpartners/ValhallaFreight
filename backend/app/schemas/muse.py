from decimal import Decimal
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StrictBool, StringConstraints

CarrierName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=180)]


class MuseRateInput(BaseModel):
    carrier_name: CarrierName
    carrier_id: int | None = Field(default=None, gt=0)
    carrier_cost: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2, allow_inf_nan=False)
    transit_days: int | None = Field(default=None, ge=1, le=90)
    customer_price: Decimal = Field(gt=0, max_digits=12, decimal_places=2, allow_inf_nan=False)


class MuseRateOut(MuseRateInput):
    revision: UUID


class MuseRateSelect(BaseModel):
    revision: UUID

CREDIT_APPLICATION_URL = "https://cdntms.taicloud.net/tms/Credit_Application.pdf"


class MusePreview(BaseModel):
    provider: str = "muse_freight"
    status: str = "preview"
    service: str = "LTL Freight"
    rate: MuseRateOut | None = None
    services: list[str] = [
        "LTL Freight", "Truckload Freight", "Intermodal Freight",
        "Expedited Freight", "Refrigerated Freight",
    ]


class MuseAccountUpdate(BaseModel):
    account_verified: StrictBool


class MuseAccountStatus(BaseModel):
    account_verified: bool
    credit_application_url: str = CREDIT_APPLICATION_URL


class MusePreviewSelection(MuseAccountStatus):
    selected: bool = False
    manufacturer_id: int
    application_status: str
    rate: MuseRateOut
    first_selection: bool
    show_onboarding: bool
