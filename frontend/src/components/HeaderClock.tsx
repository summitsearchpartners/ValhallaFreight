import {useEffect,useState} from 'react';
import {Clock3} from 'lucide-react';
import {usePreferences} from '../context/PreferencesContext';
import {formatDateTime,formatTime} from '../shared/display/preferences';
export default function HeaderClock(){const {preferences}=usePreferences();const [now,setNow]=useState(()=>new Date());useEffect(()=>{if(!preferences.show_clock)return;setNow(new Date());const timer=setInterval(()=>setNow(new Date()),preferences.show_seconds?1000:30000);return()=>clearInterval(timer)},[preferences.show_clock,preferences.show_seconds]);return preferences.show_clock?<div className="headerClock" title={`${formatDateTime(now)} · ${preferences.timezone==='local'?'Device timezone':preferences.timezone}`}><Clock3 size={14}/><time>{formatTime(now)}</time></div>:null}
