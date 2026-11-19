import {useEffect,useRef,useState} from 'react';
import {MapPin} from 'lucide-react';
import {extractStructuredAddress,googlePlacesConfigured,loadGoogleMaps,type StructuredAddress} from './googlePlaces';

type Props={
  value:string;
  onValueChange:(value:string)=>void;
  onAddressSelected:(address:StructuredAddress)=>void;
  placeholder?:string;
  required?:boolean;
  autoFocus?:boolean;
};

/**
 * Valhalla TMS shared verified-address input.
 *
 * Uses Google Places AutocompleteSuggestion (Places API New) and renders the
 * suggestion list inside Valhalla TMS. This avoids native PAC dropdown
 * stacking/portal issues inside Quote Bucket shipment confirmation while still
 * returning Google's verified structured address data.
 */
export default function AddressField({value,onValueChange,onAddressSelected,placeholder='Start typing an address…',required,autoFocus}:Props){
  const [suggestions,setSuggestions]=useState<any[]>([]);
  const [open,setOpen]=useState(false);
  const [ready,setReady]=useState(false);
  const [placesLib,setPlacesLib]=useState<any>(null);
  const [loadError,setLoadError]=useState(false);
  const wrapper=useRef<HTMLDivElement>(null);
  const sessionToken=useRef<any>(null);
  const requestId=useRef(0);
  const timer=useRef<number|undefined>(undefined);

  useEffect(()=>{
    let active=true;
    if(!googlePlacesConfigured()){
      setLoadError(true);
      console.warn('Valhalla TMS Address Service: Google Places API key is not configured.');
      return;
    }
    loadGoogleMaps().then(async()=>{
      const google=(window as any).google;
      const lib=await google.maps.importLibrary('places');
      if(!active)return;
      setPlacesLib(lib);
      if(lib?.AutocompleteSessionToken) sessionToken.current=new lib.AutocompleteSessionToken();
      setReady(Boolean(lib?.AutocompleteSuggestion));
      setLoadError(!lib?.AutocompleteSuggestion);
      if(!lib?.AutocompleteSuggestion){
        console.warn('Valhalla TMS Address Service: AutocompleteSuggestion is unavailable. Verify Places API (New) is enabled for this key.');
      }
    }).catch(err=>{
      if(active){setReady(false);setLoadError(true)}
      console.warn('Valhalla TMS Address Service: Google Places failed to initialize.',err);
    });
    return()=>{active=false;window.clearTimeout(timer.current)};
  },[]);

  useEffect(()=>{
    const close=(event:MouseEvent)=>{
      if(wrapper.current&&!wrapper.current.contains(event.target as Node))setOpen(false);
    };
    document.addEventListener('mousedown',close);
    return()=>document.removeEventListener('mousedown',close);
  },[]);

  async function fetchSuggestions(input:string){
    const trimmed=input.trim();
    if(!ready||!placesLib||trimmed.length<3){setSuggestions([]);setOpen(false);return;}
    const id=++requestId.current;
    try{
      if(!sessionToken.current&&placesLib.AutocompleteSessionToken){
        sessionToken.current=new placesLib.AutocompleteSessionToken();
      }
      const response=await placesLib.AutocompleteSuggestion.fetchAutocompleteSuggestions({
        input:trimmed,
        sessionToken:sessionToken.current,
        includedPrimaryTypes:['street_address'],
        includedRegionCodes:['us'],
        language:'en-US',
        region:'us'
      });
      if(id!==requestId.current)return;
      const next=(response?.suggestions||[]).filter((x:any)=>x?.placePrediction).slice(0,7);
      setSuggestions(next);
      setOpen(next.length>0);
    }catch(err){
      if(id===requestId.current){setSuggestions([]);setOpen(false)}
      console.warn('Valhalla TMS Address Service: address prediction request failed.',err);
    }
  }

  function changed(next:string){
    onValueChange(next);
    window.clearTimeout(timer.current);
    timer.current=window.setTimeout(()=>fetchSuggestions(next),180);
  }

  async function select(item:any){
    const prediction=item?.placePrediction;
    if(!prediction)return;
    try{
      const place=prediction.toPlace();
      await place.fetchFields({fields:['addressComponents','formattedAddress','displayName']});
      const components=place.addressComponents||[];
      if(!components.length)throw new Error('Google returned no structured address components');
      const structured=extractStructuredAddress(components);
      const formatted=String(place.formattedAddress||'').trim();
      if(!structured.address1&&formatted)structured.address1=formatted.split(',')[0].trim();
      onAddressSelected(structured);
      setSuggestions([]);
      setOpen(false);
      if(placesLib?.AutocompleteSessionToken)sessionToken.current=new placesLib.AutocompleteSessionToken();
    }catch(err){
      console.warn('Valhalla TMS Address Service: selected address details could not be loaded.',err);
    }
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
        data-google-places-ready={ready?'true':'false'}
        aria-autocomplete="list"
        aria-expanded={open}
      />
    </div>
    {open&&<div className="vfAddressSuggestions" role="listbox">
      {suggestions.map((item:any,index:number)=>{
        const prediction=item.placePrediction;
        const text=prediction?.text?.toString?.()||prediction?.mainText?.toString?.()||'';
        return <button type="button" key={`${text}-${index}`} onMouseDown={e=>e.preventDefault()} onClick={()=>select(item)}>
          <MapPin size={14}/><span>{text}</span>
        </button>;
      })}
      <div className="vfAddressGoogle">Powered by Google</div>
    </div>}
    {loadError&&<div className="vfAddressStatusError">Address search is unavailable. Enter the full address manually; in booking, choose Enter manually and confirm the facility.</div>}
  </div>;
}
