import type {BarcodeType} from 'expo-camera';
type Bridge={onModernBarcodeScanned:(listener:(event:{data:string})=>void)=>{remove:()=>void};launchScanner:(options:{barcodeTypes:BarcodeType[]})=>Promise<void>;dismissScanner:()=>Promise<void>};
/** A native scanner launch completing is not the barcode result event. */
export function nativeBarcodeSession(bridge:Bridge,types:BarcodeType[],decode:(raw:string)=>Promise<any>){
 let done=false,reading=false;let remove=()=>{};let timer:ReturnType<typeof setTimeout>;let stop:(error:Error)=>void=()=>{};
 const result=new Promise<any>((resolve,reject)=>{
  const finish=(error:Error|null,value?:any)=>{if(done)return;done=true;clearTimeout(timer);remove();if(error)reject(error);else resolve(value)};
  stop=error=>finish(error);
  const subscription=bridge.onModernBarcodeScanned(event=>{if(done||reading)return;reading=true;void decode(event.data).then(value=>finish(null,value)).catch(error=>finish(error))});
  remove=()=>subscription.remove();
  timer=setTimeout(()=>finish(new Error('No barcode returned. Retry or use the live preview.')),90000);
  try{void bridge.launchScanner({barcodeTypes:types}).catch(error=>finish(error))}catch(error){finish(error as Error)}
 });
 return {result:result.finally(()=>{void bridge.dismissScanner().catch(()=>{})}),cancel:()=>stop(new Error('Native scan cancelled'))};
}
