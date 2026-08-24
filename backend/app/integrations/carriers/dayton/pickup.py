from .client import DaytonClient

def build_test_pickup_payload(*, destination_zip='45414'):
    return {
      'customerReferenceNumber':'TESTING','sendConfirmationTo':[],'sendReceiptTo':[],
      'details':[{'serviceOption':'None','destinationZip':destination_zip,'handlingUnits':1,'weight':100,'isHazardous':False,'accessorials':[],'comment':'Valhalla Freight API connectivity test','isFood':False,'isPoisonous':False,'isFreezable':False,'referenceNumbers':[],'dimensions':None}],
      'shipper':{'name':'Valhalla Freight API Test','address':{'address1':'6450 Poe Ave.','address2':'','city':'Dayton','name':None,'state':'OH','zip':'45414'}},
      'ready':'2026-08-25T08:00:00','close':'2026-08-25T16:00:00',
      'contact':{'name':'Valhalla Freight','phone':'8000000000','extension':None,'fax':None,'email':None},
      'requester':{'name':'Valhalla Freight','phone':'8000000000','extension':None,'fax':None,'email':None},
      'accessorials':[],'comments':'Valhalla Freight API test','pickupInstructions':None,'isTest':True,
    }

async def create(payload: dict, client: DaytonClient|None=None):
    return await (client or DaytonClient()).request('PUT','/api/Pickup',json=payload)
async def get(number: str, client: DaytonClient|None=None):
    return await (client or DaytonClient()).request('GET','/api/Pickup',params={'number':number})
async def cancel(number: str, client: DaytonClient|None=None):
    return await (client or DaytonClient()).request('DELETE','/api/Pickup/Cancel',params={'number':number})
