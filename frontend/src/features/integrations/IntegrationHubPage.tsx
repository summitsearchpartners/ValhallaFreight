import {useEffect,useMemo,useRef,useState} from 'react';
import {PlugZap,RefreshCw,CheckCircle2,Settings2,Upload,ShieldCheck,Radio,Truck,FileJson,Activity,X,PlayCircle,DatabaseZap,Info,FileSearch,KeyRound} from 'lucide-react';
import {api} from '../../services/api';
import {Card,PageHead,Pill} from '../../components/UI';

type Integration={id:number;provider:string;category:string;status:string;environment:string;capabilities:string[];last_sync_at?:string|null;last_error?:string|null;settings?:Record<string,any>};
type DaytonStatus=Integration & {scac:string;adapter_installed:boolean;credentials_configured:boolean;credential_source:string;username_hint?:string|null;account?:string|null;base_url:string;auth_type:string;username_limit_note:string;capability_details:{key:string;label:string;status:string}[]};

export default function IntegrationHubPage(){
 const [rows,setRows]=useState<Integration[]>([]);
 const [dayton,setDayton]=useState<DaytonStatus|null>(null);
 const [message,setMessage]=useState('');
 const [busy,setBusy]=useState(false);
 const [showDayton,setShowDayton]=useState(false);
 const [showImport,setShowImport]=useState(false);
 const [workbench,setWorkbench]=useState<any>(null);
 const [importAnalysis,setImportAnalysis]=useState<any>(null);
 const fileRef=useRef<HTMLInputElement>(null);
 const load=()=>Promise.all([api<Integration[]>('/integrations'),api<DaytonStatus>('/integrations/dayton')]).then(([a,b])=>{setRows(a);setDayton(b)});
 useEffect(()=>{load()},[]);
 const groups=useMemo(()=>Object.entries(rows.reduce((a:any,x:any)=>((a[x.category]??=[]).push(x),a),{})),[rows]);
 const openDayton=()=>{setWorkbench(null);setShowDayton(true)};
 const openImport=()=>{setImportAnalysis(null);setShowImport(true)};

 async function test(id:number){setBusy(true);setMessage('');try{const r:any=await api(`/integrations/connection/${id}/test`,{method:'POST'});setMessage(r.message||'Connection test completed')}catch(e:any){setMessage(e.message)}finally{setBusy(false);load()}}
 async function testDayton(){if(!dayton)return;setBusy(true);setMessage('');try{const r:any=await api('/integrations/dayton/test',{method:'POST'});setMessage(r.message);setWorkbench(r)}catch(e:any){setMessage(e.message)}finally{setBusy(false);load()}}
 async function saveDaytonConfig(e:any){e.preventDefault();const f=new FormData(e.currentTarget);setBusy(true);setMessage('');try{await api('/integrations/dayton/config',{method:'PATCH',body:JSON.stringify({environment:f.get('environment'),base_url:dayton?.base_url||'https://api.daytonfreight.com',account:String(f.get('account')||'')||null,terms:f.get('terms'),direct_only:f.get('direct_only')==='on'})});setMessage('Dayton adapter settings saved. Secrets remain in the backend environment.');await load()}catch(e:any){setMessage(e.message)}finally{setBusy(false)}}
 async function runRate(e:any){e.preventDefault();setBusy(true);setMessage('');const f=new FormData(e.currentTarget);try{const r=await api('/integrations/dayton/rate-test',{method:'POST',body:JSON.stringify({origin_zip:f.get('origin'),destination_zip:f.get('destination'),freight_class:f.get('class'),weight_lbs:Number(f.get('weight')),quantity:Number(f.get('qty'))})});setWorkbench(r)}catch(e:any){setMessage(e.message)}finally{setBusy(false)}}
 async function runTracking(e:any){e.preventDefault();setBusy(true);setMessage('');const f=new FormData(e.currentTarget);try{const r=await api('/integrations/dayton/tracking-test',{method:'POST',body:JSON.stringify({number:f.get('number'),type:f.get('type')})});setWorkbench(r)}catch(e:any){setMessage(e.message)}finally{setBusy(false)}}
 async function safePickup(){setBusy(true);setMessage('');try{const r=await api('/integrations/dayton/pickup-test',{method:'POST'});setWorkbench(r);setMessage('Dayton TESTING pickup request completed without creating a live pickup.')}catch(e:any){setMessage(e.message)}finally{setBusy(false)}}
 async function importOpenApi(file:File){setBusy(true);setMessage('');try{const spec=JSON.parse(await file.text());const r:any=await api('/integrations/openapi/import',{method:'POST',body:JSON.stringify({specification:spec})});setImportAnalysis(r.analysis);setMessage(`Imported ${r.analysis.endpoint_count} API operations from ${r.analysis.title}.`);await load()}catch(e:any){setMessage(e.message||'Unable to import OpenAPI specification')}finally{setBusy(false);if(fileRef.current)fileRef.current.value=''}}

 return <>
  <PageHead eyebrow="ADMINISTRATION / CONNECTIVITY" title="Carrier Integration Hub" sub="A normalized carrier API control plane for rating, pickups, tracking, BOLs, documents, service data, EDI and future provider adapters." actions={<><button type="button" className="btn secondary" onClick={openImport}><FileJson size={15}/>Import OpenAPI</button><button type="button" className="btn primary" onClick={openDayton}><Truck size={15}/>Dayton Freight</button></>}/>

  <div className="integrationGuide">
   <div><Settings2/><span><b>Manage adapter</b>Open a carrier's production configuration, capabilities, credentials status and API workbench.</span></div>
   <div><FileSearch/><span><b>Import OpenAPI</b>Upload a carrier swagger/openapi JSON file so Valhalla can discover endpoints and register an integration candidate.</span></div>
   <div><Radio/><span><b>Test connection</b>Run a real provider health/authentication call when credentials are configured.</span></div>
  </div>

  <div className="integrationSummary"><Card><PlugZap/><div><b>{rows.length}</b><span>Registered provider adapters</span></div></Card><Card><CheckCircle2/><div><b>{rows.filter(x=>['configured','connected','imported'].includes(x.status)).length}</b><span>Configured / imported</span></div></Card><Card><RefreshCw/><div><b>{rows.filter(x=>x.last_sync_at).length}</b><span>Health checked</span></div></Card></div>

  <Card className="daytonSpotlight">
   <div className="daytonBrand"><div className="daytonLogo">DF</div><div><span>FIRST DIRECT CARRIER ADAPTER</span><h2>Dayton Freight Lines</h2><p>DAFG · REST API · Basic Auth · JSON-first</p></div></div>
   <div className="daytonStatus"><Pill tone={dayton?.credentials_configured?'success':'warning'}>{dayton?.credentials_configured?'Credentials configured':'Credentials required'}</Pill><b>{dayton?.credentials_configured?'LIVE READY':'ADAPTER CONFIGURED'}</b></div>
   <div className="daytonCapabilities">{dayton?.capability_details?.map(x=><div key={x.key}><ShieldCheck/><span>{x.label}</span><CheckCircle2/></div>)}</div>
   <div className="daytonActions"><button type="button" className="btn secondary" onClick={openDayton}><Settings2 size={14}/>Open adapter</button><button type="button" className="btn primary" disabled={busy} onClick={testDayton}><Radio size={14}/>Test connection</button></div>
  </Card>

  {message&&<div className="integrationNotice">{message}</div>}

  <div className="integrationGroups">{groups.map(([category,items]:any)=><Card key={category}><div className="integrationGroupHead"><div><span>INTEGRATION CATEGORY</span><h3>{category}</h3></div><Pill tone="neutral">{items.length} adapters</Pill></div><div className="integrationCards">{items.map((x:Integration)=>{const isDayton=x.provider==='Dayton Freight';return <div className={`integrationCard ${isDayton?'featured':''}`} key={x.id}><div className="providerMark">{x.provider.slice(0,2).toUpperCase()}</div><div className="providerInfo"><b>{x.provider}</b><span>{x.capabilities?.length?x.capabilities.join(' · '):'Connector framework'}</span></div><Pill tone={isDayton?(dayton?.credentials_configured?'success':'warning'):(x.status==='connected'?'success':x.status==='available'?'neutral':'warning')}>{isDayton?(dayton?.credentials_configured?'live ready':'awaiting credentials'):x.status}</Pill><button type="button" onClick={()=>isDayton?openDayton():test(x.id)}><Settings2/> {isDayton?'Manage':'Test'}</button></div>})}</div></Card>)}</div>

  {showDayton&&dayton&&<div className="vfModalBackdrop" onMouseDown={()=>setShowDayton(false)}><div className="vfModal vfIntegrationModal" onMouseDown={e=>e.stopPropagation()}>
   <div className="vfModalHead"><div><span>DAFG / CARRIER API</span><h2>Dayton Freight Adapter</h2><p>Production configuration and API testing for Dayton Freight inside Valhalla Freight.</p></div><button type="button" aria-label="Close Dayton adapter" onClick={()=>setShowDayton(false)}><X/></button></div>
   <div className="vfModalBody">
    <div className="adapterHero"><DatabaseZap/><div><b>{dayton.adapter_installed?'Adapter installed':'Adapter unavailable'}</b><span>{dayton.base_url}</span></div><Pill tone={dayton.credentials_configured?'success':'warning'}>{dayton.credentials_configured?'LIVE READY':'AWAITING CREDENTIALS'}</Pill></div>
    <div className="adapterPurpose"><Info/><div><b>What “Open adapter / Manage” is for</b><p>This is the carrier-specific control room. In production, this is where an administrator manages Dayton settings, verifies credential status, tests the connection, and runs diagnostic API calls. Quote Studio and Shipment Control Tower use this adapter automatically once it is live.</p></div></div>
    <div className="adapterGrid">
     <Card><h3>Authentication & commercial settings</h3><div className="adapterField"><span>Method</span><b>{dayton.auth_type}</b></div><div className="adapterField"><span>Credential source</span><b>{dayton.credential_source}</b></div><div className="adapterField"><span>Username</span><b>{dayton.username_hint||'Not configured'}</b></div><form className="daytonConfigForm" onSubmit={saveDaytonConfig}><label>Environment<select name="environment" defaultValue={dayton.environment||'sandbox'}><option value="sandbox">Sandbox / Test</option><option value="production">Production</option></select></label><label>Dayton customer account<input name="account" defaultValue={dayton.account||''} placeholder="0000031"/></label><label>Freight terms<select name="terms" defaultValue={dayton.settings?.terms||'ThirdPartyPrepaid'}><option>ThirdPartyPrepaid</option><option>Prepaid</option><option>Collect</option><option>ThirdPartyCollect</option></select></label><label className="checkLine"><input type="checkbox" name="direct_only" defaultChecked={Boolean(dayton.settings?.direct_only)}/> Direct rates only</label><button className="btn secondary" disabled={busy}>Save adapter settings</button></form><p className="adapterHint">Secrets stay backend-only. Add DAYTON_API_USERNAME and DAYTON_API_PASSWORD to the project .env and rebuild. The account may be set here or through DAYTON_API_ACCOUNT.</p><button type="button" className="btn primary wide" onClick={testDayton} disabled={busy}><Activity size={14}/>Test Dayton authentication</button></Card>
     <Card><h3>Supported operations</h3><div className="capabilityChecklist">{dayton.capability_details.map(x=><div key={x.key}><CheckCircle2/><span>{x.label}</span></div>)}</div><div className="credentialsExplainer"><KeyRound/><div><b>Configured vs. live</b><p>“Adapter configured” means Valhalla knows how to communicate with Dayton. “Live ready” means valid Dayton credentials/account access are present and the authentication test succeeds.</p></div></div></Card>
    </div>
    <div className="apiWorkbench"><h3>Dayton API Workbench</h3><p>These diagnostic tools call the actual Dayton adapter when credentials are configured. No Dayton credentials are stored in the browser.</p><div className="workbenchGrid"><form onSubmit={runRate}><b>Live rate test</b><div className="miniForm"><input name="origin" placeholder="Origin ZIP" required/><input name="destination" placeholder="Destination ZIP" required/><input name="class" defaultValue="70" placeholder="Class"/><input name="weight" type="number" defaultValue="500"/><input name="qty" type="number" defaultValue="1"/></div><button className="btn secondary" disabled={busy}><PlayCircle size={14}/>Run rate test</button></form><form onSubmit={runTracking}><b>Tracking test</b><div className="miniForm"><select name="type"><option>Pro</option><option>BillOfLading</option><option>PurchaseOrder</option><option>Pickup</option><option>PSID</option></select><input name="number" placeholder="Tracking number" required/></div><button className="btn secondary" disabled={busy}><PlayCircle size={14}/>Track shipment</button></form><div className="pickupTest"><b>Safe pickup connectivity test</b><p>Uses Dayton's documented TESTING reference so a live pickup is not created.</p><button type="button" className="btn secondary" onClick={safePickup} disabled={busy}><PlayCircle size={14}/>Run TESTING pickup</button></div></div></div>
    {workbench&&<div className="adapterResponse"><div><b>Latest adapter response</b><button type="button" onClick={()=>setWorkbench(null)}>Clear</button></div><pre>{JSON.stringify(workbench,null,2)}</pre></div>}
   </div>
  </div></div>}

  {showImport&&<div className="vfModalBackdrop" onMouseDown={()=>setShowImport(false)}><div className="vfModal openApiModal" onMouseDown={e=>e.stopPropagation()}>
   <div className="vfModalHead"><div><span>INTEGRATION ONBOARDING</span><h2>Import OpenAPI specification</h2><p>Use public carrier Swagger/OpenAPI JSON as the starting point for a new Valhalla adapter.</p></div><button type="button" aria-label="Close OpenAPI import" onClick={()=>setShowImport(false)}><X/></button></div>
   <div className="vfModalBody">
    {!importAnalysis?<><div className="openApiPurpose"><Info/><div><b>What this importer does</b><p>Valhalla reads the API title, endpoint paths, methods, tags and capability areas, then registers the provider as an integration candidate. It does not automatically invent carrier-specific freight mapping or credentials.</p></div></div><div className="openApiDrop" onClick={()=>!busy&&fileRef.current?.click()}><Upload/><h3>Upload swagger.json or openapi.json</h3><p>This is useful when a carrier publishes its API specification. After import, the carrier appears in the Integration Hub so we can build its normalization adapter.</p><input ref={fileRef} type="file" accept=".json,application/json" hidden onChange={e=>e.target.files?.[0]&&importOpenApi(e.target.files[0])}/><button type="button" className="btn primary" disabled={busy}>{busy?'Analyzing specification…':'Choose API specification'}</button></div></>:<div className="openApiResult"><CheckCircle2/><span>OPENAPI IMPORT COMPLETE</span><h3>{importAnalysis.title}</h3><p>{importAnalysis.endpoint_count} API operations discovered and registered for adapter onboarding.</p><div className="openApiStats"><div><b>{importAnalysis.endpoint_count}</b><span>Operations</span></div><div><b>{importAnalysis.tags?.length||0}</b><span>Capability groups</span></div></div><div className="tagCloud">{importAnalysis.tags?.map((t:string)=><span key={t}>{t}</span>)}</div><button type="button" className="btn primary" onClick={()=>setShowImport(false)}>Done</button></div>}
   </div>
  </div></div>}
 </>;
}
