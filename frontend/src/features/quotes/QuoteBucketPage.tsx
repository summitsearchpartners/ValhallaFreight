import {useEffect,useMemo,useState} from 'react';
import {Link,useNavigate} from 'react-router-dom';
import {Archive,Plus,Search} from 'lucide-react';
import {Card,PageHead,Pill} from '../../components/UI';
import {quoteApi} from './api';
import type {QuoteRecord} from './types';

const money=(v:any)=>`$${Number(v||0).toFixed(2)}`;
const statusTone=(s:string)=>s==='booked'?'success':s==='selected'?'warning':'info';
export default function QuoteBucketPage(){
 const nav=useNavigate();const [rows,setRows]=useState<QuoteRecord[]>([]),[query,setQuery]=useState(''),[status,setStatus]=useState('all');
 useEffect(()=>{quoteApi.list().then(setRows)},[]);
 const filtered=useMemo(()=>rows.filter(q=>(status==='all'||q.status===status)&&(!query||`${q.quote_number} ${q.customer_name||''} ${q.origin?.city||''} ${q.destination?.city||''}`.toLowerCase().includes(query.toLowerCase()))),[rows,query,status]);
 return <><PageHead eyebrow="COMMERCIAL / QUOTES" title="Quote Bucket" sub="Review rated quotes, selected carrier options, approval status and quote-to-shipment conversion." actions={<Link className="btn primary" to="/quotes"><Plus size={15}/>New quote</Link>}/><Card><div className="toolbar"><div className="tableSearch"><Search/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder="Search quote, customer, lane..."/></div><select value={status} onChange={e=>setStatus(e.target.value)}><option value="all">Status: All</option><option value="open">Open / rated</option><option value="selected">Selected / awaiting approval</option><option value="booked">Booked / shipment created</option></select></div>{filtered.length?<table className="clickableRows"><thead><tr><th>Quote</th><th>Customer</th><th>Lane</th><th>Selected carrier</th><th>Customer price</th><th>Status</th></tr></thead><tbody>{filtered.map(q=><tr key={q.id} onClick={()=>nav(`/quotes/${encodeURIComponent(q.quote_number)}`)}><td><b>{q.quote_number}</b><div className="tdsub">{new Date(q.created_at).toLocaleString()}</div></td><td>{q.customer_name||'—'}</td><td>{q.origin?.city}, {q.origin?.state} → {q.destination?.city}, {q.destination?.state}</td><td>{q.selected_option?.carrier_name||'Not selected'}</td><td>{q.selected_option?money(q.selected_option.customer_price):'—'}</td><td><Pill tone={statusTone(q.status) as any}>{q.status.replaceAll('_',' ')}</Pill></td></tr>)}</tbody></table>:<div className="empty"><Archive/><h3>No quotes match this view</h3><p>Create a quote in Quote Studio, select a carrier rate, and it will appear here for approval.</p></div>}</Card></>
}
