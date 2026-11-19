import {manufacturerSupport,clearManufacturerSupport} from '../services/manufacturerSupport';
import {useLocation} from 'react-router-dom';
import {createContext, useContext, useEffect, useRef, useState, type ReactNode} from 'react';
import {api, clearAccessToken, getAccessToken, setAccessToken} from '../services/api';

export type AuthUser={id:number;email:string;full_name:string;role:string;muse_partner_access?:boolean;actual_role?:string;customer_id?:number|null;active:boolean};
type AuthValue={user:AuthUser|null;loading:boolean;authError:string|null;retryAuth:()=>void;login:(email:string,password:string)=>Promise<AuthUser>;refreshUser:()=>Promise<void>;logout:()=>void};
function workspaceUser(user:AuthUser):AuthUser{const support=manufacturerSupport();return support&&user.role==='admin'?{...user,actual_role:'admin',role:'manufacturer_admin',customer_id:support.customer_id}:user}
const AuthContext=createContext<AuthValue|null>(null);

export function AuthProvider({children}:{children:ReactNode}){
  const location=useLocation();const lastInput=useRef(Date.now());
  const [user,setUser]=useState<AuthUser|null>(null);
  const [loading,setLoading]=useState(true);
  const [authError,setAuthError]=useState<string|null>(null);
  const [authAttempt,setAuthAttempt]=useState(0);
  useEffect(()=>{
    const token=getAccessToken();
    if(!token){setUser(null);setAuthError(null);setLoading(false);return;}
    const controller=new AbortController();
    let active=true;
    setLoading(true);
    setAuthError(null);
    // A stalled API must never leave the portal on its splash screen forever.
    const timeout=setTimeout(()=>controller.abort(),12000);
    api<AuthUser>('/auth/me',{signal:controller.signal})
      .then(value=>{if(active&&!controller.signal.aborted){setUser(workspaceUser(value));setAuthError(null)}})
      .catch(error=>{
        if(active){
          if(!getAccessToken()){setUser(null);setAuthError(null)}
          else setAuthError(error?.name==='AbortError'?'The server did not respond within 12 seconds.':'Unable to verify your session. The server may be temporarily unavailable.');
        }
      })
      .finally(()=>{clearTimeout(timeout);if(active)setLoading(false)});
    return()=>{active=false;clearTimeout(timeout);controller.abort()};
  },[authAttempt]);
  function retryAuth(){setAuthAttempt(value=>value+1)}
  useEffect(()=>{
    const active=()=>{lastInput.current=Date.now()};
    for(const name of ['pointerdown','keydown','mousemove','scroll'])window.addEventListener(name,active,{passive:true});
    return()=>{for(const name of ['pointerdown','keydown','mousemove','scroll'])window.removeEventListener(name,active)};
  },[]);
  useEffect(()=>{
    if(!user)return;lastInput.current=Date.now();
    api('/auth/presence',{method:'POST',body:JSON.stringify({path:location.pathname,event:'page_view'})}).catch(()=>{});
    const timer=setInterval(()=>{
      if(document.visibilityState!=='visible'||Date.now()-lastInput.current>120000)return;
      api('/auth/presence',{method:'POST',body:JSON.stringify({path:location.pathname,event:'heartbeat'})})
        .then(()=>api<AuthUser>('/auth/me')).then(value=>setUser(workspaceUser(value))).catch(()=>{if(!getAccessToken())setUser(null)});
    },60000);
    return()=>clearInterval(timer);
  },[user?.id,location.pathname]);
  async function login(email:string,password:string){
    const result=await api<{access_token:string;user:AuthUser}>('/auth/login',{method:'POST',body:JSON.stringify({email,password})});
    setAccessToken(result.access_token); setAuthError(null); setUser(result.user); return result.user;
  }
  async function refreshUser(){setUser(workspaceUser(await api<AuthUser>('/auth/me')))}
  function logout(){if(manufacturerSupport()){api('/admin/portal-access/end',{method:'POST'}).then(()=>{clearManufacturerSupport();window.close();window.location.assign('/admin/portal-access')}).catch(()=>window.dispatchEvent(new Event('manufacturer-support-expired')));return}api('/auth/logout',{method:'POST'}).catch(()=>{});clearAccessToken();setAuthError(null);setUser(null);}
  return <AuthContext.Provider value={{user,loading,authError,retryAuth,login,logout,refreshUser}}>{children}</AuthContext.Provider>;
}
export function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error('useAuth must be inside AuthProvider');return value;}
