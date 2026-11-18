import {createContext,useContext,useEffect,useState,type ReactNode} from 'react';
import {useAuth} from './AuthContext';
import {api} from '../services/api';
export type Workspace={company_name:string;logo_data:string;show_pricing:boolean};
const empty:Workspace={company_name:'',logo_data:'',show_pricing:false};
const Context=createContext<{workspace:Workspace;loading:boolean}>({workspace:empty,loading:true});
export function WorkspaceProvider({children}:{children:ReactNode}){
 const {user}=useAuth();const [workspace,setWorkspace]=useState<Workspace>(empty),[loading,setLoading]=useState(true);
 useEffect(()=>{let active=true;let request=0;setWorkspace(empty);setLoading(true);
  if(!user||!['admin','broker','broker_admin','manufacturer_admin','manufacturer'].includes(user.role)){setLoading(false);return}
  const load=async()=>{const id=++request;try{const row=await api<Workspace>('/workspace/settings');if(active&&id===request)setWorkspace(row)}catch{}finally{if(active&&id===request)setLoading(false)}};
  load();const timer=setInterval(load,30000);window.addEventListener('workspace-updated',load);window.addEventListener('focus',load);
  return()=>{active=false;clearInterval(timer);window.removeEventListener('workspace-updated',load);window.removeEventListener('focus',load)};
 },[user?.id,user?.role,user?.customer_id]);
 return <Context.Provider value={{workspace,loading}}>{children}</Context.Provider>
}
export function useWorkspace(){return useContext(Context)}
