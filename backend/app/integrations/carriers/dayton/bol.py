from .client import DaytonClient

async def create_standard(payload: dict):
    return await DaytonClient().request('POST','/api/BillOfLading/v2/CreateStandardElectronicBillOfLading',json=payload)
async def update_standard(payload: dict):
    return await DaytonClient().request('POST','/api/BillOfLading/v2/UpdateStandardElectronicBillOfLading',json=payload)
async def create_pdf(payload: dict):
    return await DaytonClient().request('PUT','/api/Shipping/BillOfLading',json=payload)
