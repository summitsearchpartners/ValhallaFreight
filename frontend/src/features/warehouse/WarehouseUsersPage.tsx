import {useEffect,useState,type FormEvent} from 'react';
import {useAuth} from '../../context/AuthContext';
import {api} from '../../services/api';

type WarehouseUser={id:number;email:string;full_name:string;active:boolean;customer_id:number};
type Company={id:number;name:string;manufacturer_id:number|null};
const empty={email:'',full_name:'',password:'',active:true};

export default function WarehouseUsersPage(){
 const {user}=useAuth();const isSuper=user?.role==='admin';
 const [companies,setCompanies]=useState<Company[]>([]);
 const [companyId,setCompanyId]=useState<number|undefined>(user?.customer_id??undefined);
 const [rows,setRows]=useState<WarehouseUser[]>([]);
 const [editing,setEditing]=useState<number|null>(null);
 const [form,setForm]=useState({...empty});
 const [error,setError]=useState('');const [notice,setNotice]=useState('');const [busy,setBusy]=useState(false);
 useEffect(()=>{if(isSuper)api<Company[]>('/admin/users/companies').then(v=>setCompanies(v.filter(c=>!c.manufacturer_id))).catch(e=>setError(e.message));},[isSuper]);
 useEffect(()=>{if(!companyId){setRows([]);return}api<WarehouseUser[]>(`/warehouse/users?customer_id=${companyId}`).then(setRows).catch(e=>setError(e.message));},[companyId]);
 function reload(){if(companyId)api<WarehouseUser[]>(`/warehouse/users?customer_id=${companyId}`).then(setRows).catch(e=>setError(e.message));}
 function select(row?:WarehouseUser){setEditing(row?.id??null);setForm(row?{email:row.email,full_name:row.full_name,password:'',active:row.active}:{...empty});setError('');setNotice('');}
 async function save(e:FormEvent){e.preventDefault();if(!companyId)return;setBusy(true);setError('');setNotice('');try{
  const payload={...form,customer_id:companyId,password:form.password||null};
  await api(editing===null?'/warehouse/users':`/warehouse/users/${editing}`,{method:editing===null?'POST':'PUT',body:JSON.stringify(payload)});
  select();setNotice(editing===null?'Warehouse user created.':'Warehouse user updated.');reload();
 }catch(err:any){setError(err.message)}finally{setBusy(false)}}
 return <main style={{maxWidth:1050,margin:'24px auto',padding:24}}>
  <h1>Warehouse Users</h1>
  <p>Create Safe Load-only accounts for warehouse employees. These users cannot sign in to the Valhalla Freight manufacturer portal.</p>
  {isSuper&&<label>Manufacturer company <select value={companyId??''} onChange={e=>setCompanyId(e.target.value?Number(e.target.value):undefined)}><option value="">Select manufacturer</option>{companies.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select></label>}
  {!companyId?<p>Select a manufacturer to manage its warehouse employees.</p>:<>
   <h2>{editing===null?'Create Warehouse Account':'Edit Warehouse Account'}</h2>
   <form onSubmit={save} style={{display:'grid',gap:12,maxWidth:550}}>
    <label>Employee name<input required maxLength={180} value={form.full_name} onChange={e=>setForm({...form,full_name:e.target.value})}/></label>
    <label>Email<input required type="email" value={form.email} onChange={e=>setForm({...form,email:e.target.value})}/></label>
    <label>{editing===null?'Initial password':'New password (leave blank to keep existing)'}<input type="password" required={editing===null} minLength={12} maxLength={72} autoComplete="new-password" value={form.password} onChange={e=>setForm({...form,password:e.target.value})}/></label>
    <label><input type="checkbox" checked={form.active} onChange={e=>setForm({...form,active:e.target.checked})}/> Account enabled</label>
    <div style={{display:'flex',gap:12}}><button className="btn primary" disabled={busy}>{busy?'Saving…':'Save Warehouse Account'}</button>{editing!==null&&<button className="btn secondary" type="button" onClick={()=>select()}>Cancel edit</button>}</div>
   </form>
   {error&&<p role="alert" style={{color:'#e57b7b'}}>{error}</p>}{notice&&<p role="status">{notice}</p>}
   <h2 style={{marginTop:32}}>Warehouse Employees</h2>
   <table style={{width:'100%'}}><thead><tr><th>Name</th><th>Email</th><th>Status</th><th>Action</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td>{r.full_name}</td><td>{r.email}</td><td>{r.active?'Active':'Disabled'}</td><td><button className="btn secondary" onClick={()=>select(r)}>Edit / Reset / Disable</button></td></tr>)}</tbody></table>
  </>}
 </main>
}
