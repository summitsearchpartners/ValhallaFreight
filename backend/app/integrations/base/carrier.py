from __future__ import annotations
from abc import ABC, abstractmethod

class CarrierAdapter(ABC):
    code: str
    name: str
    capabilities: tuple[str, ...] = ()

    @abstractmethod
    def configured(self) -> bool: ...

    @abstractmethod
    async def test_connection(self) -> dict: ...

    async def get_rates(self, request):
        raise NotImplementedError

    async def track(self, number: str, number_type: str='Pro'):
        raise NotImplementedError
