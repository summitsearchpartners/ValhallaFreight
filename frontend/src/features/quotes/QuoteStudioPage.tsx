import {useEffect,useState} from 'react';
import {MapPin,Package,Sparkles,ArrowRight,CheckCircle2} from 'lucide-react';
import {api} from '../../services/api';
import {Card,PageHead,Pill} from '../../components/UI';
import AddressField from '../../shared/address/AddressField';
import type {StructuredAddress} from '../../shared/address/googlePlaces';

type LaneAddress = StructuredAddress;

const emptyAddress=():LaneAddress=>({address1:'',address2:'',city:'',state:'',postal_code:'',country:'USA'});

export default function QuoteStudioPage(){
  const [customers,setCustomers]=useState<any[]>([]);
  const [rates,setRates]=useState<any[]>([]);
  const [quote,setQuote]=useState('');
  const [loading,setLoading]=useState(false);
  const [origin,setOrigin]=useState<LaneAddress>(emptyAddress());
  const [destination,setDestination]=useState<LaneAddress>(emptyAddress());

  useEffect(()=>{api<any[]>('/customers').then(setCustomers)},[]);

  function patchOrigin(address:LaneAddress){setOrigin(prev=>({...prev,...address}));}
  function patchDestination(address:LaneAddress){setDestination(prev=>({...prev,...address}));}

  async function rate(e:any){
    e.preventDefault();
    setLoading(true);
    const f=new FormData(e.currentTarget);
    try{
      const r:any=await api('/quotes/rate',{
        method:'POST',
        body:JSON.stringify({
          customer_id:Number(f.get('customer_id')),
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
          <div className="sectiontitle"><MapPin/><div><h3>Lane information</h3><p>Origin and destination details</p></div></div>
          <label>Customer<select name="customer_id" required>{customers.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}</select></label>
          <div className="form2 quoteLaneGrid">
            <fieldset className="quoteAddressGroup">
              <legend>ORIGIN</legend>
              <label>Street address
                <AddressField required value={origin.address1} onValueChange={value=>setOrigin(prev=>({...prev,address1:value}))} onAddressSelected={patchOrigin} placeholder="Start typing the origin address…"/>
              </label>
              <div className="form3">
                <label>City<input required value={origin.city} onChange={e=>setOrigin(prev=>({...prev,city:e.target.value}))} placeholder="City"/></label>
                <label>State<input required value={origin.state} onChange={e=>setOrigin(prev=>({...prev,state:e.target.value.toUpperCase()}))} placeholder="State" maxLength={3}/></label>
                <label>ZIP<input required value={origin.postal_code} onChange={e=>setOrigin(prev=>({...prev,postal_code:e.target.value}))} placeholder="ZIP"/></label>
              </div>
            </fieldset>
            <fieldset className="quoteAddressGroup">
              <legend>DESTINATION</legend>
              <label>Street address
                <AddressField required value={destination.address1} onValueChange={value=>setDestination(prev=>({...prev,address1:value}))} onAddressSelected={patchDestination} placeholder="Start typing the destination address…"/>
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
