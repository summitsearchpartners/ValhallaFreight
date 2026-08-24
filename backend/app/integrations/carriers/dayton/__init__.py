from __future__ import annotations
from app.integrations.base import CarrierAdapter, register_carrier
from .client import DaytonClient
from .models import DAYTON_CAPABILITIES

class DaytonAdapter(CarrierAdapter):
    code='DAFG'; name='Dayton Freight Lines'; capabilities=tuple(DAYTON_CAPABILITIES)
    def __init__(self, db=None): self.db=db
    def client(self): return DaytonClient.from_db(self.db) if self.db is not None else DaytonClient()
    def configured(self): return self.client().has_credentials
    async def test_connection(self):
        client=self.client()
        if not client.has_credentials:
            return {'ok':False,'configured':False,'message':'Adapter is installed and ready. Save Dayton credentials in the Integration Hub to enable live API calls.'}
        accounts=await client.request('GET','/api/Accounts')
        return {'ok':True,'configured':True,'message':'Authenticated successfully with Dayton Freight.','accounts':accounts.get('accounts',[]) if isinstance(accounts,dict) else []}

register_carrier('DAFG', DaytonAdapter)
