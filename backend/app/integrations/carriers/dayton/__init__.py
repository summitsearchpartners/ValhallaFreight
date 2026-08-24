from __future__ import annotations
from app.integrations.base import CarrierAdapter, register_carrier
from .client import DaytonClient
from .models import DAYTON_CAPABILITIES

class DaytonAdapter(CarrierAdapter):
    code='DAFG'; name='Dayton Freight Lines'; capabilities=tuple(DAYTON_CAPABILITIES)
    def configured(self): return DaytonClient().has_credentials
    async def test_connection(self):
        client=DaytonClient()
        if not client.has_credentials:
            return {'ok':False,'configured':False,'message':'Adapter is installed and ready. Dayton credentials are required for live API calls.'}
        accounts=await client.request('GET','/api/Accounts')
        return {'ok':True,'configured':True,'message':'Authenticated successfully with Dayton Freight.','accounts':accounts.get('accounts',[]) if isinstance(accounts,dict) else []}

register_carrier('DAFG', DaytonAdapter)
