import {api,API,getAccessToken} from '../../services/api';
import type {CarrierDetail,CarrierSummary} from './types';
export const carrierApi={
  list:()=>api<CarrierSummary[]>('/carrier-360'),
  detail:(id:number|string)=>api<CarrierDetail>(`/carrier-360/${id}`),
  create:(payload:any)=>api<any>('/carrier-360',{method:'POST',body:JSON.stringify(payload)}),
  update:(id:number|string,payload:any)=>api<any>(`/carrier-360/${id}`,{method:'PATCH',body:JSON.stringify(payload)}),
  add:(id:number|string,resource:string,payload:any)=>api<any>(`/carrier-360/${id}/${resource}`,{method:'POST',body:JSON.stringify(payload)}),
  edit:(id:number|string,resource:string,rowId:number,payload:any)=>api<any>(`/carrier-360/${id}/${resource}/${rowId}`,{method:'PATCH',body:JSON.stringify(payload)}),
  remove:(id:number|string,resource:string,rowId:number)=>api<any>(`/carrier-360/${id}/${resource}/${rowId}`,{method:'DELETE'}),

  uploadComplianceDocument:async(id:number|string,rowId:number,file:File)=>{
    const body=new FormData();body.append('file',file);const token=getAccessToken();
    const r=await fetch(`${API}/carrier-360/${id}/compliance/${rowId}/document`,{method:'POST',body,headers:{...(token?{Authorization:`Bearer ${token}`}:{})}});
    if(!r.ok){const payload=await r.json().catch(()=>null);throw new Error(payload?.detail||r.statusText)}return r.json();
  },
  complianceDocumentBlob:async(id:number|string,rowId:number)=>{
    const token=getAccessToken();const r=await fetch(`${API}/carrier-360/${id}/compliance/${rowId}/document`,{headers:{...(token?{Authorization:`Bearer ${token}`}:{})}});
    if(!r.ok){const payload=await r.json().catch(()=>null);throw new Error(payload?.detail||r.statusText)}return r.blob();
  },
};
