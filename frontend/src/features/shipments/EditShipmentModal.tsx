import {useState} from 'react';
import {CalendarClock,FileText,PackageSearch,X} from 'lucide-react';
import {shipmentApi} from './api';
import type {ShipmentDetail} from './types';

const dt=(value?:string|null)=>value?value.slice(0,16):'';

type Props={shipment:ShipmentDetail;close:()=>void;saved:(shipment:ShipmentDetail)=>void};
export default function EditShipmentModal({shipment,close,saved}:Props){
 const [form,setForm]=useState({
  pro_number:shipment.pro_number||'',status:shipment.status,
  scheduled_pickup_at:dt(shipment.scheduled_pickup_at),requested_delivery_at:dt(shipment.requested_delivery_at),
  actual_pickup_at:dt(shipment.actual_pickup_at),delivered_at:dt(shipment.delivered_at),
  po_number:shipment.po_number||'',customer_reference:shipment.customer_reference||'',
  package_count:shipment.package_count==null?'':String(shipment.package_count),package_type:shipment.package_type||'',
  commodity_description:shipment.commodity_description||'',nmfc_number:shipment.nmfc_number||'',
  hazmat_emergency_contact:shipment.hazmat_emergency_contact||'',hazmat_emergency_phone:shipment.hazmat_emergency_phone||'',
  declared_value:shipment.declared_value==null?'':String(shipment.declared_value),
 });
 const [busy,setBusy]=useState(false),[error,setError]=useState('');
 const set=(key:string,value:string)=>setForm(x=>({...x,[key]:value}));
 async function submit(e:React.FormEvent){
  e.preventDefault();setBusy(true);setError('');
  try{
   const result=await shipmentApi.update(shipment.id,{
    ...form,
    pro_number:form.pro_number||null,
    po_number:form.po_number||null,customer_reference:form.customer_reference||null,
    package_count:form.package_count===''?null:Number(form.package_count),package_type:form.package_type||null,
    commodity_description:form.commodity_description||null,nmfc_number:form.nmfc_number||null,
    hazmat_emergency_contact:form.hazmat_emergency_contact||null,hazmat_emergency_phone:form.hazmat_emergency_phone||null,
    declared_value:form.declared_value===''?null:Number(form.declared_value),
    scheduled_pickup_at:form.scheduled_pickup_at||null,requested_delivery_at:form.requested_delivery_at||null,
    actual_pickup_at:form.actual_pickup_at||null,delivered_at:form.delivered_at||null,
   });
   saved(result);
  }catch(err:any){setError(err.message||'Unable to update shipment')}finally{setBusy(false)}
 }
 return <div className="modalShade"><form className="entityModal shipmentEditModal" onSubmit={submit}>
  <div className="entityModalHead"><div className="entityModalIcon"><FileText/></div><div><span>SHIPMENT CONTROL TOWER</span><h2>{`Edit ${shipment.shipment_number}`}</h2></div><button type="button" onClick={close}><X/></button></div>

  <div className="shipmentEditIntro"><PackageSearch/><div><b>Shipment references & commodity details</b><p>These fields are stored on the shipment and flow automatically into the Valhalla Freight Bill of Lading.</p></div></div>
  <div className="entityFormGrid">
   <div className="lockedBolField"><span>BOL number</span><strong>{shipment.bol_number||'—'}</strong><small>System assigned at shipment creation · cannot be changed</small></div>
   <label>PRO number<input value={form.pro_number} onChange={e=>set('pro_number',e.target.value)} placeholder="Carrier PRO number"/></label>
   <label>PO number<input value={form.po_number} onChange={e=>set('po_number',e.target.value)} placeholder="Customer purchase order"/></label>
   <label>Customer reference<input value={form.customer_reference} onChange={e=>set('customer_reference',e.target.value)} placeholder="Customer reference / shipment reference"/></label>
   <label>Package count<input min="0" step="1" type="number" readOnly={!!shipment.quote_id} title={shipment.quote_id?"Calculated from the quoted freight lines":undefined} value={form.package_count} onChange={e=>set('package_count',e.target.value)} placeholder="e.g. 24"/></label>
   <label>Package type<select value={form.package_type} onChange={e=>set('package_type',e.target.value)}><option value="">Select package type</option><option>Pallets</option><option>Skids</option><option>Boxes</option><option>Crates</option><option>Drums</option><option>Bundles</option><option>Gaylord</option><option>Cartons</option><option>Pieces</option><option>Other</option></select></label>
   <label>NMFC number<input value={form.nmfc_number} onChange={e=>set('nmfc_number',e.target.value)} placeholder="NMFC item / sub number"/></label>
   <label>Declared value ($)<input min="0" step="0.01" type="number" value={form.declared_value} onChange={e=>set('declared_value',e.target.value)} placeholder="0.00"/></label>
   <label className="wide">Commodity description<textarea rows={3} value={form.commodity_description} onChange={e=>set('commodity_description',e.target.value)} placeholder="Describe the commodity exactly as it should appear on the BOL"/></label>
   <label>Hazmat emergency contact<input value={form.hazmat_emergency_contact} onChange={e=>set('hazmat_emergency_contact',e.target.value)} placeholder="Emergency contact name / provider"/></label>
   <label>Hazmat emergency phone<input value={form.hazmat_emergency_phone} onChange={e=>set('hazmat_emergency_phone',e.target.value)} placeholder="(800) 000-0000"/></label>
  </div>

  <div className="shipmentEditIntro"><CalendarClock/><div><b>Operational schedule & actuals</b><p>Requested dates preserve the customer commitment. Actual pickup and delivery timestamps drive service-performance tracking.</p></div></div>
  <div className="entityFormGrid">
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
