import {manufacturerSupport} from './manufacturerSupport';
import {portalSession} from './portalSession';
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

export function getAccessToken(){ return localStorage.getItem('vf_access_token'); }
export function setAccessToken(token:string){ localStorage.setItem('vf_access_token', token); }
export function clearAccessToken(){ localStorage.removeItem('vf_access_token'); }

function errorMessage(payload:any, fallback:string){
  const detail=payload?.detail;
  if(typeof detail==='string') return detail;
  if(Array.isArray(detail)){
    return detail.map((item:any)=>{
      const field=Array.isArray(item?.loc) ? item.loc.filter((x:any)=>x!=='body').join('.') : '';
      const msg=item?.msg || 'Invalid value';
      return field ? `${field}: ${msg}` : msg;
    }).join(' · ');
  }
  if(detail && typeof detail==='object') return detail.message || JSON.stringify(detail);
  return payload?.message || fallback;
}

export async function api<T>(path:string, init?:RequestInit):Promise<T>{
  const token=getAccessToken();
  const support=manufacturerSupport();
  const portalCompany=support?String(support.customer_id):window.location.pathname==='/portal'?new URLSearchParams(window.location.search).get('company_id'):null;
  const r=await fetch(`${API}${path}`,{
    ...init,
    headers:{
      ...(!(init?.body instanceof FormData)?{'Content-Type':'application/json'}:{}),
      ...(token?{Authorization:`Bearer ${token}`}:{ }),
      ...(portalCompany?{'X-Company-Id':portalCompany,...(support?{'X-Portal-Session':support.portal_token,'X-Portal-Workspace':'manufacturer'}:portalSession(portalCompany)?.portal_token?{'X-Portal-Session':portalSession(portalCompany).portal_token}:{})}:{}),
      ...(init?.headers||{})
    }
  });
  if(r.status===401 && path!=='/auth/login') clearAccessToken();
  if(support&&r.headers.get('X-Portal-Session-Invalid'))window.dispatchEvent(new Event('manufacturer-support-expired'));
  if(!support&&r.status===403&&portalCompany&&path.startsWith('/portal'))window.dispatchEvent(new Event('portal-session-expired'));
  if(!r.ok){
    const payload=await r.json().catch(()=>null);
    const error= new Error(errorMessage(payload,r.statusText)) as Error & {details?:any[]};
    error.details=Array.isArray(payload?.detail)?payload.detail:[];
    throw error;
  }
  return r.json();
}
export async function apiBlob(path:string):Promise<Blob>{
  const token=getAccessToken();
  const support=manufacturerSupport();
  const portalCompany=support?String(support.customer_id):window.location.pathname==='/portal'?new URLSearchParams(window.location.search).get('company_id'):null;
  const r=await fetch(`${API}${path}`,{headers:{...(token?{Authorization:`Bearer ${token}`}:{ }),...(portalCompany?{'X-Company-Id':portalCompany,...(support?{'X-Portal-Session':support.portal_token,'X-Portal-Workspace':'manufacturer'}:portalSession(portalCompany)?.portal_token?{'X-Portal-Session':portalSession(portalCompany).portal_token}:{})}:{})}});
  if(support&&r.headers.get('X-Portal-Session-Invalid'))window.dispatchEvent(new Event('manufacturer-support-expired'));
  if(!support&&r.status===403&&portalCompany)window.dispatchEvent(new Event('portal-session-expired'));
  if(!r.ok) throw new Error(r.statusText);
  return r.blob();
}
export {API};
