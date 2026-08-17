import {useState} from 'react';
import {Upload,FileSpreadsheet,X,CheckCircle2,AlertTriangle} from 'lucide-react';
import {dashboardApi} from '../api';
export default function ImportFreightModal({onClose,onImported}:{onClose:()=>void;onImported:()=>void}){
 const [file,setFile]=useState<File|null>(null),[loading,setLoading]=useState(false),[result,setResult]=useState<any>(null),[error,setError]=useState('');
 async function run(){if(!file)return;setLoading(true);setError('');try{const r=await dashboardApi.importFreight(file);setResult(r);if(r.imported>0)onImported()}catch(e:any){setError(e.message)}finally{setLoading(false)}}
 return <div className="modalShade"><div className="entityModal importModal"><div className="entityModalHead"><div className="entityModalIcon"><Upload/></div><div><span>COMMAND CENTER</span><h2>Import freight</h2></div><button onClick={onClose}><X/></button></div><div className="importBody">
   <div className="importDrop"><FileSpreadsheet/><h3>Import historical or active shipment records</h3><p>Upload CSV, XLSX, or XLS. Valhalla Freight matches customers by <b>customer_code</b> or <b>customer</b> name and carriers by SCAC.</p><label className="btn primary filebtn"><Upload size={15}/>{file?file.name:'Choose freight file'}<input type="file" accept=".csv,.xlsx,.xls" onChange={e=>{setFile(e.target.files?.[0]||null);setResult(null)}}/></label></div>
   <div className="importColumns"><b>Recommended columns</b><p>customer_code, carrier_scac, shipment_number, status, pro_number, origin_address, origin_city, origin_state, origin_zip, destination_address, destination_city, destination_state, destination_zip, customer_charge, carrier_cost, final_carrier_cost, pickup_date, estimated_delivery, delivered_at</p></div>
   {error&&<div className="importResult error"><AlertTriangle/>{error}</div>}
   {result&&<div className="importResult success"><CheckCircle2/><div><b>{result.imported} shipments imported</b><span>{result.skipped} skipped</span>{result.errors?.length>0&&<details><summary>View import issues</summary>{result.errors.map((x:string,i:number)=><p key={i}>{x}</p>)}</details>}</div></div>}
 </div><div className="entityModalFoot"><button className="btn secondary" onClick={onClose}>Close</button><button className="btn primary" disabled={!file||loading} onClick={run}>{loading?'Importing…':'Import freight'}</button></div></div></div>
}
