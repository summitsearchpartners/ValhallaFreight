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
  const r=await fetch(`${API}${path}`,{
    ...init,
    headers:{
      'Content-Type':'application/json',
      ...(token?{Authorization:`Bearer ${token}`}:{ }),
      ...(init?.headers||{})
    }
  });
  if(r.status===401 && path!=='/auth/login') clearAccessToken();
  if(!r.ok){
    const payload=await r.json().catch(()=>null);
    throw new Error(errorMessage(payload,r.statusText));
  }
  return r.json();
}
export {API};
