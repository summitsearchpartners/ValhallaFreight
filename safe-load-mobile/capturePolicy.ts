export type Stability={box:number[]|null;count:number};
export function captureStability(previous:Stability,ready:boolean,box:number[]|null):Stability{
 if(!ready||!box||box.length!==4||box.some(v=>!Number.isFinite(v)))return {box:null,count:0};
 const stable=previous.box?.length===4&&box.every((v,i)=>Math.abs(v-previous.box![i])<.045);
 return {box,count:stable?previous.count+1:1};
}
export function choosePictureSize(sizes:string[]){
 return sizes.map(value=>({value,parts:value.split('x').map(Number)})).filter(s=>s.parts.length===2&&s.parts.every(v=>Number.isFinite(v)&&v>0)).map(s=>({value:s.value,pixels:s.parts[0]*s.parts[1]})).filter(s=>s.pixels>=1000000&&s.pixels<=8000000).sort((a,b)=>b.pixels-a.pixels)[0]?.value;
}
