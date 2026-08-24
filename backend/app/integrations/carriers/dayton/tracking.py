from .client import DaytonClient
from .mapper import normalize_tracking

async def track(number: str, number_type: str='Pro', client: DaytonClient|None=None):
    client=client or DaytonClient()
    payload=await client.request('GET','/api/Tracking/ByNumber',params=[('number',number),('type',number_type)])
    return normalize_tracking(payload), payload

async def history(pro: str, client: DaytonClient|None=None):
    client=client or DaytonClient()
    return await client.request('GET','/api/Tracking/History',params={'number':pro})
