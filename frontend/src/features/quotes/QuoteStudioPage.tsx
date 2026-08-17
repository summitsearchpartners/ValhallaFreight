import {useEffect,useMemo,useState} from 'react';
import {MapPin,Package,Sparkles,ArrowRight,CheckCircle2,Building2,Search} from 'lucide-react';
import {api} from '../../services/api';
import {Card,PageHead,Pill} from '../../components/UI';
import AddressField from '../../shared/address/AddressField';
import type {StructuredAddress} from '../../shared/address/googlePlaces';
import {customerApi} from '../customers/api';
import type {Customer360,CustomerLocation,CustomerSummary} from '../customers/types';

type LaneAddress = StructuredAddress;

const emptyAddress=():LaneAddress=>({address1:'',address2:'',city:'',state:'',postal_code:'',country:'USA'});

function locationToAddress(location:CustomerLocation):LaneAddress{
  return {
    address1:location.address1||'',
    address2:location.address2||'',
    city:location.city||'',
    state:location.state||'',
    postal_code:location.postal_code||'',
    country:location.country||'USA'
  };
}

function SavedLocationPicker({label,locations,value,onChange}:{label:string;locations:CustomerLocation[];value:string;onChange:(value:string)=>void}){
  return <div className="savedLocationPicker">
    <div className="savedLocationLabel"><Building2 size={13}/><span>{label}</span></div>
    <select value={value} onChange={e=>onChange(e.target.value)} disabled={!locations.length}>
      <option value="">{locations.length?'Optional — choose a saved location…':'No saved locations for this customer'}</option>
      {locations.map(location=><option key={location.id} value={location.id}>{location.name} — {location.city}, {location.state} {location.postal_code}</option>)}
    </select>
    {locations.length>0&&<div className="savedLocationHint">Or type any address below. Saved locations are only a shortcut.</div>}
  </div>;
}

export default function QuoteStudioPage(){
  const [customers,setCustomers]=useState<CustomerSummary[]>([]);
  const [selectedCustomerId,setSelectedCustomerId]=useState<number|''>('');
  const [customer360,setCustomer360]=useState<Customer360|null>(null);
  const [locationsLoading,setLocationsLoading]=useState(false);
  const [originLocationId,setOriginLocationId]=useState('');
  const [destinationLocationId,setDestinationLocationId]=useState('');
  const [rates,setRates]=useState<any[]>([]);
  const [quote,setQuote]=useState('');
  const [loading,setLoading]=useState(false);
  const [origin,setOrigin]=useState<LaneAddress>(emptyAddress());
  const [destination,setDestination]=useState<LaneAddress>(emptyAddress());

  useEffect(()=>{
    customerApi.list().then(items=>{
      setCustomers(items);
      if(items.length)setSelectedCustomerId(items[0].id);
    });
  },[]);

  useEffect(()=>{
    if(!selectedCustomerId){setCustomer360(null);return;}
    let active=true;
    setLocationsLoading(true);
    customerApi.get(Number(selectedCustomerId)).then(record=>{
      if(!active)return;
      setCustomer360(record);
      setOriginLocationId('');
      setDestinationLocationId('');
      setOrigin(emptyAddress());
      setDestination(emptyAddress());
    }).finally(()=>{if(active)setLocationsLoading(false)});
    return()=>{active=false};
  },[selectedCustomerId]);

  const savedLocations=useMemo(()=>customer360?.locations.filter(location=>location.active!==false)||[],[customer360]);

  function patchOrigin(address:LaneAddress){setOrigin(prev=>({...prev,...address}));}
  function patchDestination(address:LaneAddress){setDestination(prev=>({...prev,...address}));}

  function chooseSavedLocation(which:'origin'|'destination',value:string){
    const setLocationId=which==='origin'?setOriginLocationId:setDestinationLocationId;
    const setAddress=which==='origin'?setOrigin:setDestination;
    setLocationId(value);
    if(!value){
      setAddress(emptyAddress());
      return;
    }
    const location=savedLocations.find(item=>String(item.id)===value);
    if(location)setAddress(locationToAddress(location));
  }

  async function rate(e:any){
    e.preventDefault();
    setLoading(true);
    const f=new FormData(e.currentTarget);
    try{
      const r:any=await api('/quotes/rate',{
        method:'POST',
        body:JSON.stringify({
          customer_id:Number(selectedCustomerId||f.get('customer_id')),
          origin:{
            address1:origin.address1,
            address2:origin.address2||null,
            city:origin.city,
            state:origin.state,
            postal_code:origin.postal_code,
            country:origin.country==='USA'?'US':origin.country
          },
          destination:{
            address1:destination.address1,
            address2:destination.address2||null,
            city:destination.city,
            state:destination.state,
            postal_code:destination.postal_code,
            country:destination.country==='USA'?'US':destination.country
          },
          handling_units:[{
            quantity:Number(f.get('qty')),
            type:'Pallet',
            weight_lbs:Number(f.get('weight')),
            length_in:Number(f.get('length')),
            width_in:Number(f.get('width')),
            height_in:Number(f.get('height')),
            freight_class:String(f.get('class'))
          }],
          accessorials:[]
        })
      });
      setRates(r.options);
      setQuote(r.quote_number);
    }finally{setLoading(false)}
  }

  return <>
    <PageHead eyebrow="RATE / QUOTE / BOOK" title="Quote Studio" sub="Build an LTL shipment once. Valhalla Freight normalizes carrier responses and applies the correct customer pricing automatically."/>
    <div className="quotegrid">
      <Card>
        <form onSubmit={rate}>
          <div className="sectiontitle"><MapPin/><div><h3>Lane information</h3><p>Choose saved customer locations or search any verified address.</p></div></div>
          <label>Customer
            <select name="customer_id" required value={selectedCustomerId} onChange={e=>setSelectedCustomerId(Number(e.target.value))}>
              {customers.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}
            </select>
          </label>
          {locationsLoading&&<div className="savedLocationLoading"><Sparkles size={13}/>Loading saved customer locations…</div>}
          <div className="form2 quoteLaneGrid">
            <fieldset className="quoteAddressGroup">
              <legend>ORIGIN</legend>
              <SavedLocationPicker label="Saved customer location" locations={savedLocations} value={originLocationId} onChange={value=>chooseSavedLocation('origin',value)}/>
              <div className="addressOrDivider"><span>or</span></div>
              <label><span className="addressInputLabel"><Search size={12}/>Verified street address</span>
                <AddressField required value={origin.address1} onValueChange={value=>{setOriginLocationId('');setOrigin(prev=>({...prev,address1:value}))}} onAddressSelected={address=>{setOriginLocationId('');patchOrigin(address)}} placeholder="Start typing the origin address…"/>
              </label>
              <div className="form3">
                <label>City<input required value={origin.city} onChange={e=>setOrigin(prev=>({...prev,city:e.target.value}))} placeholder="City"/></label>
                <label>State<input required value={origin.state} onChange={e=>setOrigin(prev=>({...prev,state:e.target.value.toUpperCase()}))} placeholder="State" maxLength={3}/></label>
                <label>ZIP<input required value={origin.postal_code} onChange={e=>setOrigin(prev=>({...prev,postal_code:e.target.value}))} placeholder="ZIP"/></label>
              </div>
            </fieldset>
            <fieldset className="quoteAddressGroup">
              <legend>DESTINATION</legend>
              <SavedLocationPicker label="Saved customer location" locations={savedLocations} value={destinationLocationId} onChange={value=>chooseSavedLocation('destination',value)}/>
              <div className="addressOrDivider"><span>or</span></div>
              <label><span className="addressInputLabel"><Search size={12}/>Verified street address</span>
                <AddressField required value={destination.address1} onValueChange={value=>{setDestinationLocationId('');setDestination(prev=>({...prev,address1:value}))}} onAddressSelected={address=>{setDestinationLocationId('');patchDestination(address)}} placeholder="Start typing the destination address…"/>
              </label>
              <div className="form3">
                <label>City<input required value={destination.city} onChange={e=>setDestination(prev=>({...prev,city:e.target.value}))} placeholder="City"/></label>
                <label>State<input required value={destination.state} onChange={e=>setDestination(prev=>({...prev,state:e.target.value.toUpperCase()}))} placeholder="State" maxLength={3}/></label>
                <label>ZIP<input required value={destination.postal_code} onChange={e=>setDestination(prev=>({...prev,postal_code:e.target.value}))} placeholder="ZIP"/></label>
              </div>
            </fieldset>
          </div>
          <div className="sectiontitle top"><Package/><div><h3>Freight details</h3><p>Handling unit dimensions and classification</p></div></div>
          <div className="form6"><label>Qty<input name="qty" type="number" defaultValue="2"/></label><label>Weight (lb)<input name="weight" type="number" defaultValue="1850"/></label><label>Length<input name="length" type="number" defaultValue="48"/></label><label>Width<input name="width" type="number" defaultValue="40"/></label><label>Height<input name="height" type="number" defaultValue="52"/></label><label>Class<select name="class"><option>70</option><option>77.5</option><option>85</option><option>100</option><option>125</option><option>150</option></select></label></div>
          <button className="btn primary wide" disabled={loading}><Sparkles size={17}/>{loading?'Rating network...':'Get live rates'}</button>
        </form>
      </Card>
      <div><Card className="ratepanel"><div className="cardhead"><div><span>CARRIER OPTIONS</span><h3>{rates.length?`${rates.length} normalized rates`:'Ready to rate'}</h3></div>{quote&&<Pill tone="success">{quote}</Pill>}</div>{!rates.length?<div className="empty"><div><Sparkles/></div><h3>Your rate comparison will appear here</h3><p>Valhalla Freight will rank normalized options by customer price while protecting the pricing rules and minimum margin configured for this account.</p></div>:<div className="rates">{rates.map((r,i)=><div className={`rate ${i===0?'best':''}`} key={r.carrier_id}>{i===0&&<span className="besttag"><CheckCircle2 size={13}/>Best value</span>}<div className="ratecarrier"><div className="carrierlogo">{r.scac.slice(0,2)}</div><div><b>{r.carrier_name}</b><span>{r.service} • {r.transit_days} business days</span></div></div><div className="rateprice"><strong>${Number(r.customer_price).toFixed(2)}</strong><span>Cost ${Number(r.carrier_cost).toFixed(2)} · GP ${Number(r.gross_profit).toFixed(2)} ({Number(r.margin_pct).toFixed(1)}%)</span></div><button className="selectrate">Select <ArrowRight size={14}/></button></div>)}</div>}</Card></div>
    </div>
  </>;
}
