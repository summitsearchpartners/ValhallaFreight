from .client import DaytonClient
from .mapper import build_rate_payload, normalize_rate

async def get_rate(request, *, account: str|None=None, direct_only: bool=False, terms: str='ThirdPartyPrepaid'):
    client=DaytonClient(); acct=(account or client.account).strip()
    if not acct: raise ValueError('Dayton Freight customer account code is required for live rating')
    payload=build_rate_payload(request,acct,direct_only,terms)
    response=await client.request('POST','/api/Rates',json=payload)
    return normalize_rate(response), payload, response
