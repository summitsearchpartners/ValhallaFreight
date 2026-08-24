from __future__ import annotations
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

@dataclass
class NormalizedRate:
    carrier_code: str
    carrier_name: str
    service: str
    transit_days: int
    carrier_cost: Decimal
    base_charge: Decimal = Decimal('0')
    fuel: Decimal = Decimal('0')
    accessorials: Decimal = Decimal('0')
    provider_quote_id: str | None = None
    movement_type: str | None = None
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

@dataclass
class NormalizedTrackingEvent:
    code: str
    status: str
    description: str | None = None
    location: str | None = None
    event_time: str | None = None
    source: str = 'carrier_api'
