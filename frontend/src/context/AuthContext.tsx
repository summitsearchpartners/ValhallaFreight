import {createContext, useContext, useEffect, useState, type ReactNode} from 'react';
import {api, clearAccessToken, getAccessToken, setAccessToken} from '../services/api';

export type AuthUser={id:number;email:string;full_name:string;role:string;active:boolean};
type AuthValue={user:AuthUser|null;loading:boolean;login:(email:string,password:string)=>Promise<void>;logout:()=>void};
const AuthContext=createContext<AuthValue|null>(null);

export function AuthProvider({children}:{children:ReactNode}){
  const [user,setUser]=useState<AuthUser|null>(null);
  const [loading,setLoading]=useState(true);
  useEffect(()=>{
    const token=getAccessToken();
    if(!token){setLoading(false);return;}
    api<AuthUser>('/auth/me').then(setUser).catch(()=>clearAccessToken()).finally(()=>setLoading(false));
  },[]);
  async function login(email:string,password:string){
    const result=await api<{access_token:string;user:AuthUser}>('/auth/login',{method:'POST',body:JSON.stringify({email,password})});
    setAccessToken(result.access_token); setUser(result.user);
  }
  function logout(){clearAccessToken();setUser(null);}
  return <AuthContext.Provider value={{user,loading,login,logout}}>{children}</AuthContext.Provider>;
}
export function useAuth(){const value=useContext(AuthContext);if(!value)throw new Error('useAuth must be inside AuthProvider');return value;}
