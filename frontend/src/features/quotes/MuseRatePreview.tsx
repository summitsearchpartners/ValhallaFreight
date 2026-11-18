import {useEffect,useRef,useState,type FormEvent} from 'react';
import {ArrowRight,ExternalLink,RefreshCw,Truck,X} from 'lucide-react';
import {Link} from 'react-router-dom';
import {quoteApi} from './api';
import type {MusePreview,MusePreviewSelection,RateOption} from './types';

const usd=new Intl.NumberFormat('en-US',{style:'currency',currency:'USD'});

export function MuseRateBadge({rate}:{rate:RateOption}){
  return rate.provider==='muse_freight'?<span className="museRateBadge">Muse Rate</span>:null;
}

export default function MuseRatePreview({preview,quote,customer,disabled=false,studio=false,canManage=false,onChange,onSelected}:{
  preview:MusePreview;quote:string;customer?:string|null;disabled?:boolean;studio?:boolean;canManage?:boolean;
  onChange:(value:MusePreview|null)=>void;onSelected?:()=>Promise<void>;
}){
  const [busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
  const [selection,setSelection]=useState<MusePreviewSelection|null>(null);
  const [carriers,setCarriers]=useState<{id:number;carrier_name:string}[]>([]);
  const [carrierId,setCarrierId]=useState(''),[cost,setCost]=useState(''),[transit,setTransit]=useState('');
  const [editing,setEditing]=useState(false),[carrier,setCarrier]=useState(''),[price,setPrice]=useState('');
  const rate=preview.rate;

  async function run(action:()=>Promise<void>){
    setBusy(true);setError('');setMessage('');
    try{await action();}
    catch(e){setError(e instanceof Error?e.message:'Unable to update the Muse Freight rate.');}
    finally{setBusy(false);}
  }

  async function openEditor(){
    try{const q=await quoteApi.get(quote);setCarriers(q.options.filter(o=>o.provider!=='muse_freight').map(o=>({id:o.carrier_id,carrier_name:o.carrier_name})));}catch(e){setError(String(e));return}
    setCarrier(rate?.carrier_name??'');setPrice(rate?.customer_price??'');setCarrierId(String(rate?.carrier_id||''));setCost(String(rate?.carrier_cost??''));setTransit(String(rate?.transit_days??''));setEditing(true);setMessage('');
  }

  function save(e:FormEvent<HTMLFormElement>){
    e.preventDefault();
    void run(async()=>{
      onChange(await quoteApi.saveMuseRate(quote,{carrier_name:carrier.trim(),customer_price:price,carrier_id:carrierId?Number(carrierId):null,carrier_cost:cost||null,transit_days:transit?Number(transit):null}));
      setEditing(false);setMessage('Muse rate saved.');
    });
  }

  return <section className={`musePreview ${rate?'musePriced':''}`} aria-label="Muse Freight rate">
    <div className="musePreviewMain">
      <span className="musePreviewIcon"><Truck size={20}/></span>
      <div><div className="musePreviewHeading"><strong>{rate?.carrier_name||'Muse Freight'}</strong><span className="museRateBadge">Muse Rate</span></div>
        <p>{preview.service} · {rate?'Quoted through Muse Freight':'Awaiting a price from Muse Freight'}</p></div>
      {rate&&<div className="museQuotedPrice"><strong>{usd.format(Number(rate.customer_price))}</strong><small>Customer price</small></div>}
      {rate&&<button type="button" className="selectrate" aria-label="Select Muse rate" disabled={disabled||busy||editing}
        onClick={()=>void run(async()=>{
const result=await quoteApi.selectMuseRate(quote,rate.revision);
if(result.selected){await onSelected?.();setMessage('Muse rate selected. Complete shipment confirmation to book.');}
else setSelection(result);
})}>Select <ArrowRight size={14}/></button>}
    </div>
    <div className="museRateFooter">
      {studio&&<Link to={`/quotes/${encodeURIComponent(quote)}`}>Open saved quote</Link>}
      {!editing&&<button type="button" className="btn secondary" disabled={disabled||busy}
        onClick={()=>void run(async()=>{
          const result=await quoteApi.getMuseRate(quote);
          if(!result)throw new Error('Muse rates are no longer available for this quote.');
          onChange(result);setMessage(result.rate?'Muse rate refreshed.':'A Muse price hasn’t been added yet.');
        })}><RefreshCw size={14}/>Refresh Muse rate</button>}
      {canManage&&!editing&&<button type="button" className="btn secondary" disabled={disabled||busy} onClick={openEditor}>{rate?'Edit Muse rate':'Add Muse rate'}</button>}
    </div>
    {editing&&<form className="museRateForm" onSubmit={save}>
      <p>Enter the actual customer price quoted by Muse Freight for this shipment in USD.</p>
      <label>Quoted carrier<select value={carrierId} required disabled={busy} onChange={e=>{setCarrierId(e.target.value);setCarrier(carriers.find(c=>c.id===Number(e.target.value))?.carrier_name||'')}}><option value="">Choose a carrier</option>{carriers.map(c=><option key={c.id} value={c.id}>{c.carrier_name}</option>)}</select></label>
      <label>Customer price (USD)<input type="number" min="0.01" max="9999999999.99" step="0.01" required value={price} onChange={e=>setPrice(e.target.value)} disabled={busy}/></label>
      <label>Muse carrier cost (USD)<input type="number" min="0" step="0.01" value={cost} onChange={e=>setCost(e.target.value)} disabled={busy}/></label>
      <label>Transit (business days)<input type="number" min="1" max="90" value={transit} onChange={e=>setTransit(e.target.value)} disabled={busy}/></label>
      <div className="museRateFooter">
        <button type="button" className="btn secondary" disabled={busy} onClick={()=>{setEditing(false);setError('');}}>Cancel</button>
        {rate&&<button type="button" className="btn secondary" disabled={busy} onClick={()=>void run(async()=>{
          onChange(await quoteApi.removeMuseRate(quote));setEditing(false);setMessage('Muse rate withdrawn.');
        })}>Withdraw Muse rate</button>}
        <button className="btn primary" disabled={busy||!carrier.trim()}>Save Muse rate</button>
      </div>
    </form>}
    {message&&<p role="status">{message}</p>}
    {error&&<p className="inlineError" role="alert">{error}</p>}
    {selection&&<MuseRateDialog selection={selection} services={preview.services} customer={customer} quote={quote} close={()=>setSelection(null)}/>}
  </section>;
}

function MuseRateDialog({selection,services,customer,quote,close}:{
  selection:MusePreviewSelection;services:string[];customer?:string|null;quote:string;close:()=>void
}){
  const dialog=useRef<HTMLDialogElement>(null);
  useEffect(()=>{
    const node=dialog.current;
    if(node&&!node.open)node.showModal();
    return ()=>{if(node?.open)node.close();};
  },[]);
  return <dialog ref={dialog} className="museDialog" aria-labelledby="museDialogTitle"
    onCancel={e=>{e.preventDefault();close();}}
    onClick={e=>{if(e.target===e.currentTarget)close();}}>
    <div className="museDialogInner">
      <div className="museDialogHead">
        <div><span className="museRateBadge">Muse Rate</span>
          <h2 id="museDialogTitle">{selection.application_status==='pending'?'Muse application under review':'Set up your Muse Freight account'}</h2>
          {customer&&<p>Customer: <strong>{customer}</strong></p>}
        </div>
        <button type="button" className="museDialogClose" onClick={close} aria-label="Close Muse Freight rate" autoFocus><X size={20}/></button>
      </div>
      <div className="museServiceList museDialogRate"><strong>{selection.rate.carrier_name}</strong><strong>{usd.format(Number(selection.rate.customer_price))}</strong></div>
      <p>{selection.application_status==='pending'?'Your manufacturer’s credit application has been sent to Muse Freight. You can book Muse rates after Muse approves it.':'Complete the original Muse credit application in the software. Muse will review it and enable booking after approval.'}</p>
      <p>Your other carrier options remain available.</p>
      <div className="museServiceList"><strong>Muse Freight services</strong><ul>{services.map(service=><li key={service}>{service}</li>)}</ul></div>
      <footer className="museDialogActions">
        <button type="button" className="btn secondary" onClick={close}>Back to carrier options</button>
        <Link className="btn primary" to={`/muse-credit/${selection.manufacturer_id}?quote=${encodeURIComponent(quote)}`}>{selection.application_status==='pending'?'View application status':'Complete credit application'} <ExternalLink size={15}/></Link>
      </footer>
    </div>
  </dialog>;
}
