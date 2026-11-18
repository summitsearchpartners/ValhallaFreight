import {useState} from 'react';
import {Check,ChevronDown,ChevronUp,PackageCheck} from 'lucide-react';

const LEGACY_ACCESSORIAL_ALIASES:Record<string,string>={
  carnival_delivery:'limited_access_delivery',
  institution_delivery:'limited_access_delivery',
  hotel_delivery:'limited_access_delivery',
  secure_site_delivery:'limited_access_delivery',
  utility_delivery:'limited_access_delivery',
  school_delivery:'limited_access_delivery',
  camp_delivery:'limited_access_delivery',
  construction_delivery:'limited_access_delivery',
  farm_delivery:'limited_access_delivery',
  quarry_delivery:'limited_access_delivery',
  self_storage_delivery:'limited_access_delivery',
  mill_delivery:'limited_access_delivery',
  exhibition_delivery:'trade_show_delivery',
  construction_pickup:'limited_access_pickup',
};

export const ACCESSORIAL_GROUPS={
  'Pickup Services':[
    ['airport_pickup','Airport Pickup'],
    ['appointment_pickup','Appointment / Call Before Pickup'],
    ['inside_pickup','Inside Pickup'],
    ['liftgate_pickup','Liftgate Pickup'],
    ['limited_access_pickup','Limited Access Pickup'],
    ['residential_pickup','Residential Pickup'],
    ['trade_show_pickup','Trade Show Pickup']
  ],
  'Delivery Services':[
    ['airport_delivery','Airport Delivery'],
    ['appointment_delivery','Appointment / Call Before Delivery'],
    ['inside_delivery','Inside Delivery'],
    ['liftgate_delivery','Liftgate Delivery'],
    ['limited_access_delivery','Limited Access Delivery'],
    ['residential_delivery','Residential Delivery'],
    ['trade_show_delivery','Trade Show / Exhibition Delivery']
  ],
  'Shipment Characteristics':[
    ['hazmat','Hazardous Materials'],
    ['freeze_protection','Freeze Protection'],
    ['protect_from_heat','Protect From Heat'],
    ['overlength','Overlength / Excessive Length'],
    ['non_stackable','Non-Stackable Freight'],
    ['high_value','High Value Freight'],
    ['sort_and_segregate','Sort & Segregate'],
    ['notification','Shipment Notification']
  ]
} as const;

export function normalizeAccessorials(values:string[]=[]){
  return Array.from(new Set(values.map(x=>LEGACY_ACCESSORIAL_ALIASES[x]||x)));
}

export function accessorialLabel(code:string){
  const normalized=LEGACY_ACCESSORIAL_ALIASES[code]||code;
  for(const items of Object.values(ACCESSORIAL_GROUPS)){
    const hit=items.find(x=>x[0]===normalized);
    if(hit)return hit[1];
  }
  return normalized.replaceAll('_',' ').replace(/\b\w/g,x=>x.toUpperCase());
}

export default function AccessorialSelector({value,onChange,compact=false}:{value:string[];onChange:(value:string[])=>void;compact?:boolean}){
 const [open,setOpen]=useState(true),[tab,setTab]=useState<keyof typeof ACCESSORIAL_GROUPS>(compact?'Shipment Characteristics':'Delivery Services');
 const normalizedValue=normalizeAccessorials(value);
 const toggle=(code:string)=>onChange(normalizedValue.includes(code)?normalizedValue.filter(x=>x!==code):[...normalizedValue,code]);
 return <div className={`accessorialSelector ${compact?'compact':''}`}>
   <button type="button" className="accessorialHead" onClick={()=>setOpen(!open)}><div><PackageCheck/><span><b>Special Services / Accessorials</b><small>{normalizedValue.length?`${normalizedValue.length} selected`:'Select services required for the rate'}</small></span></div>{open?<ChevronUp/>:<ChevronDown/>}</button>
   {open&&<><div className="accessorialTabs">{Object.keys(ACCESSORIAL_GROUPS).map(k=><button type="button" key={k} className={tab===k?'active':''} onClick={()=>setTab(k as any)}>{k}</button>)}</div><div className="accessorialGrid">{ACCESSORIAL_GROUPS[tab].map(([code,label])=><label className={`accessorialOption ${normalizedValue.includes(code)?'selected':''}`} key={code}><input type="checkbox" checked={normalizedValue.includes(code)} onChange={()=>toggle(code)}/><i>{normalizedValue.includes(code)&&<Check/>}</i><span>{label}</span></label>)}</div></>}
   {!!normalizedValue.length&&<div className="accessorialSummary">{normalizedValue.map(x=><span key={x}>{accessorialLabel(x)}</span>)}</div>}
 </div>
}
