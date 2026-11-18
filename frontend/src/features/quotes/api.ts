import {api} from '../../services/api';
import type {MusePreview,MusePreviewSelection,MuseRateInput,QuoteRecord} from './types';
export const quoteApi={
  list:(status?:string)=>api<QuoteRecord[]>(`/quotes${status?`?status=${encodeURIComponent(status)}`:''}`),
  getMuseRate:(ref:string)=>api<MusePreview|null>(`/quotes/${encodeURIComponent(ref)}/muse-rate`),
  saveMuseRate:(ref:string,rate:MuseRateInput)=>api<MusePreview>(`/quotes/${encodeURIComponent(ref)}/muse-rate`,{method:'PUT',body:JSON.stringify(rate)}),
  removeMuseRate:(ref:string)=>api<MusePreview>(`/quotes/${encodeURIComponent(ref)}/muse-rate`,{method:'DELETE'}),
  selectMuseRate:(ref:string,revision:string)=>api<MusePreviewSelection>(`/quotes/${encodeURIComponent(ref)}/muse-rate/select`,{method:'POST',body:JSON.stringify({revision})}),
  get:(ref:string)=>api<QuoteRecord>(`/quotes/${encodeURIComponent(ref)}`),
  select:(ref:string,carrierId:number)=>api<QuoteRecord>(`/quotes/${encodeURIComponent(ref)}/select`,{method:'POST',body:JSON.stringify({carrier_id:carrierId})}),
  email:(ref:string,toEmail?:string)=>api<{ok:boolean;to:string;status:string}>(`/quotes/${encodeURIComponent(ref)}/email`,{method:'POST',body:JSON.stringify({to_email:toEmail||null})}),
  book:(quoteNumber:string,carrierId:number,payload:any={})=>api<any>('/shipments',{method:'POST',body:JSON.stringify({quote_number:quoteNumber,carrier_id:carrierId,option_index:0,...payload})})
};
