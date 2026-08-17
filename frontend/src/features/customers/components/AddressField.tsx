import {useEffect,useRef,useState} from 'react';
import {MapPin} from 'lucide-react';
import {extractStructuredAddress,googlePlacesConfigured,loadGoogleMaps,type StructuredAddress} from '../address/googlePlaces';

type Props={
  value:string;
  onValueChange:(value:string)=>void;
  onAddressSelected:(address:StructuredAddress)=>void;
  placeholder?:string;
  required?:boolean;
  autoFocus?:boolean;
};

export default function AddressField({value,onValueChange,onAddressSelected,placeholder='Start typing an address…',required,autoFocus}:Props){
  const [suggestions,setSuggestions]=useState<any[]>([]);
  const [open,setOpen]=useState(false);
  const [ready,setReady]=useState(false);
  const [placesLib,setPlacesLib]=useState<any>(null);
  const sessionToken=useRef<any>(null);
  const requestId=useRef(0);
  const timer=useRef<number|undefined>(undefined);
  const wrapper=useRef<HTMLDivElement>(null);

  useEffect(()=>{
    let active=true;
    if(!googlePlacesConfigured()) return;
    loadGoogleMaps().then(async()=>{
      const google=(window as any).google;
      const lib=await google.maps.importLibrary('places');
      if(!active)return;
      setPlacesLib(lib);
      sessionToken.current=new lib.AutocompleteSessionToken();
      setReady(true);
    }).catch(()=>setReady(false));
    return()=>{active=false};
  },[]);

  useEffect(()=>{
    const close=(event:MouseEvent)=>{
      if(wrapper.current&&!wrapper.current.contains(event.target as Node))setOpen(false);
    };
    document.addEventListener('mousedown',close);
    return()=>document.removeEventListener('mousedown',close);
  },[]);

  async function fetchSuggestions(input:string){
    if(!ready||!placesLib||input.trim().length<3){setSuggestions([]);setOpen(false);return;}
    const id=++requestId.current;
    try{
      if(!sessionToken.current)sessionToken.current=new placesLib.AutocompleteSessionToken();
      const {suggestions:items}=await placesLib.AutocompleteSuggestion.fetchAutocompleteSuggestions({
        input,
        sessionToken:sessionToken.current,
        includedPrimaryTypes:['street_address'],
        includedRegionCodes:['us'],
        language:'en-US',
        region:'us'
      });
      if(id!==requestId.current)return;
      const next=(items||[]).filter((x:any)=>x.placePrediction).slice(0,6);
      setSuggestions(next);
      setOpen(next.length>0);
    }catch{
      if(id===requestId.current){setSuggestions([]);setOpen(false);}
    }
  }

  function changed(next:string){
    onValueChange(next);
    window.clearTimeout(timer.current);
    timer.current=window.setTimeout(()=>fetchSuggestions(next),220);
  }

  async function select(item:any){
    const prediction=item.placePrediction;
    if(!prediction)return;
    const place=prediction.toPlace();
    await place.fetchFields({fields:['addressComponents','formattedAddress']});
    if(place.addressComponents){
      const structured=extractStructuredAddress(place.addressComponents);
      onAddressSelected(structured);
      onValueChange(structured.address1||place.formattedAddress||value);
    }
    setSuggestions([]);setOpen(false);
    sessionToken.current=placesLib?new placesLib.AutocompleteSessionToken():null;
  }

  return <div className="vfAddressField" ref={wrapper}>
    <div className="vfAddressInputWrap">
      <MapPin size={14}/>
      <input
        required={required}
        autoFocus={autoFocus}
        autoComplete="off"
        value={value}
        onChange={e=>changed(e.target.value)}
        onFocus={()=>suggestions.length&&setOpen(true)}
        placeholder={placeholder}
      />
    </div>
    {open&&<div className="vfAddressSuggestions" role="listbox">
      {suggestions.map((item:any,index:number)=>{
        const prediction=item.placePrediction;
        const text=prediction?.text?.toString?.()||'';
        return <button type="button" key={`${text}-${index}`} onMouseDown={e=>e.preventDefault()} onClick={()=>select(item)}>
          <MapPin size={14}/><span>{text}</span>
        </button>
      })}
      <div className="vfAddressGoogle">Powered by Google</div>
    </div>}
  </div>
}
