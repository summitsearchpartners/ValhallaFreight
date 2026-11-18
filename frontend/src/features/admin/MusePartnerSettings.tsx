import {useEffect,useState} from 'react';
import {api} from '../../services/api';
import {Card} from '../../components/UI';

export default function MusePartnerSettings({companies,saved}:{companies:{id:number;name:string}[];saved:()=>Promise<void>}){
 const [current,setCurrent]=useState<string|null>(null),[selected,setSelected]=useState(''),[busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
 useEffect(()=>{api<any>('/admin/muse-partner').then(v=>{setCurrent(String(v.company_id||''));setSelected(String(v.company_id||''))}).catch(e=>setError(e.message))},[]);
 return <Card className="musePartnerDesignation"><details><summary>Muse Freight partner access</summary><p>Only Broker Admins assigned to this company can open the Muse Portal and review opted-in manufacturers. Other broker companies retain their normal workspace access.</p>
 <form className="museAccountFields" onSubmit={async e=>{e.preventDefault();setBusy(true);setError('');setMessage('');try{const v=await api<any>('/admin/muse-partner',{method:'PUT',body:JSON.stringify({company_id:selected?Number(selected):null})});setCurrent(String(v.company_id||''));await saved();setMessage('Muse partner company saved. Refresh the broker session to update its menu.')}catch(e:any){setError(e.message)}finally{setBusy(false)}}}>
 <label>Muse Freight company<select aria-label="Muse Freight company" value={selected} disabled={busy||current===null} onChange={e=>setSelected(e.target.value)}><option value="">No partner company assigned</option>{companies.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>
 <button className="btn primary" disabled={busy||current===null||current===selected}>Save Muse partner company</button></form>
 {message&&<p role="status">{message}</p>}{error&&<p className="inlineError" role="alert">{error}</p>}</details></Card>
}
