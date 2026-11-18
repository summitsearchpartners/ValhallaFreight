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

    async def book_shipment(self, shipment, db=None):
        """Optional carrier booking/eBOL capability. Return a normalized dict containing pro_number/provider_reference when available."""
        raise NotImplementedError

    async def get_invoices(self, *args, **kwargs):
        """Optional carrier capability. Implementations normalize invoice records into Valhalla's finance ingestion pipeline."""
        raise NotImplementedError
