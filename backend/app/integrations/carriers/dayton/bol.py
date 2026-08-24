from .client import DaytonClient

async def create_standard(payload: dict, client: DaytonClient|None=None):
    return await (client or DaytonClient()).request('POST','/api/BillOfLading/v2/CreateStandardElectronicBillOfLading',json=payload)
async def update_standard(payload: dict, client: DaytonClient|None=None):
    return await (client or DaytonClient()).request('POST','/api/BillOfLading/v2/UpdateStandardElectronicBillOfLading',json=payload)
async def create_pdf(payload: dict, client: DaytonClient|None=None):
    return await (client or DaytonClient()).request('PUT','/api/Shipping/BillOfLading',json=payload)
