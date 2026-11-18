import {File} from 'expo-file-system';
import {fetch as expoFetch} from 'expo/fetch';

type ArrivalPhotos={server:string;token:string;shipmentId:number;revision:number;idUri:string;vinUri:string;idCapturedAt:string;vinCapturedAt:string;licenseBarcode?:string;vinBarcode?:string;uploadId?:string;backUri?:string};
function cameraFile(uri:string,label:string){
 if(!uri)throw new Error(`Take the ${label} photo before submitting.`);
 const file=new File(uri);
 if(!file.exists||file.size===0)throw new Error(`The ${label} camera photo is no longer available. Retake it and submit again.`);
 if(file.size>8*1024*1024)throw new Error(`The ${label} photo exceeds 8 MB. Retake it closer to the document with all text in frame.`);
 return file;
}
export async function uploadArrivalPhotos(input:ArrivalPhotos){
 // SDK58 fetch serializes Blob/File bytes, not React Native's legacy {uri,name,type} parts.
 if(input.backUri){
  let supported=false;
  try{const check=await expoFetch(input.server.replace(/\/$/,'')+'/api/v1/safe-load/capture-features',{headers:{Authorization:'Bearer '+input.token}});supported=check.ok&&(await check.json()).id_back_photo===true}catch{}
  if(!supported)throw new Error('The backend must be updated/rebuilt before submitting an ID back photo. Your photos are retained.');
 }
 const id=cameraFile(input.idUri,'driver ID'),vin=cameraFile(input.vinUri,'truck VIN');
 const data=new FormData();
 data.append('revision',String(input.revision));
 data.append('capture_source','native_camera');
 data.append('license_captured_at',input.idCapturedAt);
 data.append('vin_captured_at',input.vinCapturedAt);
 if(input.licenseBarcode)data.append('license_barcode',input.licenseBarcode);
 if(input.vinBarcode)data.append('vin_barcode',input.vinBarcode);
 if(input.uploadId)data.append('upload_id',input.uploadId);
 data.append('license_photo',id);
 data.append('vin_photo',vin);
 if(input.backUri)data.append('license_back_photo',cameraFile(input.backUri,'ID back'));
 let response:Response;
 try{
  // Let Expo generate the multipart boundary; a manually set Content-Type would break uploads.
  response=await expoFetch(input.server.replace(/\/$/,'')+`/api/v1/safe-load/shipments/${input.shipmentId}/photo-review`,{method:'POST',headers:{Authorization:'Bearer '+input.token},body:data});
 }catch{
  throw new Error('Photo upload did not complete. Your photos are retained. Check the TMS server connection and retry; refresh the load if the server already received it.');
 }
 let result:any;
 try{result=await response.json()}catch{
  throw new Error(`Photo upload returned HTTP ${response.status} without a readable result. Your photos are retained; refresh the load before retrying.`);
 }
 if(!response.ok){
  const detail=typeof result.detail==='string'?result.detail:Array.isArray(result.detail)?result.detail.map((e:any)=>`${(e.loc||[]).filter((v:any)=>v!=='body').join('.')}: ${e.msg}`).join(' · '):`Server returned HTTP ${response.status}`;
  throw new Error(`Photo submission failed: ${detail}. Your photos are retained for retry.`);
 }
 return result;
}
