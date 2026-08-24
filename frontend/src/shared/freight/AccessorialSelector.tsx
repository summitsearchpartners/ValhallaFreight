import {useState} from 'react';
import {Check,ChevronDown,ChevronUp,PackageCheck} from 'lucide-react';

export const ACCESSORIAL_GROUPS={
  'Pickup Services':[
    ['airport_pickup','Airport Pickup'],['appointment_pickup','Appointment / Call Before Pickup'],['inside_pickup','Inside Pickup'],['liftgate_pickup','Liftgate Pickup'],['limited_access_pickup','Limited Access Pickup'],['residential_pickup','Residential Pickup'],['trade_show_pickup','Trade Show Pickup'],['construction_pickup','Construction Site Pickup']
  ],
  'Delivery Services':[
    ['airport_delivery','Airport'],['appointment_delivery','Appointment Needed or Call Before'],['carnival_delivery','Carnival, Fair, Flea Market, Strip Mall'],['institution_delivery','Church, Nursing Home, Country Club'],['inside_delivery','Delivery Inside Facility'],['hotel_delivery','Hotel, Motel, Inn, Restaurant'],['secure_site_delivery','Military, Correctional, or Nuclear Site'],['residential_delivery','Residential Delivery'],['trade_show_delivery','Trade Show'],['utility_delivery','Plant (Power, Water, Utility)'],['school_delivery','Apartment, School, University, Library'],['camp_delivery','Camp, Amusement Park, Marina'],['exhibition_delivery','Trade Show / Exhibition Hall'],['construction_delivery','Construction Site Delivery'],['farm_delivery','Farm, Ranch, Vineyard, Orchard, Winery'],['liftgate_delivery','Liftgate Trailer for Delivery'],['quarry_delivery','Quarry or Mining Site'],['self_storage_delivery','Self Storage Facility'],['limited_access_delivery','Limited Access'],['mill_delivery','Mill Site']
  ],
  'Shipment Characteristics':[
    ['hazmat','Hazardous Materials'],['freeze_protection','Freeze Protection'],['protect_from_heat','Protect From Heat'],['overlength','Overlength / Excessive Length'],['non_stackable','Non-Stackable Freight'],['high_value','High Value Freight'],['sort_and_segregate','Sort & Segregate'],['notification','Shipment Notification']
  ]
} as const;

export function accessorialLabel(code:string){for(const items of Object.values(ACCESSORIAL_GROUPS)){const hit=items.find(x=>x[0]===code);if(hit)return hit[1]}return code.replaceAll('_',' ').replace(/\b\w/g,x=>x.toUpperCase())}

export default function AccessorialSelector({value,onChange,compact=false}:{value:string[];onChange:(value:string[])=>void;compact?:boolean}){
 const [open,setOpen]=useState(true),[tab,setTab]=useState<keyof typeof ACCESSORIAL_GROUPS>('Delivery Services');
 const toggle=(code:string)=>onChange(value.includes(code)?value.filter(x=>x!==code):[...value,code]);
 return <div className={`accessorialSelector ${compact?'compact':''}`}>
   <button type="button" className="accessorialHead" onClick={()=>setOpen(!open)}><div><PackageCheck/><span><b>Special Services / Accessorials</b><small>{value.length?`${value.length} selected`:'Select services required for the rate'}</small></span></div>{open?<ChevronUp/>:<ChevronDown/>}</button>
   {open&&<><div className="accessorialTabs">{Object.keys(ACCESSORIAL_GROUPS).map(k=><button type="button" key={k} className={tab===k?'active':''} onClick={()=>setTab(k as any)}>{k}</button>)}</div><div className="accessorialGrid">{ACCESSORIAL_GROUPS[tab].map(([code,label])=><label className={`accessorialOption ${value.includes(code)?'selected':''}`} key={code}><input type="checkbox" checked={value.includes(code)} onChange={()=>toggle(code)}/><i>{value.includes(code)&&<Check/>}</i><span>{label}</span></label>)}</div></>}
   {!!value.length&&<div className="accessorialSummary">{value.map(x=><span key={x}>{accessorialLabel(x)}</span>)}</div>}
 </div>
}
