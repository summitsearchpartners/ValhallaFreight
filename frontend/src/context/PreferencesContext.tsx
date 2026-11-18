import {createContext,useContext,useEffect,useRef,useState,type ReactNode} from 'react';
import {useAuth} from './AuthContext';
import {api} from '../services/api';
import {configureDisplay,defaultPreferences,type DisplayPreferences} from '../shared/display/preferences';

type Value={preferences:DisplayPreferences;loading:boolean;error:string;applyPreferences:(p:DisplayPreferences)=>void;savePreferences:(p:DisplayPreferences)=>Promise<void>};
const Context=createContext<Value|null>(null);
export function PreferencesProvider({children}:{children:ReactNode}){
 const {user}=useAuth();const [preferences,setPreferences]=useState<DisplayPreferences>({...defaultPreferences}),[loading,setLoading]=useState(true),[error,setError]=useState('');const identity=useRef(user?.id);identity.current=user?.id;
 useEffect(()=>{let active=true;setError('');configureDisplay(defaultPreferences);setPreferences({...defaultPreferences});setLoading(Boolean(user));if(!user)return;
  api<DisplayPreferences>('/workspace/preferences').then(p=>{if(active){configureDisplay(p);setPreferences(p)}}).catch(e=>{if(active)setError(e.message)}).finally(()=>{if(active)setLoading(false)});
  return()=>{active=false};
 },[user?.id]);
 useEffect(()=>{const query=window.matchMedia('(prefers-color-scheme: dark)');const apply=()=>{document.documentElement.dataset.theme=preferences.theme==='system'?(query.matches?'dark':'light'):preferences.theme;document.documentElement.dataset.density=preferences.density};apply();query.addEventListener('change',apply);return()=>query.removeEventListener('change',apply)},[preferences.theme,preferences.density]);
 function applyPreferences(p:DisplayPreferences){configureDisplay(p);setPreferences(p);setError('')}
 async function savePreferences(p:DisplayPreferences){const id=user?.id;const saved=await api<DisplayPreferences>('/workspace/preferences',{method:'PUT',body:JSON.stringify(p)});if(identity.current===id){configureDisplay(saved);setPreferences(saved);setError('')}}
 return <Context.Provider value={{preferences,loading,error,savePreferences,applyPreferences}}>{children}</Context.Provider>;
}
export function usePreferences(){const value=useContext(Context);if(!value)throw Error('PreferencesProvider required');return value}
