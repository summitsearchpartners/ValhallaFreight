import {useEffect,useRef,useState} from 'react';
import {Link,useSearchParams} from 'react-router-dom';
import {useAuth} from '../../context/AuthContext';
import {api,apiBlob} from '../../services/api';
import {PdfViewer} from './MuseCreditPage';
import {printBOL} from '../shipments/printDocuments';

export default function MusePortal(){
 const {user,logout}=useAuth();const [search]=useSearchParams();
 const [manufacturers,setManufacturers]=useState<any[]>([]),[quotes,setQuotes]=useState<any[]>([]),[bookings,setBookings]=useState<any[]>([]);
 const [tab,setTab]=useState('manufacturers'),[profile,setProfile]=useState<any>(null),[rateQuote,setRateQuote]=useState<any>(null),[confirmBooking,setConfirmBooking]=useState<any>(null);
 const [note,setNote]=useState(''),[carrier,setCarrier]=useState(''),[price,setPrice]=useState(''),[cost,setCost]=useState(''),[transit,setTransit]=useState(''),[reference,setReference]=useState(''),[pro,setPro]=useState('');
 const [busy,setBusy]=useState(false),[error,setError]=useState(''),[pdf,setPdf]=useState(''),[message,setMessage]=useState('');
 async function load(){const [m,q,b]=await Promise.all([api<any[]>('/muse/manufacturers'),api<any[]>('/muse/quotes'),api<any[]>('/muse/bookings')]);setManufacturers(m);setQuotes(q);setBookings(b)}
 useEffect(()=>{load().catch(e=>setError(e.message));const t=setInterval(()=>load().catch(()=>{}),30000);return()=>clearInterval(t)},[]);
 async function openProfile(id:number){setProfile(await api(`/muse/manufacturers/${id}`));setNote('')}
 useEffect(()=>{const id=Number(search.get('manufacturer'));if(id)openProfile(id).catch(e=>setError(e.message))},[search]);
 async function action(work:()=>Promise<void>){setBusy(true);setError('');setMessage('');try{await work();await load()}catch(e:any){setError(e.message)}finally{setBusy(false)}}
 const pending=manufacturers.filter(m=>m.application_status==='pending').length;
 return <div className="musePortal"><aside><div className="musePortalBrand"><img src="/muse-freight-logo.png" alt="Muse Freight"/><h2>Muse Partner Portal</h2></div>
 {['manufacturers','quotes','bookings'].map(t=><button key={t} className={tab===t?'active':''} onClick={()=>setTab(t)}>{t==='manufacturers'?'Manufacturers':t==='quotes'?'Muse quotes':'Shipment bookings'}{t==='manufacturers'&&pending>0?<b>{pending}</b>:t==='bookings'&&bookings.some(b=>b.status==='requested')?<b>{bookings.filter(b=>b.status==='requested').length}</b>:null}</button>)}
 <div className="musePortalUser"><b>{user?.full_name}</b><span>{user?.role==='broker_admin'?'Broker Admin · Muse Freight':'Muse Freight Admin'}</span>{['admin','broker_admin'].includes(user?.role||'')&&<Link to="/">{user?.role==='admin'?'Return to Valhalla Freight':'Return to broker workspace'}</Link>}<button onClick={logout}>Sign out</button></div></aside>
 <main><div className="musePortalHead"><div><span>MUSE FREIGHT</span><h1>{tab==='manufacturers'?'Manufacturer accounts':tab==='quotes'?'Muse rate workspace':'Shipment booking requests'}</h1><p>{pending} credit application{pending===1?'':'s'} awaiting review</p></div><button className="btn secondary" onClick={()=>action(load)}>Refresh</button></div>
 {error&&<p role="alert" className="inlineError">{error}</p>}{message&&<p role="status">{message}</p>}
 <div className="musePortalList">
 {tab==='manufacturers'&&(manufacturers.length?manufacturers.map(m=><button className="musePortalRow" key={m.manufacturer_id} onClick={()=>openProfile(m.manufacturer_id).catch(e=>setError(e.message))}><div><b>{m.manufacturer_name}</b><span>Opted in to Muse rates</span></div><strong className={m.can_book?'approved':''}>{m.application_status.replaceAll('_',' ')}</strong><span>Open profile →</span></button>):<p>No manufacturers have been opted in by Valhalla Super Admin.</p>)}
 {tab==='quotes'&&(quotes.length?quotes.map(q=><div className="musePortalRow" key={q.id}><div><b>{q.quote_number}</b><span>{q.manufacturer_name} · {q.origin_zip} → {q.destination_zip}</span></div><strong>{q.muse_preview.rate?`$${Number(q.muse_preview.rate.customer_price).toFixed(2)}`:'No Muse price yet'}</strong><button className="btn secondary" onClick={()=>{const r=q.muse_preview.rate;setRateQuote(q);setCarrier(String(r?.carrier_id||''));setPrice(String(r?.customer_price||''));setCost(String(r?.carrier_cost??''));setTransit(String(r?.transit_days||''))}}>Manage rate</button></div>):<p>No active quotes from opted-in manufacturers. Manufacturer carrier options remain available in their own portal.</p>)}
 {tab==='bookings'&&(bookings.length?bookings.map(b=><div className="musePortalRow" key={b.id}><div><b>{b.shipment_number}</b><span>{b.manufacturer_name} · {b.carrier_name}</span><span>BOL {b.bol_number} · {b.origin.city}, {b.origin.state} → {b.destination.city}, {b.destination.state}</span><span>{b.status}{b.pro_number?` · PRO ${b.pro_number}`:''}</span></div>
 <div className="museRateFooter"><button className="btn secondary" onClick={()=>action(async()=>{const s=await api<any>(`/muse/bookings/${b.id}/detail`);printBOL(s)})}>View BOL</button>
 {b.status==='requested'&&<button className="btn primary" onClick={()=>{setConfirmBooking(b);setReference('');setPro('')}}>Confirm booking</button>}</div></div>):<p>No Muse shipment booking requests yet.</p>)}
 </div></main>
 {profile&&<Modal title={profile.manufacturer_name} close={()=>setProfile(null)} busy={busy} error={error}><p>Application status: <b>{profile.application_status}</b> · Booking {profile.can_book?'enabled':'not approved'}</p>
 {profile.applications.length?profile.applications.map((a:any)=><section className="museApplicationReview" key={a.id}><b>Application #{a.id} · {a.status}</b><p>Submitted {new Date(a.created_at+'Z').toLocaleString()}</p><button className="btn secondary" onClick={()=>apiBlob(`/muse/applications/${a.id}/pdf`).then(b=>setPdf(URL.createObjectURL(b))).catch(e=>setError(e.message))}>View completed application</button>
 {a.status==='pending'&&<><label>Review note<textarea maxLength={1000} value={note} onChange={e=>setNote(e.target.value)}/></label><div className="museRateFooter"><button className="btn secondary" disabled={busy||!note.trim()} onClick={()=>action(async()=>{await api(`/muse/applications/${a.id}/decision`,{method:'POST',body:JSON.stringify({decision:'declined',note})});await openProfile(profile.manufacturer_id)})}>Request a new application</button><button className="btn primary" disabled={busy} onClick={()=>action(async()=>{await api(`/muse/applications/${a.id}/decision`,{method:'POST',body:JSON.stringify({decision:'approved',note})});await openProfile(profile.manufacturer_id)})}>Approve booking access</button></div></>}
 {a.decision_note&&<p>{a.decision_note}</p>}</section>):<p>This manufacturer has not submitted a credit application.</p>}</Modal>}
 {rateQuote&&<Modal title={rateQuote.quote_number+' · Muse rate'} close={()=>setRateQuote(null)} busy={busy} error={error}>
 <p>{rateQuote.manufacturer_name} · {rateQuote.origin_zip} → {rateQuote.destination_zip}</p>
 <div className="museFreightSummary">{rateQuote.handling_units.map((u:any,i:number)=><p key={i}>{u.quantity} × {u.weight_lbs} lb · {u.length_in} × {u.width_in} × {u.height_in} in · Class {u.freight_class}</p>)}<p>Accessorials: {rateQuote.accessorials.join(', ')||'None'}</p></div>
 <form onSubmit={e=>{e.preventDefault();action(async()=>{await api(`/muse/quotes/${rateQuote.id}/rate`,{method:'PUT',body:JSON.stringify({carrier_id:Number(carrier),carrier_name:rateQuote.carriers.find((c:any)=>c.id===Number(carrier))?.name,customer_price:price,carrier_cost:cost,transit_days:Number(transit)})});setRateQuote(null);setMessage('Muse rate published.')})}}>
 <label>Carrier<select aria-label="Carrier" required value={carrier} onChange={e=>setCarrier(e.target.value)}><option value="">Choose a carrier</option>{rateQuote.carriers.map((c:any)=><option value={c.id} key={c.id}>{c.name}</option>)}</select></label>
 <label>Customer price (USD)<input type="number" step=".01" min=".01" required value={price} onChange={e=>setPrice(e.target.value)}/></label>
 <label>Muse carrier cost (USD)<input type="number" step=".01" min="0" required value={cost} onChange={e=>setCost(e.target.value)}/></label>
 <label>Transit (business days)<input type="number" min="1" max="90" required value={transit} onChange={e=>setTransit(e.target.value)}/></label>
 <p>Use the price and service details actually supplied by Muse. No live Muse API is connected.</p><div className="museRateFooter">{rateQuote.muse_preview.rate&&<button type="button" className="btn secondary" disabled={busy} onClick={()=>action(async()=>{await api(`/muse/quotes/${rateQuote.id}/rate`,{method:'DELETE'});setRateQuote(null)})}>Withdraw rate</button>}<button className="btn primary" disabled={busy}>Publish Muse rate</button></div></form></Modal>}
 {confirmBooking&&<Modal title={'Confirm '+confirmBooking.shipment_number} close={()=>setConfirmBooking(null)} busy={busy} error={error}><p>Confirm only after arranging the shipment with the actual carrier.</p><form onSubmit={e=>{e.preventDefault();action(async()=>{await api(`/muse/bookings/${confirmBooking.id}/confirm`,{method:'POST',body:JSON.stringify({provider_reference:reference,pro_number:pro})});setConfirmBooking(null);setMessage('Muse booking confirmed.')})}}>
 <label>Booking / pickup reference<input required maxLength={120} value={reference} onChange={e=>setReference(e.target.value)}/></label><label>Carrier PRO number<input required maxLength={60} value={pro} onChange={e=>setPro(e.target.value)}/></label><button className="btn primary" disabled={busy}>Confirm carrier booking</button></form></Modal>}
 {pdf&&<PdfViewer url={pdf} close={()=>setPdf('')}/>}
 </div>
}
function Modal({title,close,busy,error,children}:{title:string;close:()=>void;busy:boolean;error:string;children:React.ReactNode}){
 const dialog=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const node=dialog.current;if(node&&!node.open)node.showModal();return()=>{if(node?.open)node.close()}},[]);
 return <dialog ref={dialog} className="musePortalModal" aria-label={title} onCancel={e=>{e.preventDefault();if(!busy)close()}}>
 <div className="museDialogHead"><h2>{title}</h2><button type="button" className="btn secondary" disabled={busy} onClick={close} autoFocus>Close</button></div>
 {error&&<p role="alert" className="inlineError">{error}</p>}{children}</dialog>
}
