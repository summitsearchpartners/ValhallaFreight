import {formatTimestamp as displayDateTime} from '../../shared/display/preferences';
import {useEffect,useMemo,useRef,useState} from 'react';
import {PlugZap,RefreshCw,CheckCircle2,Settings2,Upload,ShieldCheck,Radio,Truck,FileJson,Activity,X,PlayCircle,DatabaseZap,Info,FileSearch,KeyRound,LockKeyhole,Eye,EyeOff,Trash2,Save,ServerCog} from 'lucide-react';
import {api as baseApi} from '../../services/api';
import {useAuth} from '../../context/AuthContext';
import {Card,PageHead,Pill} from '../../components/UI';

type Integration={adapter_available?:boolean;state?:string;credentials_configured?:boolean;connection_verified?:boolean;live_healthy?:boolean;last_success_at?:string|null;customer_id?:number|null;id:number;provider:string;category:string;status:string;environment:string;capabilities:string[];last_sync_at?:string|null;last_error?:string|null;settings?:Record<string,any>};
type CredentialStatus={configured:boolean;auth_type:string;username_hint?:string|null;has_password:boolean;has_api_key:boolean;has_bearer_token:boolean;client_id_hint?:string|null;has_client_secret:boolean;custom_header_names:string[];configured_at?:string|null;updated_at?:string|null};
type DaytonStatus=Integration & {scac:string;adapter_installed:boolean;credentials_configured:boolean;credential_source:string;username_hint?:string|null;account?:string|null;base_url:string;auth_type:string;auth_type_key:string;username_limit_note:string;credential_status:CredentialStatus;capability_details:{key:string;label:string;status:string}[]};
type ManagedConnection={connection:Integration;credentials:CredentialStatus};

const authLabel=(value:string)=>({none:'No authentication',basic_auth:'Basic Authentication',api_key:'API Key',bearer_token:'Bearer Token',oauth2:'OAuth 2.0',client_credentials:'Client ID / Secret',custom:'Custom Headers'} as Record<string,string>)[value]||value;

export default function IntegrationHubPage(){
 const {user}=useAuth();const [companyId,setCompanyId]=useState('');const [companies,setCompanies]=useState<{id:number;name:string}[]>([]);
 const api=<T,>(path:string,init?:RequestInit)=>baseApi<T>(path,{...init,headers:{...init?.headers,...(user?.role==='admin'&&companyId?{'X-Company-Id':companyId}:{})}});
 useEffect(()=>{if(user?.role==='admin')baseApi<any[]>('/admin/users/companies').then(rows=>setCompanies(rows.filter(c=>!c.manufacturer_id))).catch(e=>setMessage(e.message))},[user?.role]);
 const pendingManage=useRef<Integration|null>(null);
 const [rows,setRows]=useState<Integration[]>([]);
 const [dayton,setDayton]=useState<DaytonStatus|null>(null);
 const [message,setMessage]=useState('');
 const [busy,setBusy]=useState(false);
 const [showDayton,setShowDayton]=useState(false);
 const [showImport,setShowImport]=useState(false);
 const [showGeneric,setShowGeneric]=useState(false);
 const [managed,setManaged]=useState<ManagedConnection|null>(null);
 const [showPassword,setShowPassword]=useState(false);
 const [deleteTarget,setDeleteTarget]=useState<Integration|null>(null);
 const [deleteConfirm,setDeleteConfirm]=useState('');
 const [workbench,setWorkbench]=useState<any>(null);
 const [importAnalysis,setImportAnalysis]=useState<any>(null);
 const [importConnection,setImportConnection]=useState<Integration|null>(null);
 const fileRef=useRef<HTMLInputElement>(null);
 const load=()=>Promise.all([api<Integration[]>('/integrations'),api<DaytonStatus>('/integrations/dayton')]).then(([a,b])=>{setRows(a);setDayton(b)});
 useEffect(()=>{const timer=setInterval(()=>load().catch(e=>setMessage(e.message)),60000);return()=>clearInterval(timer)},[companyId]);
 useEffect(()=>{setRows([]);setDayton(null);setShowDayton(false);setShowGeneric(false);setShowImport(false);setManaged(null);setDeleteTarget(null);setMessage('');load().then(()=>{const x=pendingManage.current;pendingManage.current=null;if(x){if(x.provider==='Dayton Freight')openDayton();else openGeneric(x)}}).catch(e=>setMessage(e.message))},[companyId]);
 const groups=useMemo(()=>Object.entries(rows.reduce((a:any,x:any)=>((a[x.category]??=[]).push(x),a),{})),[rows]);
 const openDayton=()=>{setWorkbench(null);setShowDayton(true)};
 const openImport=()=>{setImportAnalysis(null);setImportConnection(null);setShowImport(true)};

 function manageRow(x:Integration){const scope=String(x.customer_id||'');if(user?.role==='admin'&&scope!==companyId){pendingManage.current=x;setCompanyId(scope);return}if(x.provider==='Dayton Freight')openDayton();else openGeneric(x)}
 async function openGeneric(x:Integration){setBusy(true);setMessage('');try{const r=await api<ManagedConnection>(`/integrations/connection/${x.id}/manage`);setManaged(r);setShowGeneric(true)}catch(e:any){setMessage(e.message)}finally{setBusy(false)}}
 async function test(id:number){setBusy(true);setMessage('');try{const r:any=await api(`/integrations/connection/${id}/test`,{method:'POST'});setMessage(r.message||'Connection test completed')}catch(e:any){setMessage(e.message)}finally{setBusy(false);load()}}
 async function testDayton(){if(!dayton)return;setBusy(true);setMessage('');try{const r:any=await api('/integrations/dayton/test',{method:'POST'});setMessage(r.message);setWorkbench(r)}catch(e:any){setMessage(e.message)}finally{setBusy(false);load()}}

 async function saveDaytonConfig(e:any){
  e.preventDefault();
  const form=e.currentTarget as HTMLFormElement;
  const f=new FormData(form);
  setBusy(true);setMessage('');
  try{
   await api('/integrations/dayton/config',{method:'PATCH',body:JSON.stringify({environment:f.get('environment'),base_url:String(f.get('base_url')||'https://api.daytonfreight.com'),account:String(f.get('account')||'')||null,terms:f.get('terms'),direct_only:f.get('direct_only')==='on'})});
   const username=String(f.get('username')||'').trim();const password=String(f.get('password')||'');
   if(username||password||dayton?.credential_status?.configured){
    await api(`/integrations/connection/${dayton!.id}/credentials`,{method:'PUT',body:JSON.stringify({auth_type:'basic_auth',username:username||undefined,password:password||undefined})});
   }
   const passwordInput=form.querySelector('input[name="password"]') as HTMLInputElement|null;if(passwordInput)passwordInput.value='';
   const usernameInput=form.querySelector('input[name="username"]') as HTMLInputElement|null;if(usernameInput)usernameInput.value='';
   await load();
   setMessage('Dayton adapter configuration saved securely. Saved credentials remain encrypted on the server; the password is intentionally never displayed again.');
  }catch(err:any){setMessage(err.message)}finally{setBusy(false)}
 }

 async function removeDaytonCredentials(){if(!dayton||!confirm('Remove the saved Dayton Freight credentials from Valhalla Freight?'))return;setBusy(true);try{await api(`/integrations/connection/${dayton.id}/credentials`,{method:'DELETE'});setMessage('Dayton credentials removed.');await load()}catch(e:any){setMessage(e.message)}finally{setBusy(false)}}

 async function saveGeneric(e:any){
  e.preventDefault();if(!managed)return;const f=new FormData(e.currentTarget);setBusy(true);setMessage('');
  try{
   const authType=String(f.get('auth_type')||'none');
   const baseUrl=String(f.get('base_url')||'').trim();
   await api(`/integrations/connection/${managed.connection.id}`,{method:'PATCH',body:JSON.stringify({environment:f.get('environment'),settings:{...(managed.connection.settings||{}),base_url:baseUrl,detected_auth_type:authType}})});
   const payload:any={auth_type:authType};
   for(const key of ['username','password','api_key','bearer_token','client_id','client_secret']){const value=String(f.get(key)||'').trim();if(value)payload[key]=value}
   if(authType!=='none') await api(`/integrations/connection/${managed.connection.id}/credentials`,{method:'PUT',body:JSON.stringify(payload)});
   const refreshed=await api<ManagedConnection>(`/integrations/connection/${managed.connection.id}/manage`);setManaged(refreshed);setMessage(`${managed.connection.provider} adapter settings saved.`);await load();
  }catch(e:any){setMessage(e.message)}finally{setBusy(false)}
 }

 async function removeGenericCredentials(){if(!managed||!confirm(`Remove saved credentials for ${managed.connection.provider}?`))return;setBusy(true);try{await api(`/integrations/connection/${managed.connection.id}/credentials`,{method:'DELETE'});const refreshed=await api<ManagedConnection>(`/integrations/connection/${managed.connection.id}/manage`);setManaged(refreshed);setMessage('Credentials removed.')}catch(e:any){setMessage(e.message)}finally{setBusy(false);load()}}

 function requestDelete(x:Integration){
  if(x.provider==='Dayton Freight'&&user?.role!=='admin'){setMessage('Dayton Freight is a built-in Valhalla carrier adapter and cannot be deleted. You can remove its saved credentials instead.');return}
  setDeleteConfirm('');setDeleteTarget(x);
 }
 async function deleteAdapter(){
  if(!deleteTarget||deleteConfirm!==deleteTarget.provider)return;
  setBusy(true);setMessage('');
  try{
   const name=deleteTarget.provider;
   await api(`/integrations/connection/${deleteTarget.id}`,{method:'DELETE'});
   setDeleteTarget(null);setDeleteConfirm('');setShowGeneric(false);setManaged(null);
   await load();setMessage(`${name} provider adapter was permanently deleted.`);
  }catch(e:any){setMessage(e.message)}finally{setBusy(false)}
 }

 async function runRate(e:any){e.preventDefault();setBusy(true);setMessage('');const f=new FormData(e.currentTarget);try{const r=await api('/integrations/dayton/rate-test',{method:'POST',body:JSON.stringify({origin_zip:f.get('origin'),destination_zip:f.get('destination'),freight_class:f.get('class'),weight_lbs:Number(f.get('weight')),quantity:Number(f.get('qty'))})});setWorkbench(r)}catch(e:any){setMessage(e.message)}finally{setBusy(false)}}
 async function runTracking(e:any){e.preventDefault();setBusy(true);setMessage('');const f=new FormData(e.currentTarget);try{const r=await api('/integrations/dayton/tracking-test',{method:'POST',body:JSON.stringify({number:f.get('number'),type:f.get('type')})});setWorkbench(r)}catch(e:any){setMessage(e.message)}finally{setBusy(false)}}
 async function safePickup(){setBusy(true);setMessage('');try{const r=await api('/integrations/dayton/pickup-test',{method:'POST'});setWorkbench(r);setMessage('Dayton TESTING pickup request completed without creating a live pickup.')}catch(e:any){setMessage(e.message)}finally{setBusy(false)}}
 async function importOpenApi(file:File){setBusy(true);setMessage('');try{const spec=JSON.parse(await file.text());const r:any=await api('/integrations/openapi/import',{method:'POST',body:JSON.stringify({specification:spec})});setImportAnalysis(r.analysis);setImportConnection(r.connection);setMessage(`Imported ${r.analysis.endpoint_count} API operations from ${r.analysis.title}.`);await load()}catch(e:any){setMessage(e.message||'Unable to import OpenAPI specification')}finally{setBusy(false);if(fileRef.current)fileRef.current.value=''}}

 return <>{user?.role==='admin'&&<div className="companyScope"><b>Integration account</b><select disabled={busy} value={companyId} onChange={e=>setCompanyId(e.target.value)}><option value="">Valhalla Freight / All integration accounts</option>{companies.map(c=><option key={c.id} value={c.id}>{c.name}</option>)}</select><span>Choose a company to configure its API connections.</span></div>}
  <PageHead eyebrow="ADMINISTRATION / CONNECTIVITY" title="Carrier Integration Hub" sub="Import carrier APIs, configure authentication securely, test connectivity, and let Valhalla normalize live carrier services without hard-coded credentials." actions={<><button type="button" className="btn secondary" onClick={openImport}><FileJson size={15}/>Import OpenAPI</button><button type="button" className="btn primary" onClick={openDayton}><Truck size={15}/>Dayton Freight</button></>}/>

  <div className="integrationGuide">
   <div><Settings2/><span><b>Manage adapter</b>Configure environment, base URL, authentication, commercial settings and diagnostics from the software.</span></div>
   <div><FileSearch/><span><b>Import OpenAPI</b>Upload Swagger/OpenAPI JSON. Valhalla discovers endpoints, capability areas and published security schemes.</span></div>
   <div><LockKeyhole/><span><b>Secure credentials</b>Secrets are encrypted server-side. Saved passwords/API keys are never returned to the browser or committed to GitHub.</span></div>
  </div>

  <div className="integrationSummary"><Card><PlugZap/><div><b>{rows.length}</b><span>Provider definitions</span></div></Card><Card><PlugZap/><div><b>{rows.filter(x=>x.adapter_available).length}</b><span>Live adapters installed</span></div></Card><Card><CheckCircle2/><div><b>{rows.filter(x=>x.credentials_configured).length}</b><span>Credentials configured</span></div></Card><Card><RefreshCw/><div><b>{rows.filter(x=>x.live_healthy).length}</b><span>Live check current (15 min)</span></div></Card></div>

  <Card className="daytonSpotlight">
   <div className="daytonBrand"><div className="daytonLogo">DF</div><div><span>FIRST DIRECT CARRIER ADAPTER</span><h2>Dayton Freight Lines</h2><p>DAFG · REST API · Basic Auth · JSON-first</p></div></div>
   <div className="daytonStatus"><Pill tone={dayton?.credentials_configured?'success':'warning'}>{dayton?.credentials_configured?'Credentials configured':'Credentials required'}</Pill><b>{dayton?.credentials_configured?'LIVE READY':'ADAPTER CONFIGURED'}</b></div>
   <div className="daytonCapabilities">{dayton?.capability_details?.map(x=><div key={x.key}><ShieldCheck/><span>{x.label}</span><CheckCircle2/></div>)}</div>
   <div className="daytonActions"><button type="button" className="btn secondary" onClick={openDayton}><Settings2 size={14}/>Open adapter</button><button type="button" className="btn primary" disabled={busy} onClick={testDayton}><Radio size={14}/>Test connection</button></div>
  </Card>

  {message&&<div className="integrationNotice">{message}</div>}

  <p className="statusStages">Adapter available → Credentials configured → Live connection verified → Healthy (successful check within 15 minutes). Imported specifications and configuration reviews do not verify live service health.</p><div className="integrationGroups">{groups.map(([category,items]:any)=><Card key={category}><div className="integrationGroupHead"><div><span>INTEGRATION CATEGORY</span><h3>{category}</h3></div><Pill tone="neutral">{items.length} adapters</Pill></div><div className="integrationCards">{items.map((x:Integration)=>{const isDayton=x.provider==='Dayton Freight';return <div className={`integrationCard ${isDayton?'featured':''}`} key={x.id}><div className="providerMark">{x.provider.slice(0,2).toUpperCase()}</div><div className="providerInfo"><b>{x.provider}</b>{user?.role==='admin'&&<small>{x.customer_id?companies.find(c=>c.id===x.customer_id)?.name||`Company #${x.customer_id}`:'Valhalla Freight'}</small>}<span>{x.capabilities?.length?x.capabilities.join(' · '):'Connector framework'}</span><small>{x.adapter_available?'Live adapter installed':'Provider definition · live calls not implemented'}</small></div><div><Pill tone={x.live_healthy?'success':'warning'}>{(x.state||'not_verified').replaceAll('_',' ')}</Pill><small className="cellSub">Last successful live check: {x.last_success_at?displayDateTime(x.last_success_at):'Never'}</small></div><div className="integrationCardActions"><button type="button" onClick={()=>manageRow(x)}><Settings2/> Manage</button>{(!isDayton||user?.role==='admin')&&<button type="button" className="dangerIconBtn" title="Delete provider adapter" aria-label={`Delete ${x.provider}`} onClick={()=>requestDelete(x)}><Trash2/></button>}</div></div>})}</div></Card>)}</div>

  {showDayton&&dayton&&<div className="vfModalBackdrop" onMouseDown={()=>setShowDayton(false)}><div className="vfModal vfIntegrationModal" onMouseDown={e=>e.stopPropagation()}>
   <div className="vfModalHead"><div><span>DAFG / CARRIER API</span><h2>Dayton Freight Adapter</h2><p>Complete production configuration, secure credentials and API testing inside Valhalla Freight.</p></div><button type="button" aria-label="Close Dayton adapter" onClick={()=>setShowDayton(false)}><X/></button></div>
   <div className="vfModalBody">
    <div className="adapterHero"><DatabaseZap/><div><b>{dayton.adapter_installed?'Adapter installed':'Adapter unavailable'}</b><span>{dayton.base_url}</span></div><Pill tone={dayton.credentials_configured?'success':'warning'}>{dayton.credentials_configured?'LIVE READY':'AWAITING CREDENTIALS'}</Pill></div>
    <div className="adapterPurpose"><Info/><div><b>Production carrier control room</b><p>Configure and test Dayton here. Authentication confirms credentials only. Before a live pilot, prove booking, carrier tracking, delivery/POD and invoicing on the same shipment. Sandbox requests do not confirm a live booking.</p></div></div>
    <div className="adapterGrid">
     <Card><h3>Credentials & authentication</h3><form className="daytonConfigForm credentialForm" onSubmit={saveDaytonConfig}>
      <label>Authentication type<input value="Basic Authentication" disabled/></label>
      <label>API base URL<input name="base_url" defaultValue={dayton.base_url||'https://api.daytonfreight.com'} /></label>
      <label>Environment<select name="environment" defaultValue={dayton.environment||'sandbox'}><option value="sandbox">Sandbox / Test</option><option value="production">Production</option></select></label>
      <label>Dayton username<input name="username" autoComplete="off" placeholder={dayton.username_hint?`Saved securely: ${dayton.username_hint}`:'Enter Dayton web username'}/><small>{dayton.username_hint?<>✓ Username saved as <b>{dayton.username_hint}</b>. Enter a new username only to replace it.</>:<>Dayton uses the first 10 characters when authenticating.</>}</small></label>
      <label>Password<div className="secretInput"><input name="password" type={showPassword?'text':'password'} autoComplete="new-password" placeholder={dayton.credential_status?.has_password?'••••••••  Saved securely — blank keeps current':'Enter Dayton password'}/><button type="button" onClick={()=>setShowPassword(v=>!v)}>{showPassword?<EyeOff/>:<Eye/>}</button></div><small>{dayton.credential_status?.has_password?'✓ Password is saved and encrypted. It is intentionally never loaded back into this field.':'Enter the Dayton web password.'}</small></label>
      <label>Dayton customer account<input name="account" defaultValue={dayton.account||''} placeholder="0000031"/></label>
      <label>Freight terms<select name="terms" defaultValue={dayton.settings?.terms||'ThirdPartyPrepaid'}><option>ThirdPartyPrepaid</option><option>Prepaid</option><option>Collect</option><option>ThirdPartyCollect</option></select></label>
      <label className="checkLine"><input type="checkbox" name="direct_only" defaultChecked={Boolean(dayton.settings?.direct_only)}/> Direct rates only</label>
      <div className="credentialActions"><button className="btn primary" disabled={busy}><Save size={14}/>Save configuration</button>{dayton.credential_status?.configured&&<button type="button" className="btn danger" onClick={removeDaytonCredentials} disabled={busy}><Trash2 size={14}/>Remove credentials</button>}</div>
     </form>
     <div className="secureStorageNote"><LockKeyhole/><div><b>Encrypted server-side storage</b><p>Credentials are encrypted before they are written to PostgreSQL. Valhalla never sends the saved password back to this page. For production, set a unique <code>INTEGRATION_SECRET_KEY</code> on the backend.</p></div></div>
     <button type="button" className="btn secondary wide" onClick={testDayton} disabled={busy}><Activity size={14}/>Test Dayton authentication</button></Card>
     <Card><h3>Adapter status</h3><div className="adapterField"><span>Credential source</span><b>{dayton.credential_source}</b></div><div className="adapterField"><span>Username</span><b>{dayton.username_hint||'Not configured'}</b></div><div className="adapterField"><span>Account</span><b>{dayton.account||'Not configured'}</b></div><div className="adapterField"><span>Status</span><b>{(dayton.state||'not_verified').replaceAll('_',' ')}</b></div><h3 className="subHead">Supported operations</h3><div className="capabilityChecklist">{dayton.capability_details.map(x=><div key={x.key}><CheckCircle2/><span>{x.label}</span></div>)}</div><div className="credentialsExplainer"><KeyRound/><div><b>Configured vs. connected</b><p>Saving credentials makes the adapter configured. A successful carrier authentication test verifies the connection. Live health is current for 15 minutes and includes the last successful check.</p></div></div></Card>
    </div>
    <div className="apiWorkbench"><h3>Dayton API Workbench</h3><p>These diagnostics use the exact encrypted credentials saved above. Credentials never enter the response payload.</p><div className="workbenchGrid"><form onSubmit={runRate}><b>Live rate test</b><div className="miniForm"><input name="origin" placeholder="Origin ZIP" required/><input name="destination" placeholder="Destination ZIP" required/><input name="class" defaultValue="70" placeholder="Class"/><input name="weight" type="number" defaultValue="500"/><input name="qty" type="number" defaultValue="1"/></div><button className="btn secondary" disabled={busy}><PlayCircle size={14}/>Run rate test</button></form><form onSubmit={runTracking}><b>Tracking test</b><div className="miniForm"><select name="type"><option>Pro</option><option>BillOfLading</option><option>PurchaseOrder</option><option>Pickup</option><option>PSID</option></select><input name="number" placeholder="Tracking number" required/></div><button className="btn secondary" disabled={busy}><PlayCircle size={14}/>Track shipment</button></form><div className="pickupTest"><b>Safe pickup connectivity test</b><p>Uses Dayton's documented TESTING reference so a live pickup is not created.</p><button type="button" className="btn secondary" onClick={safePickup} disabled={busy}><PlayCircle size={14}/>Run TESTING pickup</button></div></div></div>
    {workbench&&<div className="adapterResponse"><div><b>Latest adapter response</b><button type="button" onClick={()=>setWorkbench(null)}>Clear</button></div><pre>{JSON.stringify(workbench,null,2)}</pre></div>}
   </div>
  </div></div>}

  {showGeneric&&managed&&<div className="vfModalBackdrop" onMouseDown={()=>setShowGeneric(false)}><div className="vfModal genericAdapterModal" onMouseDown={e=>e.stopPropagation()}>
   <div className="vfModalHead"><div><span>PROVIDER ADAPTER</span><h2>{managed.connection.provider}</h2><p>Configure the API connection discovered by Valhalla.</p></div><button type="button" onClick={()=>setShowGeneric(false)}><X/></button></div>
   <div className="vfModalBody"><div className="adapterPurpose"><ServerCog/><div><b>Imported API candidate</b><p>OpenAPI import discovers the provider surface. This screen stores its connection settings and credentials securely while a carrier-specific normalization adapter is developed.</p></div></div>
    <form className="genericCredentialForm" onSubmit={saveGeneric}>
     <label>Environment<select name="environment" defaultValue={managed.connection.environment||'sandbox'}><option value="sandbox">Sandbox / Test</option><option value="production">Production</option></select></label>
     <label>API base URL<input name="base_url" defaultValue={managed.connection.settings?.base_url||''} placeholder="https://api.carrier.com"/></label>
     <label>Authentication type<select name="auth_type" defaultValue={managed.credentials.auth_type||managed.connection.settings?.detected_auth_type||'none'}><option value="none">No authentication</option><option value="basic_auth">Basic Authentication</option><option value="api_key">API Key</option><option value="bearer_token">Bearer Token</option><option value="oauth2">OAuth 2.0</option><option value="client_credentials">Client ID / Secret</option></select></label>
     <div className="genericSecrets"><label>Username<input name="username" placeholder={managed.credentials.username_hint?`Saved: ${managed.credentials.username_hint}`:'Optional / Basic Auth'}/></label><label>Password<input name="password" type="password" placeholder={managed.credentials.has_password?'Saved — blank keeps current':'Optional / Basic Auth'}/></label><label>API Key<input name="api_key" type="password" placeholder={managed.credentials.has_api_key?'Saved — blank keeps current':'Optional / API Key'}/></label><label>Bearer Token<input name="bearer_token" type="password" placeholder={managed.credentials.has_bearer_token?'Saved — blank keeps current':'Optional / Bearer'}/></label><label>Client ID<input name="client_id" placeholder={managed.credentials.client_id_hint?`Saved: ${managed.credentials.client_id_hint}`:'Optional / OAuth'}/></label><label>Client Secret<input name="client_secret" type="password" placeholder={managed.credentials.has_client_secret?'Saved — blank keeps current':'Optional / OAuth'}/></label></div>
     <div className="credentialActions"><button className="btn primary" disabled={busy}><Save size={14}/>Save adapter configuration</button>{managed.credentials.configured&&<button type="button" className="btn danger" onClick={removeGenericCredentials}><Trash2 size={14}/>Remove credentials</button>}<button type="button" className="btn secondary" onClick={()=>test(managed.connection.id)}><Radio size={14}/>Configuration health check</button></div>
    </form>
    <div className="secureStorageNote"><LockKeyhole/><div><b>Credential status: {managed.credentials.configured?'Encrypted credentials saved':'No saved credentials'}</b><p>Detected authentication: {authLabel(managed.connection.settings?.detected_auth_type||managed.credentials.auth_type||'none')}. Imported providers require a normalization adapter before Valhalla will make live operational calls.</p></div></div>
    <div className="adapterDangerZone"><div><Trash2/><span><b>Danger zone</b><p>Delete this imported provider adapter, its saved credentials, settings, and Integration Hub registration.</p></span></div><button type="button" className="btn danger" onClick={()=>requestDelete(managed.connection)}><Trash2 size={14}/>Delete provider adapter</button></div>
   </div>
  </div></div>}

  {showImport&&<div className="vfModalBackdrop" onMouseDown={()=>setShowImport(false)}><div className="vfModal openApiModal" onMouseDown={e=>e.stopPropagation()}>
   <div className="vfModalHead"><div><span>INTEGRATION ONBOARDING</span><h2>Import OpenAPI specification</h2><p>Discover a carrier API and immediately prepare its connection profile.</p></div><button type="button" aria-label="Close OpenAPI import" onClick={()=>setShowImport(false)}><X/></button></div>
   <div className="vfModalBody">
    {!importAnalysis?<><div className="openApiPurpose"><Info/><div><b>What this importer does</b><p>Valhalla reads API metadata, paths, methods, capability groups, server URLs and published authentication schemes. It then registers a provider adapter candidate that can be configured from the Integration Hub.</p></div></div><div className="openApiDrop" onClick={()=>!busy&&fileRef.current?.click()}><Upload/><h3>Upload swagger.json or openapi.json</h3><p>After import, configure the provider's URL and credentials entirely through Valhalla Freight.</p><input ref={fileRef} type="file" accept=".json,application/json" hidden onChange={e=>e.target.files?.[0]&&importOpenApi(e.target.files[0])}/><button type="button" className="btn primary" disabled={busy}>{busy?'Analyzing specification…':'Choose API specification'}</button></div></>:<div className="openApiResult"><CheckCircle2/><span>OPENAPI IMPORT COMPLETE</span><h3>{importAnalysis.title}</h3><p>{importAnalysis.endpoint_count} API operations discovered and registered for adapter onboarding.</p><div className="openApiStats"><div><b>{importAnalysis.endpoint_count}</b><span>Operations</span></div><div><b>{importAnalysis.tags?.length||Object.keys(importAnalysis.tags||{}).length}</b><span>Capability groups</span></div><div><b>{authLabel(importAnalysis.detected_auth_type||'none')}</b><span>Detected auth</span></div></div><div className="tagCloud">{Object.keys(importAnalysis.tags||{}).map((t:string)=><span key={t}>{t}</span>)}</div><div className="credentialActions"><button type="button" className="btn secondary" onClick={()=>setShowImport(false)}>Done</button>{importConnection&&<button type="button" className="btn primary" onClick={()=>{setShowImport(false);importConnection.provider==='Dayton Freight'?openDayton():openGeneric(importConnection)}}><Settings2 size={14}/>Configure adapter</button>}</div></div>}
   </div>
  </div></div>}

  {deleteTarget&&<div className="vfModalBackdrop dangerBackdrop" onMouseDown={()=>setDeleteTarget(null)}><div className="vfModal deleteAdapterModal" onMouseDown={e=>e.stopPropagation()}>
   <div className="vfModalHead dangerHead"><div><span>DANGER ZONE</span><h2>Delete provider adapter?</h2><p>This action permanently removes the imported API connection from Valhalla Freight.</p></div><button type="button" onClick={()=>setDeleteTarget(null)}><X/></button></div>
   <div className="vfModalBody">
    <div className="deleteWarning"><Trash2/><div><b>This cannot be undone.</b><p><strong>{deleteTarget.provider}</strong> will be removed from the Integration Hub along with its encrypted credentials and saved adapter settings. Historical shipment data is not deleted.</p></div></div>
    <label className="deleteConfirmLabel">Type <b>{deleteTarget.provider}</b> to confirm<input value={deleteConfirm} onChange={e=>setDeleteConfirm(e.target.value)} autoFocus placeholder={deleteTarget.provider}/></label>
    <div className="deleteModalActions"><button type="button" className="btn secondary" onClick={()=>setDeleteTarget(null)}>Cancel</button><button type="button" className="btn danger" disabled={busy||deleteConfirm!==deleteTarget.provider} onClick={deleteAdapter}><Trash2 size={14}/>{busy?'Deleting…':'Permanently delete adapter'}</button></div>
   </div>
  </div></div>}
 </>;
}
