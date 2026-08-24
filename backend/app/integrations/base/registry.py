from __future__ import annotations
from typing import Callable
from .carrier import CarrierAdapter

_REGISTRY: dict[str, Callable[[], CarrierAdapter]] = {}

def register_carrier(code: str, factory: Callable[[], CarrierAdapter]):
    _REGISTRY[code.upper()] = factory

def get_carrier(code: str) -> CarrierAdapter | None:
    factory = _REGISTRY.get(code.upper())
    return factory() if factory else None

def registered_carriers() -> list[str]:
    return sorted(_REGISTRY)
