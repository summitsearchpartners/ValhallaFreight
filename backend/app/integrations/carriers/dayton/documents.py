from .client import DaytonClient
async def search(pro: str, client: DaytonClient|None=None):
    return await (client or DaytonClient()).request('GET','/api/Images/Search',params={'pro':pro})
async def get(pro: str, doc_type: str, hash_value: str, fmt: str='Pdf', client: DaytonClient|None=None):
    return await (client or DaytonClient()).request('GET','/api/Images',params={'pro':pro,'type':doc_type,'hash':hash_value,'format':fmt})
