import {Search,Plus,MapPin,Users,Truck,ArrowUpRight} from 'lucide-react';
import {useEffect,useMemo,useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {Card,PageHead,Pill} from '../../../components/UI';
import {customerApi} from '../api';
import type {CustomerSummary} from '../types';
import CustomerModal from './CustomerModal';

export default function CustomerList(){
  const [rows,setRows]=useState<CustomerSummary[]>([]),[search,setSearch]=useState(''),[createOpen,setCreateOpen]=useState(false);
  const navigate=useNavigate();
  const load=()=>customerApi.list().then(setRows);
  useEffect(()=>{load()},[]);
  const filtered=useMemo(()=>rows.filter(c=>(c.name+' '+c.code+' '+(c.industry||'')).toLowerCase().includes(search.toLowerCase())),[rows,search]);
  const active=rows.filter(x=>x.status==='active').length;
  const revenue=rows.reduce((a,b)=>a+Number(b.revenue_total||0),0);
  return <>
    <PageHead eyebrow="CUSTOMER 360" title="Customer Accounts" sub="A single source of truth for shipper profiles, locations, contacts, commercial terms, activity and shipment history." actions={<button className="btn primary" onClick={()=>setCreateOpen(true)}><Plus size={16}/>New customer</button>}/>
    <div className="customerKpis">
      <Card><span>Active accounts</span><strong>{active}</strong><small>{rows.length} total customer records</small></Card>
      <Card><span>Customer locations</span><strong>{rows.reduce((a,b)=>a+b.location_count,0)}</strong><small>Shipping origins and destinations</small></Card>
      <Card><span>Active shipments</span><strong>{rows.reduce((a,b)=>a+b.active_shipment_count,0)}</strong><small>Across all customer accounts</small></Card>
      <Card><span>Lifetime revenue</span><strong>${revenue.toLocaleString(undefined,{maximumFractionDigits:0})}</strong><small>Recorded customer shipment revenue</small></Card>
    </div>
    <Card className="customerTableCard">
      <div className="customerToolbar"><div className="tableSearch"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder="Search customer name, code or industry..."/></div><div className="customerResultCount">{filtered.length} accounts</div></div>
      <table className="customerTable"><thead><tr><th>Customer</th><th>Industry</th><th>Locations</th><th>Contacts</th><th>Shipments</th><th>Revenue</th><th>Status</th><th></th></tr></thead><tbody>{filtered.map(c=><tr key={c.id} onClick={()=>navigate(`/customers/${c.id}`)}>
        <td><div className="customerIdentity"><div className="customerAvatar">{c.name.slice(0,2).toUpperCase()}</div><div><b>{c.name}</b><small>{c.code}</small></div></div></td>
        <td>{c.industry||'—'}</td><td><span className="inlineMeta"><MapPin size={13}/>{c.location_count}</span></td><td><span className="inlineMeta"><Users size={13}/>{c.contact_count}</span></td><td><span className="inlineMeta"><Truck size={13}/>{c.shipment_count}</span></td>
        <td><b>${Number(c.revenue_total||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}</b></td><td><Pill tone={c.status==='active'?'success':'neutral'}>{c.status}</Pill></td><td><ArrowUpRight size={15}/></td>
      </tr>)}</tbody></table>
      {!filtered.length&&<div className="customerEmpty">No customer accounts match your search.</div>}
    </Card>
    {createOpen&&<CustomerModal onClose={()=>setCreateOpen(false)} onSaved={(c)=>{setCreateOpen(false);load();navigate(`/customers/${c.id}`)}}/>}
  </>
}
