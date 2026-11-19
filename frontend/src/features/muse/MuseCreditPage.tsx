import {useEffect,useRef,useState} from 'react';
import {Link,useParams,useSearchParams} from 'react-router-dom';
import {api,apiBlob} from '../../services/api';
import {Card,PageHead} from '../../components/UI';
import {useAuth} from '../../context/AuthContext';

export function PdfViewer({url,close}:{url:string;close:()=>void}){
 const ref=useRef<HTMLDialogElement>(null);
 useEffect(()=>{const node=ref.current;if(node&&!node.open)node.showModal();return()=>{if(node?.open)node.close();URL.revokeObjectURL(url)}},[url]);
 return <dialog ref={ref} className="musePdfViewer" aria-label="Muse credit application PDF" onCancel={e=>{e.preventDefault();close()}}>
 <div><b>Muse credit application</b><a className="btn secondary" href={url} download="Muse-Credit-Application.pdf">Download PDF</a><button className="btn secondary" onClick={close} autoFocus>Close document</button></div><iframe title="Muse credit application PDF" src={url}/></dialog>
}

export default function MuseCreditPage(){
 const {manufacturerId=''}=useParams();const [search]=useSearchParams();const quote=search.get('quote');const {user}=useAuth();
 const [form,setForm]=useState<any>(null),[enrollment,setEnrollment]=useState<any>(null),[values,setValues]=useState<Record<string,string>>({date:new Date().toLocaleDateString('en-CA'),signature:'',print_name:user?.full_name||''});
 const [business,setBusiness]=useState(''),[consent,setConsent]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[pdf,setPdf]=useState('');
 const path=`/muse/enrollment/${manufacturerId}`;
 function refresh(){return api<any>(path).then(setEnrollment)}
 useEffect(()=>{let active=true;Promise.all([api<any>('/muse/credit-form'),api<any>(path)]).then(([f,e])=>{if(active){setForm(f);setEnrollment(e);setValues(v=>({...v,company_name:e.manufacturer_name}))}}).catch(e=>{if(active)setError(e.message)});return()=>{active=false}},[path]);
 async function submit(e:React.FormEvent){
  e.preventDefault();setBusy(true);setError('');
  try{setEnrollment(await api(path+'/application',{method:'POST',body:JSON.stringify({values,business_type:business,consent})}));setValues({});setConsent(false)}
  catch(e:any){setError(e.message)}finally{setBusy(false)}
 }
 return <><PageHead eyebrow="MUSE FREIGHT" title="Credit application" sub={enrollment?.manufacturer_name||'Manufacturer onboarding'} actions={<Link className="btn secondary" to={quote?`/quotes/${encodeURIComponent(quote)}`:'/quotes'}>Back to quote</Link>}/>
 {error&&<p className="inlineError" role="alert">{error}</p>}
 {enrollment&&!enrollment.enabled?<Card><p>Muse rates have not been enabled for this manufacturer. Contact your Valhalla TMS administrator.</p></Card>:
 enrollment&&['pending','approved'].includes(enrollment.application_status)?<Card><h2>{enrollment.can_book?'Muse booking approved':'Application sent to Muse Freight'}</h2>
 <p>{enrollment.can_book?'Your manufacturer is approved. Return to the quote and select a Muse rate to complete shipment booking.':'Muse will review your completed application. All authorized users in your manufacturer workspace share this status.'}</p>
 <div className="museRateFooter"><button className="btn secondary" onClick={()=>refresh().catch(e=>setError(e.message))}>Refresh approval status</button>
 {enrollment.application_id&&<button className="btn secondary" onClick={()=>apiBlob(`/muse/applications/${enrollment.application_id}/pdf`).then(b=>setPdf(URL.createObjectURL(b))).catch(e=>setError(e.message))}>View submitted application</button>}</div></Card>:
 form&&enrollment&&<Card><p>Complete the original Muse Freight form below. Its layout and wording are unchanged. Type your authorized signature in the signature blank, then submit it to Muse for review.</p>
 {enrollment.application_status==='declined'&&<p className="inlineError">Muse requested a new application: {enrollment.decision_note}</p>}
 <a className="btn secondary" href="/muse-credit-application.pdf" target="_blank" rel="noopener noreferrer">View original blank PDF</a>
 <form onSubmit={submit}><div className="creditPaperScroll"><div className="creditPaper">
 <img src="/muse-credit-application.png" alt="Original Muse Freight credit application" width="1082" height="1400"/>
 {form.fields.map((f:any)=><input key={f.key} className="creditPdfInput" aria-label={f.label} title={f.label} required={f.required} disabled={busy} maxLength={120}
 style={{left:`${f.x/612*100}%`,top:`${f.top/792*100}%`,width:`${f.width/612*100}%`,height:`${f.height/792*100}%`}}
 value={values[f.key]||''} onChange={e=>setValues(v=>({...v,[f.key]:e.target.value}))} autoComplete="off"/>)}
 {form.business_types.map((f:any)=><input key={f.value} className="creditPdfRadio" type="radio" name="business_type" aria-label={f.value.replaceAll('_',' ')} required disabled={busy}
 style={{left:`${f.x/612*100}%`,top:`${f.top/792*100}%`}} checked={business===f.value} onChange={()=>setBusiness(f.value)}/>)}
 </div></div>
 <label className="museCheck"><input type="checkbox" required checked={consent} onChange={e=>setConsent(e.target.checked)} disabled={busy}/>I am authorized to sign for this company and its bank account. I confirm this application is complete and authorize its electronic submission to Muse Freight with my typed signature.</label>
 <p>Application details are shared only with authorized users of your manufacturer, Valhalla Super Admin, and Muse Freight administrators.</p>
 <button className="btn primary" disabled={busy||!consent}>{busy?'Submitting…':'Submit application to Muse Freight'}</button>
 </form></Card>}
 {pdf&&<PdfViewer url={pdf} close={()=>setPdf('')}/>}</>
}
