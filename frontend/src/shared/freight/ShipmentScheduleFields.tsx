import {CalendarClock} from 'lucide-react';

type Props={
  pickupName?:string;
  deliveryName?:string;
  pickupDefault?:string;
  deliveryDefault?:string;
  title?:string;
  compact?:boolean;
};

export default function ShipmentScheduleFields({pickupName='requested_pickup_at',deliveryName='requested_delivery_at',pickupDefault='',deliveryDefault='',title='Requested schedule',compact=false}:Props){
  return <div className={compact?'scheduleBlock compact':'scheduleBlock'}>
    <div className="sectiontitle top"><CalendarClock/><div><h3>{title}</h3><p>Capture the customer commitment before rating. Pickup time is origin-local; delivery time is destination-local.</p></div></div>
    <div className="form2 scheduleInputs">
      <label>Requested pickup date & time<input type="datetime-local" name={pickupName} defaultValue={pickupDefault}/></label>
      <label>Required delivery date & time<input type="datetime-local" name={deliveryName} defaultValue={deliveryDefault}/></label>
    </div>
  </div>
}
