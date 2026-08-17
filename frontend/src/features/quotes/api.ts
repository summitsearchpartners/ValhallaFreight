import {api} from '../../services/api';
import type {QuoteRecord} from './types';
export const quoteApi={
  list:(status?:string)=>api<QuoteRecord[]>(`/quotes${status?`?status=${encodeURIComponent(status)}`:''}`),
  get:(ref:string)=>api<QuoteRecord>(`/quotes/${encodeURIComponent(ref)}`),
  select:(ref:string,carrierId:number)=>api<QuoteRecord>(`/quotes/${encodeURIComponent(ref)}/select`,{method:'POST',body:JSON.stringify({carrier_id:carrierId})}),
  book:(quoteNumber:string,carrierId:number,scheduledPickupAt?:string,requestedDeliveryAt?:string)=>api<any>('/shipments',{method:'POST',body:JSON.stringify({quote_number:quoteNumber,carrier_id:carrierId,option_index:0,scheduled_pickup_at:scheduledPickupAt||null,requested_delivery_at:requestedDeliveryAt||null})})
};
