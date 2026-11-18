import {useEffect,useState} from 'react';
import {Link} from 'react-router-dom';
import {api} from '../../services/api';
import {Card,PageHead} from '../../components/UI';

export default function CustomerBilling(){
 const [rows,setRows]=useState<any[]>([]),[error,setError]=useState('');
 useEffect(()=>{api<any[]>('/finance/customer-invoices').then(setRows).catch(e=>setError(e.message))},[]);
 return <><PageHead eyebrow="YOUR ACCOUNT" title="Invoices & freight charges" sub="Review invoices for your company's shipments."/>
 {error&&<p role="alert">{error}</p>}<Card>{rows.length?<table><thead><tr><th>Invoice</th><th>Amount</th><th>Status</th><th>Due date</th><th>Shipment</th></tr></thead><tbody>{rows.map(r=><tr key={r.id}><td>{r.invoice_number}</td><td>{Number(r.amount).toLocaleString(undefined,{style:'currency',currency:'USD'})}</td><td>{r.status}</td><td>{r.due_date||'—'}</td><td><Link to={`/shipments/${r.shipment_id}`}>Open shipment</Link></td></tr>)}</tbody></table>:<p>No invoices have been issued yet. <Link to="/shipments">Review your shipments and freight charges.</Link></p>}</Card></>;
}
