import {useEffect,useRef,useState} from 'react';
import {Link,useLocation} from 'react-router-dom';
import {ShieldCheck,AlertTriangle} from 'lucide-react';
import {api} from '../../services/api';
import {clearPortalSession,portalSession,savePortalSession} from '../../services/portalSession';
import CustomerPortalApp from './CustomerPortalApp';
export default function PortalSupportGate(){
 const location=useLocation(),company=new URLSearchParams(location.search).get('company_id')||'';
 const ticket=useRef(new URLSearchParams(location.hash.slice(1)).get('access_ticket'));
 const redemption=useRef<Promise<{portal_token:string;customer_id:number;expires_at:string}>|null>(null);
 const [ready,setReady]=useState(Boolean(portalSession(company))),[error,setError]=useState(''),[loading,setLoading]=useState(Boolean(ticket.current));
 useEffect(()=>{let active=true;
  if(ticket.current){
   window.history.replaceState(null,'',location.pathname+location.search);
   if(!redemption.current)redemption.current=api('/admin/portal-access/redeem',{method:'POST',body:JSON.stringify({ticket:ticket.current})});
   redemption.current.then(result=>{if(!active)return;if(String(result.customer_id)!==company)throw Error('Portal selection mismatch. Verify again in Portal Access.');savePortalSession(company,result);setReady(true)}).catch(e=>{if(active){clearPortalSession(company);setError(e.message);setReady(false)}}).finally(()=>{if(active)setLoading(false)});
  }
  const expired=()=>{clearPortalSession(company);setReady(false);setError('Your support session ended or expired. Verify again in Portal Access.')};window.addEventListener('portal-session-expired',expired);const timer=setInterval(()=>{const session=portalSession(company);if(session?.expires_at&&new Date(session.expires_at.endsWith('Z')?session.expires_at:session.expires_at+'Z').getTime()<=Date.now())expired()},10000);
  return()=>{active=false;clearInterval(timer);window.removeEventListener('portal-session-expired',expired)};
 },[company]);
 if(loading)return <div className="supportAccessState"><ShieldCheck size={32}/><h1>Opening verified customer portal…</h1><p>Your Valhalla Freight Admin identity remains active.</p></div>;
 if(!ready)return <div className="supportAccessState"><AlertTriangle size={32}/><h1>Portal verification required</h1><p>{error||'Select a customer and verify your administrator credentials to start a support session.'}</p><Link className="btn primary" to={`/admin/portal-access?customer_id=${company}`}>Go to Portal Access</Link></div>;
 return <CustomerPortalApp/>;
}
