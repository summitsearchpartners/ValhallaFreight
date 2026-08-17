import {useState} from 'react';
import {CalendarClock,FileText,X} from 'lucide-react';
import {shipmentApi} from './api';
import type {ShipmentDetail} from './types';

const dt=(value?:string|null)=>value?value.slice(0,16):'';

type Props={shipment:ShipmentDetail;close:()=>void;saved:(shipment:ShipmentDetail)=>void};
export default function EditShipmentModal({shipment,close,saved}:Props){
 const [form,setForm]=useState({
  bol_number:shipment.bol_number||'',pro_number:shipment.pro_number||'',status:shipment.status,
  scheduled_pickup_at:dt(shipment.scheduled_pickup_at),requested_delivery_at:dt(shipment.requested_delivery_at),
  actual_pickup_at:dt(shipment.actual_pickup_at),delivered_at:dt(shipment.delivered_at),
 });
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const set=(key:string,value:string)=>setForm(x=>({...x,[key]:value}));
 async function submit(e:React.FormEvent){e.preventDefault();setBusy(true);setError('');try{const result=await shipmentApi.update(shipment.id,{...form,bol_number:form.bol_number||null,pro_number:form.pro_number||null,scheduled_pickup_at:form.scheduled_pickup_at||null,requested_delivery_at:form.requested_delivery_at||null,actual_pickup_at:form.actual_pickup_at||null,delivered_at:form.delivered_at||null});saved(result)}catch(err:any){setError(err.message||'Unable to update shipment')}finally{setBusy(false)}}
 return <div className="modalShade"><form className="entityModal shipmentEditModal" onSubmit={submit}>
  <div className="entityModalHead"><div className="entityModalIcon"><FileText/></div><div><span>SHIPMENT CONTROL TOWER</span><h2>Edit {shipment.shipment_number}</h2></div><button type="button" onClick={close}><X/></button></div>
  <div className="shipmentEditIntro"><CalendarClock/><div><b>Operational schedule & actuals</b><p>Requested dates preserve the customer commitment. Actual pickup and delivery timestamps drive service-performance tracking.</p></div></div>
  <div className="entityFormGrid">
   <label>BOL number<input value={form.bol_number} onChange={e=>set('bol_number',e.target.value)} placeholder="Enter BOL number"/></label>
   <label>PRO number<input value={form.pro_number} onChange={e=>set('pro_number',e.target.value)} placeholder="Carrier PRO number"/></label>
   <label>Scheduled pickup — origin local time<input type="datetime-local" value={form.scheduled_pickup_at} onChange={e=>set('scheduled_pickup_at',e.target.value)}/></label>
   <label>Required delivery — destination local time<input type="datetime-local" value={form.requested_delivery_at} onChange={e=>set('requested_delivery_at',e.target.value)}/></label>
   <label>Actual pickup — origin local time<input type="datetime-local" value={form.actual_pickup_at} onChange={e=>set('actual_pickup_at',e.target.value)}/></label>
   <label>Actual delivery — destination local time<input type="datetime-local" value={form.delivered_at} onChange={e=>set('delivered_at',e.target.value)}/></label>
   <label className="wide">Shipment status<select value={form.status} onChange={e=>set('status',e.target.value)}><option value="booked">Booked</option><option value="pickup_requested">Pickup Requested</option><option value="dispatched">Dispatched</option><option value="picked_up">Picked Up</option><option value="in_transit">In Transit</option><option value="out_for_delivery">Out for Delivery</option><option value="delivered">Delivered</option><option value="cancelled">Cancelled</option></select></label>
  </div>
  {error&&<div className="formError">{error}</div>}
  <div className="entityModalFoot"><button type="button" className="btn secondary" onClick={close}>Cancel</button><button className="btn primary" disabled={busy}>{busy?'Saving shipment...':'Save shipment changes'}</button></div>
 </form></div>
}
