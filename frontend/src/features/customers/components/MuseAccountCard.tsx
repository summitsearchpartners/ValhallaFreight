import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {Card} from '../../../components/UI';
import {api} from '../../../services/api';

export default function MuseAccountCard({customerId}:{customerId:number}){
 const [account,setAccount]=useState<any>(null),[enabled,setEnabled]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const path=`/muse/enrollment/${customerId}`;
 useEffect(()=>{const c=new AbortController();api<any>(path,{signal:c.signal}).then(v=>{setAccount(v);setEnabled(v.enabled)}).catch(e=>{if(!c.signal.aborted)setError(e.message)});return()=>c.abort()},[path]);
 return <Card className="museAccountCard"><h3>Muse Freight access</h3><p>Only Valhalla TMS Super Admin can enable Muse rates for this manufacturer and its customer accounts. Muse approves credit applications separately.</p>
 {error&&<p className="inlineError" role="alert">{error}</p>}
 {account&&<form onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');try{const v=await api<any>(path+'/opt-in',{method:'PUT',body:JSON.stringify({enabled})});setAccount(v);setMessage('Muse access saved.')}catch(e:any){setError(e.message)}finally{setBusy(false)}}}>
 <label className="museCheck"><input type="checkbox" checked={enabled} disabled={busy} onChange={e=>setEnabled(e.target.checked)}/>Offer Muse Freight rates to this manufacturer</label>
 <p>Credit application: <b>{account.application_status.replaceAll('_',' ')}</b></p>
 <div className="museRateFooter"><button className="btn primary" disabled={busy||enabled===account.enabled}>Save Muse access</button><Link className="btn secondary" to="/muse">Open Muse Portal</Link></div>
 {message&&<p role="status">{message}</p>}</form>}</Card>
}
