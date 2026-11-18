from __future__ import annotations
from app.integrations.base import CarrierAdapter, register_carrier
from .client import DaytonClient
from .models import DAYTON_CAPABILITIES
from .bol import create_standard
from decimal import Decimal, ROUND_CEILING

class DaytonAdapter(CarrierAdapter):
    code='DAFG'; name='Dayton Freight Lines'; capabilities=tuple(DAYTON_CAPABILITIES)
    def __init__(self, db=None): self.db=db
    def client(self): return DaytonClient.from_db(self.db) if self.db is not None else DaytonClient()
    def configured(self): return self.client().has_credentials
    async def book_shipment(self, shipment, db=None):
        client=self.client()
        if not client.has_credentials:
            raise ValueError('Dayton credentials are not configured')
        origin=shipment.origin or {}; destination=shipment.destination or {}; units=shipment.handling_units or []
        from app.integrations.service import get_dayton_connection
        env=(get_dayton_connection(self.db).environment if self.db is not None else 'sandbox')
        is_test=str(env or 'sandbox').lower()!='production'
        def digits(v): return ''.join(ch for ch in str(v or '') if ch.isdigit())[:10]
        def contact(a): return {'name':(a.get('contact_name') or '')[:30] or None,'phone':digits(a.get('phone')) or None,'email':a.get('email') or None}
        def location(a,account=None): return {'account':account,'locationId':str(a.get('location_id') or '') or None,'name':str(a.get('name') or shipment.customer.name if getattr(shipment,'customer',None) else 'Customer')[:30],'address1':str(a.get('address1') or '')[:30],'address2':str(a.get('address2') or '')[:30] or None,'city':str(a.get('city') or '')[:30],'stateProvince':str(a.get('state') or '')[:2],'postalCode':str(a.get('postal_code') or ''),'country':'USA','contact':contact(a)}
        handling=[]
        total_weight=0; total_count=0
        for i,u in enumerate(units):
            count=int(u.get('quantity') or 1);weight=int((Decimal(str(u.get('weight_lbs') or 0))*count).to_integral_value(rounding=ROUND_CEILING));total_weight+=weight;total_count+=count
            line={'classification':str(u.get('freight_class') or '70'),'description':str(shipment.commodity_description or 'General freight')[:255],'hazardous':bool(shipment.hazmat_emergency_contact),'packagingType':str(u.get('type') or shipment.package_type or 'PALLET').upper(),'pieces':count,'weight':weight,'nmfc':str(shipment.nmfc_number or '')[:10] or None}
            handling.append({'count':count,'type':str(u.get('type') or shipment.package_type or 'PALLET').upper(),'weight':weight,'length':int(float(u.get('length_in') or 0)) or None,'width':int(float(u.get('width_in') or 0)) or None,'height':int(float(u.get('height_in') or 0)) or None,'stackable':False,'lineItems':[line]})
        pickup=shipment.scheduled_pickup_at or shipment.created_at
        pay_terms={'Prepaid':'PREPAID','Collect':'COLLECT','Third Party':'THIRD PARTY','Third Party Prepaid':'THIRD PARTY','Third Party Collect':'THIRD PARTY'}.get(getattr(shipment,'payment_terms','Prepaid'),'PREPAID')
        payload={'bol':{'requestedPickupDate':pickup.isoformat(),'function':'CREATE','isTest':is_test,'requestorRole':'THIRD PARTY','specialInstructions':origin.get('instructions') or destination.get('instructions')},'version':'2.1.0','referenceNumbers':{'pro':shipment.pro_number,'quoteId':None,'shipmentId':shipment.shipment_number,'bol':[shipment.bol_number] if shipment.bol_number else None,'po':[{'number':shipment.po_number,'pieces':int(shipment.package_count or total_count or 1),'weight':total_weight,'palletized':True,'additionalShipperInfo':shipment.customer_reference}] if shipment.po_number else None},'payment':{'terms':pay_terms},'commodities':{'handlingUnits':handling,'lineItemLayout':'Nested'},'shipmentTotals':{'declaredValue':float(shipment.declared_value or 0),'grossWeight':total_weight,'handlingUnits':total_count,'dimensionsUnit':'Inches','weightUnit':'Pounds','currency':'USD'},'accessorials':{'codes':[]},'origin':location(origin,client.account or None),'destination':location(destination,None),'billTo':location(origin,client.account or None)}
        raw=await create_standard(payload,client)
        outcome=(raw or {}).get('messageStatus') or {}
        if str(outcome.get('status') or '').upper() not in {'PASS','WARNING'}:
            raise ValueError('Dayton did not accept the electronic BOL: '+str(outcome.get('message') or 'No acceptance status returned'))
        refs=(raw or {}).get('referenceNumbers') or {}
        return {'is_test':is_test,'pro_number':refs.get('pro'),'provider_reference':refs.get('shipmentConfirmationNumber'),'message_status':(raw or {}).get('messageStatus'),'raw':raw}

    async def test_connection(self):
        client=self.client()
        if not client.has_credentials:
            return {'ok':False,'configured':False,'message':'Adapter is installed and ready. Save Dayton credentials in the Integration Hub to enable live API calls.'}
        accounts=await client.request('GET','/api/Accounts')
        return {'ok':True,'configured':True,'message':'Authenticated successfully with Dayton Freight.','accounts':accounts.get('accounts',[]) if isinstance(accounts,dict) else []}

register_carrier('DAFG', DaytonAdapter)
