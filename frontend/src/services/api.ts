const API = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
export async function api<T>(path:string, init?:RequestInit):Promise<T>{
  const r=await fetch(`${API}${path}`,{...init,headers:{'Content-Type':'application/json',...(init?.headers||{})}});
  if(!r.ok) throw new Error((await r.json().catch(()=>({detail:r.statusText}))).detail || r.statusText);
  return r.json();
}
export {API};
