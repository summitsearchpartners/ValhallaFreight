import {useEffect,useMemo,useState} from 'react';
import {useNavigate} from 'react-router-dom';
import {Building2,ShieldCheck,Truck,Search,Plus,Star,PlugZap,AlertTriangle,ArrowUpRight} from 'lucide-react';
import {Card,PageHead,Pill} from '../../components/UI';
import {carrierApi} from './api';
import type {CarrierSummary} from './types';
import CarrierCreateModal from './components/CarrierCreateModal';

export default function CarrierNetworkPage(){
  const [rows,setRows]=useState<CarrierSummary[]>([]);const [q,setQ]=useState('');const [mode,setMode]=useState('All');const [status,setStatus]=useState('All');const [createOpen,setCreateOpen]=useState(false);const [loading,setLoading]=useState(true);const nav=useNavigate();
  async function refresh(){setLoading(true);try{setRows(await carrierApi.list())}finally{setLoading(false)}}
  useEffect(()=>{refresh()},[]);
  const modes=useMemo(()=>['All',...Array.from(new Set(rows.flatMap(x=>x.modes||[x.mode])))],[rows]);
  const filtered=rows.filter(x=>{const text=(x.name+' '+x.scac+' '+x.mode+' '+(x.modes||[]).join(' ')).toLowerCase();const matchQ=text.includes(q.toLowerCase());const matchMode=mode==='All'||(x.modes||[x.mode]).includes(mode);const matchStatus=status==='All'||(status==='Preferred'&&x.preferred)||(status==='Needs attention'&&(!x.compliance_ok||x.authority_status!=='active'))||(status==='Connected'&&x.api_enabled)||(status==='Active'&&x.active);return matchQ&&matchMode&&matchStatus});
  const weighted=rows.filter(x=>x.shipments>0);const avgOtd=weighted.length?weighted.reduce((a,x)=>a+x.on_time_delivery_pct,0)/weighted.length:0;const spend=rows.reduce((a,x)=>a+x.carrier_spend,0);
  return <>
    <PageHead eyebrow="NETWORK / CARRIER 360" title="Carrier Network" sub="Control carrier qualification, compliance, service capability, lane strategy, performance, contracts and spend from one network workspace." actions={<button className="btn primary" onClick={()=>setCreateOpen(true)}><Plus size={15}/>Add carrier</button>}/>
    <div className="carrierHeroKpis">
      <Card><div className="carrierKpiIcon"><Truck/></div><span>Active carriers</span><b>{rows.filter(x=>x.active).length}</b><small>{rows.length} total network records</small></Card>
      <Card><div className="carrierKpiIcon"><Star/></div><span>Preferred network</span><b>{rows.filter(x=>x.preferred).length}</b><small>Strategic routing partners</small></Card>
      <Card><div className="carrierKpiIcon"><ShieldCheck/></div><span>Compliance ready</span><b>{rows.filter(x=>x.compliance_ok).length}</b><small>{rows.filter(x=>!x.compliance_ok).length} need attention</small></Card>
      <Card><div className="carrierKpiIcon"><PlugZap/></div><span>Connected</span><b>{rows.filter(x=>x.api_enabled).length}</b><small>API / EDI enabled</small></Card>
      <Card><div className="carrierKpiIcon"><ArrowUpRight/></div><span>Avg on-time delivery</span><b>{avgOtd.toFixed(1)}%</b><small>Shipment-derived scorecard</small></Card>
      <Card><div className="carrierKpiIcon"><Building2/></div><span>Carrier spend</span><b>${Math.round(spend).toLocaleString()}</b><small>Recorded shipment cost</small></Card>
    </div>
    <Card className="carrierNetworkShell">
      <div className="carrierNetworkToolbar"><div className="tableSearch carrierSearch"><Search/><input value={q} onChange={e=>setQ(e.target.value)} placeholder="Search carrier, SCAC, mode..."/></div><select value={mode} onChange={e=>setMode(e.target.value)}>{modes.map(x=><option key={x}>{x}</option>)}</select><select value={status} onChange={e=>setStatus(e.target.value)}>{['All','Active','Preferred','Connected','Needs attention'].map(x=><option key={x}>{x}</option>)}</select><span className="carrierResultCount">{filtered.length} carriers</span></div>
      {loading?<div className="carrierLoading">Loading carrier network...</div>:<div className="carrierNetworkTableWrap"><table className="carrierNetworkTable"><thead><tr><th>Carrier</th><th>Modes</th><th>Compliance</th><th>Performance</th><th>Spend</th><th>Claims</th><th>Connectivity</th><th></th></tr></thead><tbody>{filtered.map(c=><tr key={c.id} onClick={()=>nav(`/carriers/${c.id}`)}>
        <td><div className="carrierIdentity"><div className="biglogo">{c.scac.slice(0,2)}</div><div><b>{c.name}</b><span>{c.scac} · {c.authority_status}</span></div>{c.preferred&&<Star size={14} className="carrierStar"/>}</div></td>
        <td><div className="modeTags">{(c.modes||[c.mode]).slice(0,3).map(m=><span key={m}>{m}</span>)}</div></td>
        <td><Pill tone={c.compliance_ok?'success':'warning'}>{c.compliance_ok?'Ready':'Review'}</Pill><small className="cellSub">{c.onboarding_status}</small></td>
        <td><b>{c.on_time_delivery_pct.toFixed(1)}%</b><small className="cellSub">OTD · {c.shipments} shipments</small></td>
        <td><b>${Math.round(c.carrier_spend).toLocaleString()}</b><small className="cellSub">Avg ${Math.round(c.avg_cost).toLocaleString()}</small></td>
        <td><b>{c.claims}</b><small className="cellSub">{c.claims_pct.toFixed(2)}%</small></td>
        <td>{c.api_enabled?<Pill tone="success">Connected</Pill>:<Pill tone="neutral">Adapter ready</Pill>}</td>
        <td><ArrowUpRight size={16}/></td>
      </tr>)}</tbody></table>{!filtered.length&&<div className="carrierEmpty"><AlertTriangle/><h3>No carriers match these filters</h3><p>Adjust the search or filters, or add a new carrier to the network.</p></div>}</div>}
    </Card>
    <CarrierCreateModal open={createOpen} onClose={()=>setCreateOpen(false)} onSubmit={async payload=>{const created=await carrierApi.create(payload);setCreateOpen(false);await refresh();nav(`/carriers/${created.id}`)}}/>
  </>
}
