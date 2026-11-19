import {formatDateTime} from '../../shared/display/preferences';
import {useEffect,useRef,useState,type ReactNode} from 'react';
import {ShieldCheck} from 'lucide-react';
import {api} from '../../services/api';
import {manufacturerSupport,saveManufacturerSupport,clearManufacturerSupport,type ManufacturerSupport} from '../../services/manufacturerSupport';

// Finish one-time verification before mounting any auth/workspace/data providers.
export default function ManufacturerSupportWindow({children}:{children:ReactNode}){
 const entry=useRef(window.location.pathname==='/manufacturer-support');
 const company=useRef(new URLSearchParams(window.location.search).get('company_id')||'');
 const ticket=useRef(new URLSearchParams(window.location.hash.slice(1)).get('access_ticket'));
 const redemption=useRef<Promise<ManufacturerSupport>|null>(null);
 const [ready,setReady]=useState(!entry.current),[error,setError]=useState('');
 useEffect(()=>{let active=true;
  if(entry.current){
   window.history.replaceState(null,'','/manufacturer-support?company_id='+encodeURIComponent(company.current));
   if(!ticket.current){setError('Select a manufacturer and verify your administrator credentials in Portal Access.');setReady(false)}
   else{
    if(!redemption.current)redemption.current=api<ManufacturerSupport>('/admin/portal-access/redeem',{method:'POST',headers:{'X-Company-Id':company.current},body:JSON.stringify({ticket:ticket.current})});
    redemption.current.then(value=>{if(!active)return;if(value.portal_type!=='manufacturer'||String(value.customer_id)!==company.current)throw Error('This launch is not for the selected manufacturer workspace.');saveManufacturerSupport(value);window.history.replaceState(null,'','/');setReady(true)}).catch(e=>{if(active){clearManufacturerSupport();setError(e.message);setReady(false)}});
   }
  }
  const expired=()=>{clearManufacturerSupport();setError('Your manufacturer support session ended or expired. Verify again in Portal Access.');setReady(false)};
  window.addEventListener('manufacturer-support-expired',expired);
  const timer=setInterval(()=>{const session=manufacturerSupport();if(session&&new Date(session.expires_at.endsWith('Z')?session.expires_at:session.expires_at+'Z').getTime()<=Date.now())expired()},5000);
  return()=>{active=false;clearInterval(timer);window.removeEventListener('manufacturer-support-expired',expired)};
 },[]);
 function returnToAdmin(){clearManufacturerSupport();window.location.assign('/admin/portal-access')}
 if(!ready)return <div className="supportAccessState"><ShieldCheck size={32}/><h1>{error?'Manufacturer verification required':'Opening manufacturer workspace…'}</h1><p>{error||'Preparing the company Command Center under your Valhalla TMS Admin identity.'}</p>{error&&<button className="btn primary" onClick={returnToAdmin}>Go to Portal Access</button>}</div>;
 return <>{children}</>;
}

export function ManufacturerSupportBanner(){
 const session=manufacturerSupport();const [busy,setBusy]=useState(false),[error,setError]=useState('');
 if(!session)return null;
 async function end(close:boolean){setBusy(true);setError('');try{await api('/admin/portal-access/end',{method:'POST'});clearManufacturerSupport();if(close)window.close();window.location.assign('/admin/portal-access')}catch(e:any){setError(e.message)}finally{setBusy(false)}}
 return <div className="manufacturerSupportBanner"><div><b>Valhalla TMS Admin · Super User</b><span>Manufacturer workspace · {session.company_name} · {error||`Expires ${formatDateTime(session.expires_at.endsWith('Z')?session.expires_at:session.expires_at+'Z')}`}</span></div><div><button disabled={busy} onClick={()=>end(false)}>Switch portal</button><button disabled={busy} onClick={()=>end(true)}>{busy?'Ending…':'End support session'}</button></div></div>;
}
