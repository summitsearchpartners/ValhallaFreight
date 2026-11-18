import {File} from 'expo-file-system';
import {fetch} from 'expo/fetch';
export class CameraRequestError extends Error{constructor(message:string,public status=0){super(message)}}
export type CameraContext={server:string;token:string;shipmentId:number;revision:number};
export async function cameraRequest(context:CameraContext,path:string,init:RequestInit){
 let response:Response;
 try{response=await fetch(context.server.replace(/\/$/,'')+`/api/v1/safe-load/shipments/${context.shipmentId}/`+path,{...init,headers:{Authorization:'Bearer '+context.token,...init.headers}})}catch{throw new CameraRequestError('Camera checker cannot reach the TMS server. Check the connection and retry.')}
 let result:any;
 try{result=await response.json()}catch{throw new CameraRequestError(`Camera checker returned an unreadable response (HTTP ${response.status}). Retry or cancel.`,response.status)}
 if(!response.ok)throw new CameraRequestError(typeof result.detail==='string'?result.detail:`Camera request failed (HTTP ${response.status})`,response.status);
 return result;
}
export async function decodeLiveBarcode(context:CameraContext,kind:'license'|'vin',barcode:string){
 const result=await cameraRequest(context,kind+'-barcode/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({revision:context.revision,barcode})});
 if(kind==='license'&&!result.complete)throw new CameraRequestError('Scan the entire PDF417 barcode; required ID fields are missing',422);
 return {...result,barcode:kind==='license'?barcode:result.vin};
}
export async function inspectCameraFrame(context:CameraContext,uri:string,kind:'idPhoto'|'license'|'vin'){
 const file=new File(uri);
 if(!file.exists||file.size===0)throw new CameraRequestError('Camera image is unavailable. Retake it.');
 if(file.size>8*1024*1024)throw new CameraRequestError('Camera frame is over 8 MB; reduce camera resolution.');
 const body=new FormData();body.append('revision',String(context.revision));body.append('frame',file);
 if(kind!=='idPhoto')body.append('kind',kind);
 return cameraRequest(context,kind==='idPhoto'?'capture-readiness':'barcode-frame',{method:'POST',body});
}
