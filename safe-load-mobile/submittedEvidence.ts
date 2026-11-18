export type SavedAttempt={id:number;revision:number;has_back_photo:boolean;created_at?:string};
export type EvidenceContext={shipmentId:number;revision:number};
export type EvidenceKind='license'|'license-back'|'vin';
export type SavedEvidence=EvidenceContext&{attempt:SavedAttempt;photos?:Partial<Record<EvidenceKind,string>>;errors?:Partial<Record<EvidenceKind,string>>};
const labels:Record<EvidenceKind,string>={'license':'Front ID','license-back':'Back ID','vin':'Truck VIN'};
function sameContext(saved:SavedEvidence|undefined,context:EvidenceContext){return !!saved&&saved.shipmentId===context.shipmentId&&saved.revision===context.revision&&saved.attempt.revision===context.revision&&Number.isSafeInteger(saved.attempt.id)&&saved.attempt.id>0}
/** Image receives local/data URIs only. Protected HTTP requests go through the authenticated API client. */
export function evidenceSource(localUri:string,saved:SavedEvidence|undefined,kind:EvidenceKind,context:EvidenceContext,token:string,submittedUri=''){
 if(!token)return undefined;
 const canonical=sameContext(saved,context)?saved?.photos?.[kind]:undefined;
 if(canonical&&localUri&&localUri===submittedUri)return {uri:canonical};
 if(localUri)return {uri:localUri};
 if(!sameContext(saved,context)||kind==='license-back'&&!saved!.attempt.has_back_photo)return undefined;
 const uri=saved?.photos?.[kind];return uri?{uri}:undefined;
}
export function currentAttempt(attempts:SavedAttempt[],revision:number){return attempts.find(a=>a.revision===revision)}
export function checkedPhoto(data:any,saved:SavedEvidence,kind:EvidenceKind){
 if(data?.shipment_id!==saved.shipmentId||data?.attempt_id!==saved.attempt.id||data?.revision!==saved.revision||data?.kind!==kind)throw Error('Photo response belongs to a different shipment or assignment. Refresh this load.');
 if(typeof data.data_uri!=='string'||data.data_uri.length>16000000||!/^data:image\/jpeg;base64,[A-Za-z0-9+/]+={0,2}$/.test(data.data_uri))throw Error('Server did not return a valid photo preview. Update/rebuild the backend and retry.');
 return data.data_uri as string;
}
export async function loadSubmittedPhotos(saved:SavedEvidence,request:(path:string)=>Promise<any>,isCurrent:()=>boolean=()=>true,onUpdate?:(value:SavedEvidence)=>void){
 let state:SavedEvidence={...saved,photos:{},errors:{}};
 // Each protected read records a custody view. Keep these sequential rather
 // than making concurrent writes to one shipment's custody chain.
 const kinds:EvidenceKind[]=['license',...(saved.attempt.has_back_photo?['license-back' as const]:[]),'vin'];
 for(const kind of kinds){
  if(!isCurrent())return undefined;
  try{
   const data=await request(`/safe-load/shipments/${saved.shipmentId}/attempts/${saved.attempt.id}/${kind}/photo-data`);
   if(!isCurrent())return undefined;
   state={...state,photos:{...state.photos,[kind]:checkedPhoto(data,saved,kind)}};
  }catch(e:any){
   if(!isCurrent())return undefined;
   state={...state,errors:{...state.errors,[kind]:`${labels[kind]}: ${e?.message||'Saved photo could not be loaded'}`}};
  }
  onUpdate?.(state);
 }
 return state;
}
