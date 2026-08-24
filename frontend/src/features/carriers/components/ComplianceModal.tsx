import {useEffect,useRef,useState} from 'react';
import {FileCheck2,UploadCloud,X,FileText} from 'lucide-react';

type ComplianceForm={item_type:string;status:string;expires_at?:string|null};
const requirements=['Operating Authority','Cargo Insurance','Auto Liability','W-9','Carrier Agreement','Hazmat Certification','Workers Compensation','Safety Review'];
const statuses=['valid','pending','expiring','expired','invalid'];

export default function ComplianceModal({open,title,initial={},onClose,onSubmit}:{open:boolean;title:string;initial?:Record<string,any>;onClose:()=>void;onSubmit:(data:ComplianceForm,file?:File)=>Promise<void>}){
  const [form,setForm]=useState<ComplianceForm>({item_type:'Operating Authority',status:'valid',expires_at:null});
  const [file,setFile]=useState<File>();const [busy,setBusy]=useState(false);const [err,setErr]=useState('');const inputRef=useRef<HTMLInputElement>(null);
  useEffect(()=>{if(open){setForm({item_type:initial.item_type||'Operating Authority',status:initial.status||'valid',expires_at:initial.expires_at||null});setFile(undefined);setErr('')}},[open,initial]);
  if(!open)return null;
  async function save(){try{setBusy(true);setErr('');await onSubmit(form,file);onClose()}catch(e:any){setErr(e?.message||'Unable to save compliance requirement')}finally{setBusy(false)}}
  function choose(files:FileList|null){const f=files?.[0];if(!f)return;const ok=/\.(pdf|doc|docx|jpe?g|png)$/i.test(f.name);if(!ok){setErr('Upload a PDF, DOC, DOCX, JPG, JPEG, or PNG file.');return}if(f.size>15*1024*1024){setErr('The maximum compliance document size is 15 MB.');return}setErr('');setFile(f)}
  return <div className="modalOverlay" onMouseDown={e=>{if(e.currentTarget===e.target)onClose()}}><div className="carrierModal complianceModal">
    <div className="carrierModalHead"><div><span>CARRIER 360</span><h2>{title}</h2></div><button onClick={onClose}><X/></button></div>
    <div className="carrierModalBody"><div className="carrierFormGrid">
      <label>Requirement<select value={form.item_type} onChange={e=>setForm({...form,item_type:e.target.value})}>{requirements.map(x=><option key={x}>{x}</option>)}</select></label>
      <label>Status<select value={form.status} onChange={e=>setForm({...form,status:e.target.value})}>{statuses.map(x=><option key={x}>{x}</option>)}</select></label>
      <label>Expiration date<input type="date" value={form.expires_at||''} onChange={e=>setForm({...form,expires_at:e.target.value||null})}/></label>
      <div className="complianceUploadBlock">
        <span className="complianceUploadLabel">Compliance document</span>
        <button type="button" className="complianceDropzone" onClick={()=>inputRef.current?.click()} onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();choose(e.dataTransfer.files)}}>
          {file?<><FileText/><div><b>{file.name}</b><small>{(file.size/1024/1024).toFixed(2)} MB · Ready to upload</small></div></>:<><UploadCloud/><div><b>Upload compliance document</b><small>Drag & drop or browse · PDF, DOC, DOCX, JPG, PNG · max 15 MB</small></div></>}
        </button>
        <input ref={inputRef} hidden type="file" accept=".pdf,.doc,.docx,.jpg,.jpeg,.png,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/jpeg,image/png" onChange={e=>choose(e.target.files)}/>
        {initial.document_name&&!file&&<div className="existingComplianceDoc"><FileCheck2/><div><b>Current document</b><span>{initial.document_name}</span><small>Choose a new file above only if you want to replace it.</small></div></div>}
      </div>
    </div>{err&&<div className="formError">{err}</div>}</div>
    <div className="carrierModalFoot"><button className="btn secondary" onClick={onClose}>Cancel</button><button className="btn primary" onClick={save} disabled={busy}>{busy?'Saving...':'Save changes'}</button></div>
  </div></div>
}
