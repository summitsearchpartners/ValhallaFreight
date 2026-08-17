import {useEffect,useState} from 'react';
import {MapPin,Sparkles,ArrowRight,CheckCircle2,Archive,Loader2} from 'lucide-react';
import {Link,useNavigate} from 'react-router-dom';
import {api} from '../../services/api';
import {Card,PageHead,Pill} from '../../components/UI';
import {customerApi} from '../customers/api';
import type {CustomerSummary} from '../customers/types';
import LaneAddressSelector,{emptyLaneAddress,useCustomerLocations,LocationsLoading,type LaneAddress} from '../../shared/freight/LaneAddressSelector';
import FreightDetailsFields from '../../shared/freight/FreightDetailsFields';
import {quoteApi} from './api';
import type {RateOption} from './types';

export default function QuoteStudioPage(){
  const nav=useNavigate();
  const [customers,setCustomers]=useState<CustomerSummary[]>([]);
  const [selectedCustomerId,setSelectedCustomerId]=useState<number|''>('');
  const {locations,loading:locationsLoading}=useCustomerLocations(selectedCustomerId);
  const [rates,setRates]=useState<RateOption[]>([]),[quote,setQuote]=useState(''),[loading,setLoading]=useState(false),[selecting,setSelecting]=useState<number|null>(null),[error,setError]=useState('');
  const [origin,setOrigin]=useState<LaneAddress>(emptyLaneAddress()),[destination,setDestination]=useState<LaneAddress>(emptyLaneAddress());

  useEffect(()=>{customerApi.list().then(items=>{setCustomers(items);if(items.length)setSelectedCustomerId(items[0].id)})},[]);
  useEffect(()=>{setOrigin(emptyLaneAddress());setDestination(emptyLaneAddress());setRates([]);setQuote('')},[selectedCustomerId]);

  async function rate(e:any){
    e.preventDefault();setLoading(true);setError('');const f=new FormData(e.currentTarget);
    try{
      const r:any=await api('/quotes/rate',{method:'POST',body:JSON.stringify({
        customer_id:Number(selectedCustomerId),
        origin:{...origin,address2:origin.address2||null,country:origin.country==='USA'?'US':origin.country},
        destination:{...destination,address2:destination.address2||null,country:destination.country==='USA'?'US':destination.country},
        handling_units:[{quantity:Number(f.get('qty')),type:'Pallet',weight_lbs:Number(f.get('weight')),length_in:Number(f.get('length')),width_in:Number(f.get('width')),height_in:Number(f.get('height')),freight_class:String(f.get('class'))}],
        accessorials:[]
      })});setRates(r.options);setQuote(r.quote_number)
    }catch(err:any){setError(err.message||'Unable to rate shipment')}finally{setLoading(false)}
  }

  async function selectRate(rate:RateOption){
    if(!quote)return;setSelecting(rate.carrier_id);setError('');
    try{await quoteApi.select(quote,rate.carrier_id);nav(`/quotes/${encodeURIComponent(quote)}`)}catch(err:any){setError(err.message||'Unable to select this rate')}finally{setSelecting(null)}
  }

  return <>
    <PageHead eyebrow="RATE / QUOTE / BOOK" title="Quote Studio" sub="Build the shipment, compare normalized carrier rates, then select the option you want to save for approval." actions={<Link className="btn secondary" to="/quotes/bucket"><Archive size={15}/>Quote bucket</Link>}/>
    <div className="quotegrid">
      <Card><form onSubmit={rate}><div className="sectiontitle"><MapPin/><div><h3>Lane information</h3><p>Use a saved customer location or search any verified address.</p></div></div><label>Customer<select required value={selectedCustomerId} onChange={e=>setSelectedCustomerId(Number(e.target.value))}>{customers.map(c=><option value={c.id} key={c.id}>{c.name}</option>)}</select></label>{locationsLoading&&<LocationsLoading/>}<div className="form2 quoteLaneGrid"><LaneAddressSelector title="ORIGIN" address={origin} setAddress={setOrigin} locations={locations}/><LaneAddressSelector title="DESTINATION" address={destination} setAddress={setDestination} locations={locations}/></div><FreightDetailsFields/>{error&&<div className="inlineError">{error}</div>}<button className="btn primary wide" disabled={loading||!selectedCustomerId}><Sparkles size={17}/>{loading?'Rating network...':'Get live rates'}</button></form></Card>
      <div><Card className="ratepanel"><div className="cardhead"><div><span>CARRIER OPTIONS</span><h3>{rates.length?`${rates.length} normalized rates`:'Ready to rate'}</h3></div>{quote&&<Pill tone="success">{quote}</Pill>}</div>{!rates.length?<div className="empty"><div><Sparkles/></div><h3>Your rate comparison will appear here</h3><p>Selecting a rate now saves it into the Quote Bucket. The shipment is not created until the quote is approved.</p></div>:<div className="rates">{rates.map((r,i)=><div className={`rate ${i===0?'best':''}`} key={r.carrier_id}>{i===0&&<span className="besttag"><CheckCircle2 size={13}/>Best value</span>}<div className="ratecarrier"><div className="carrierlogo">{r.scac.slice(0,2)}</div><div><b>{r.carrier_name}</b><span>{r.service} • {r.transit_days} business days</span></div></div><div className="rateprice"><strong>${Number(r.customer_price).toFixed(2)}</strong><span>Cost ${Number(r.carrier_cost).toFixed(2)} · GP ${Number(r.gross_profit).toFixed(2)} ({Number(r.margin_pct).toFixed(1)}%)</span></div><button type="button" className="selectrate" disabled={selecting!==null} onClick={()=>selectRate(r)}>{selecting===r.carrier_id?<><Loader2 size={13}/>Saving…</>:<>Select <ArrowRight size={14}/></>}</button></div>)}</div>}</Card></div>
    </div>
  </>;
}
