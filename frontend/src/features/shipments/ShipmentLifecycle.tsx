import {Card} from '../../components/UI';
import type {ShipmentDetail} from './types';
export default function ShipmentLifecycle({shipment:s}:{shipment:ShipmentDetail}){
 const submission=s.carrier_submissions?.[0];
 const accepted=submission?.status==='submitted'&&!submission.is_test;
 const carrierEvents=s.tracking_events.filter(e=>e.source==='dayton_api');
 const delivered=carrierEvents.some(e=>e.status.toUpperCase()==='DELIVERED');
 const pod=s.documents?.some(d=>/^(pod|proof of delivery|delivery receipt)$/i.test(d.document_type));
 const steps=[
  {title:'Carrier request',done:accepted,note:accepted?'Carrier accepted the request.':submission?.status==='test_submitted'?'Test request only · no live booking confirmed.':'Not accepted by carrier yet.'},
  {title:'Carrier tracking',done:carrierEvents.length>0,note:carrierEvents.length?`${carrierEvents.length} Dayton event(s) received.`:'Awaiting carrier tracking events.'},
  {title:'Delivery',done:delivered,note:delivered?'Dayton delivery event received.':s.delivered_at?'Delivery entered locally · carrier confirmation pending.':'Awaiting delivery confirmation.'},
  {title:'Delivery document',done:!!pod,note:pod?'POD / delivery receipt attached. Review the document.':'Attach the POD or delivery receipt.'},
  {title:'Customer invoice',done:!!s.invoice_issued,note:s.invoice_issued?'Customer invoice recorded.':'No customer invoice issued yet.'}
 ];
 if(s.carrier_scac!=='DAFG')return null;
 return <Card className="shipmentSection"><div className="pilotIntro"><div><h3>Booking → delivery → invoice</h3><p>Evidence for this shipment. A local BOL, manual delivery entry, or test request does not confirm a live carrier booking.</p></div></div><div className="pilotSteps">{steps.map((step,i)=><div className={`pilotStep ${step.done?'complete':''}`} key={step.title}><small>{step.done?'Recorded':'Pending'} · {i+1}</small><strong>{step.title}</strong><span>{step.note}</span></div>)}</div></Card>
}
