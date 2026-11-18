import {Package,Plus,Trash2} from 'lucide-react';

export type FreightUnitDraft={quantity:string;weight:string;length:string;width:string;height:string;freightClass:string};
export const newFreightUnit=():FreightUnitDraft=>({quantity:'1',weight:'',length:'',width:'',height:'',freightClass:''});

export function densityClass(weight:number,length:number,width:number,height:number){
 const cubicFeet=(length*width*height)/1728;
 if(!weight||!cubicFeet)return {density:0,freightClass:''};
 const d=weight/cubicFeet;
 const freightClass=d>=50?'50':d>=35?'55':d>=30?'60':d>=22.5?'65':d>=15?'70':d>=12?'85':d>=10?'92.5':d>=8?'100':d>=6?'125':d>=4?'175':d>=2?'250':d>=1?'300':'400';
 return {density:d,freightClass};
}

export default function FreightDetailsFields({units,onChange}:{units:FreightUnitDraft[];onChange:(units:FreightUnitDraft[])=>void}){
 function set(i:number,key:keyof FreightUnitDraft,value:string){
  const next=units.map((u,n)=>n===i?{...u,[key]:value}:u);
  if(['weight','length','width','height'].includes(key)){
   const u=next[i],calc=densityClass(Number(u.weight),Number(u.length),Number(u.width),Number(u.height));
   next[i]={...u,freightClass:calc.freightClass};
  }
  onChange(next);
 }
 return <><div className="sectiontitle top"><Package/><div><h3>Freight details</h3><p>Add each unique skid / handling-unit size separately. Class is estimated from the current NMFC 13-tier density scale and remains editable.</p></div></div><div className="freightUnitList">{units.map((u,i)=><div className="freightUnitRow" key={i}><div className="freightUnitNumber">{i+1}</div><label>Qty<input type="number" min="1" value={u.quantity} onChange={e=>set(i,'quantity',e.target.value)} required/></label><label>Weight / unit (lb)<input type="number" min="1" value={u.weight} onChange={e=>set(i,'weight',e.target.value)} required/></label><label>Length (in)<input type="number" min="1" value={u.length} onChange={e=>set(i,'length',e.target.value)} required/></label><label>Width (in)<input type="number" min="1" value={u.width} onChange={e=>set(i,'width',e.target.value)} required/></label><label>Height (in)<input type="number" min="1" value={u.height} onChange={e=>set(i,'height',e.target.value)} required/></label><label>Class<input type="text" inputMode="decimal" value={u.freightClass} onChange={e=>set(i,'freightClass',e.target.value)} placeholder="Auto" required/></label>{units.length>1&&<button className="freightRemove" type="button" title="Remove freight line" onClick={()=>onChange(units.filter((_,n)=>n!==i))}><Trash2/></button>}</div>)}</div><button type="button" className="addFreightUnit" onClick={()=>onChange([...units,newFreightUnit()])}><Plus/>Add another freight classification / skid</button></>
}
