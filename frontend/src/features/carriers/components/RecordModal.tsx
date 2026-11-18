import {useEffect,useMemo,useState} from 'react';
import {X} from 'lucide-react';

type Field={key:string;label:string;type?:'text'|'email'|'tel'|'number'|'date'|'datetime-local'|'textarea'|'select'|'checkbox'|'url';options?:string[];placeholder?:string;span?:2};
export default function RecordModal({open,title,eyebrow='CARRIER 360',fields,initial={},submitLabel='Save',onClose,onSubmit}:{open:boolean;title:string;eyebrow?:string;fields:Field[];initial?:Record<string,any>;submitLabel?:string;onClose:()=>void;onSubmit:(data:Record<string,any>)=>Promise<void>|void}){
  const seed=useMemo(()=>Object.fromEntries(fields.map(f=>{let v=initial[f.key]??(f.type==='checkbox'?false:'');if(f.type==='datetime-local'&&typeof v==='string')v=v.slice(0,16);return [f.key,v]})),[fields,initial]);
  const [form,setForm]=useState<Record<string,any>>(seed);const [busy,setBusy]=useState(false);const [err,setErr]=useState('');
  useEffect(()=>{if(open){setForm(seed);setErr('')}},[open,seed]);
  if(!open)return null;
  async function save(){try{setBusy(true);setErr('');const payload:any={};for(const f of fields){let v=form[f.key];if(f.type==='number'&&v!=='')v=Number(v);if(v==='')v=null;payload[f.key]=v}await onSubmit(payload);onClose()}catch(e:any){setErr(e?.message||'Unable to save record')}finally{setBusy(false)}}
  return <div className="modalOverlay" onMouseDown={e=>{if(e.currentTarget===e.target)onClose()}}><div className="carrierModal">
    <div className="carrierModalHead"><div><span>{eyebrow}</span><h2>{title}</h2></div><button onClick={onClose}><X/></button></div>
    <div className="carrierModalBody"><div className="carrierFormGrid">{fields.map(f=><label key={f.key} className={f.span===2?'span2':''}>{f.label}{f.type==='textarea'?<textarea value={form[f.key]??''} onChange={e=>setForm({...form,[f.key]:e.target.value})} placeholder={f.placeholder}/>:f.type==='select'?<select value={form[f.key]??''} onChange={e=>setForm({...form,[f.key]:e.target.value})}>{(f.options||[]).map(x=><option key={x} value={x}>{x}</option>)}</select>:f.type==='checkbox'?<span className="checkField"><input type="checkbox" checked={!!form[f.key]} onChange={e=>setForm({...form,[f.key]:e.target.checked})}/><b>Enabled</b></span>:<input type={f.type||'text'} value={form[f.key]??''} onChange={e=>setForm({...form,[f.key]:e.target.value})} placeholder={f.placeholder}/>}</label>)}</div>{err&&<div className="formError">{err}</div>}</div>
    <div className="carrierModalFoot"><button className="btn secondary" onClick={onClose}>Cancel</button><button className="btn primary" onClick={save} disabled={busy}>{busy?'Saving...':submitLabel}</button></div>
  </div></div>
}
export type {Field};
