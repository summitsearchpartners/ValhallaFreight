import {useEffect,useMemo,useState} from 'react';
import {Building2,Search,Sparkles} from 'lucide-react';
import AddressField from '../address/AddressField';
import type {StructuredAddress} from '../address/googlePlaces';
import {customerApi} from '../../features/customers/api';
import type {Customer360,CustomerLocation} from '../../features/customers/types';

export type LaneAddress=StructuredAddress;
export const emptyLaneAddress=():LaneAddress=>({address1:'',address2:'',city:'',state:'',postal_code:'',country:'USA'});

function locationToAddress(location:CustomerLocation):LaneAddress{return {address1:location.address1||'',address2:location.address2||'',city:location.city||'',state:location.state||'',postal_code:location.postal_code||'',country:location.country||'USA'}}

function Picker({locations,value,onChange}:{locations:CustomerLocation[];value:string;onChange:(value:string)=>void}){return <div className="savedLocationPicker"><div className="savedLocationLabel"><Building2 size={13}/><span>Saved customer location</span></div><select value={value} onChange={e=>onChange(e.target.value)} disabled={!locations.length}><option value="">{locations.length?'Optional — choose a saved location…':'No saved locations for this customer'}</option>{locations.map(x=><option key={x.id} value={x.id}>{x.name} — {x.city}, {x.state} {x.postal_code}</option>)}</select>{locations.length>0&&<div className="savedLocationHint">Or type any address below. Saved locations are only a shortcut.</div>}</div>}

export function useCustomerLocations(customerId:number|''){
 const [record,setRecord]=useState<Customer360|null>(null),[loading,setLoading]=useState(false);
 useEffect(()=>{if(!customerId){setRecord(null);return}let active=true;setRecord(null);setLoading(true);customerApi.get(Number(customerId)).then(r=>{if(active)setRecord(r)}).finally(()=>{if(active)setLoading(false)});return()=>{active=false}},[customerId]);
 return {locations:useMemo(()=>record?.locations.filter(x=>x.active!==false)||[],[record]),loading};
}

export default function LaneAddressSelector({title,address,setAddress,locations}:{title:string;address:LaneAddress;setAddress:(address:LaneAddress)=>void;locations:CustomerLocation[]}){
 const [locationId,setLocationId]=useState('');
 useEffect(()=>{setLocationId('')},[locations]);
 function choose(value:string){setLocationId(value);if(!value){setAddress(emptyLaneAddress());return}const loc=locations.find(x=>String(x.id)===value);if(loc)setAddress(locationToAddress(loc))}
 return <fieldset className="quoteAddressGroup"><legend>{title}</legend><Picker locations={locations} value={locationId} onChange={choose}/><div className="addressOrDivider"><span>or</span></div><label><span className="addressInputLabel"><Search size={12}/>Verified street address</span><AddressField required value={address.address1} onValueChange={value=>{setLocationId('');setAddress({...address,address1:value})}} onAddressSelected={selected=>{setLocationId('');setAddress({...address,...selected})}} placeholder={`Start typing the ${title.toLowerCase()} address…`}/></label><div className="form3"><label>City<input required value={address.city} onChange={e=>setAddress({...address,city:e.target.value})}/></label><label>State<input required value={address.state} maxLength={3} onChange={e=>setAddress({...address,state:e.target.value.toUpperCase()})}/></label><label>ZIP<input required value={address.postal_code} onChange={e=>setAddress({...address,postal_code:e.target.value})}/></label></div></fieldset>
}

export function LocationsLoading(){return <div className="savedLocationLoading"><Sparkles size={13}/>Loading saved customer locations…</div>}
