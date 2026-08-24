from .client import DaytonClient
from .mapper import normalize_tracking

async def track(number: str, number_type: str='Pro'):
    client=DaytonClient()
    payload=await client.request('GET','/api/Tracking/ByNumber',params=[('number',number),('type',number_type)])
    return normalize_tracking(payload), payload

async def history(pro: str):
    return await DaytonClient().request('GET','/api/Tracking/History',params={'number':pro})
