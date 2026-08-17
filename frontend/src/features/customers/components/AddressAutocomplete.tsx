import {useEffect,useRef,useState} from 'react';
import {MapPin,Search,ShieldCheck} from 'lucide-react';

type AddressValue={address1:string;address2?:string;city:string;state:string;postal_code:string;country:string};
type Props={value:AddressValue;onChange:(patch:Partial<AddressValue>)=>void};

let googleLoader:Promise<void>|null=null;
function loadGoogleMaps(apiKey:string){
  if((window as any).google?.maps?.importLibrary) return Promise.resolve();
  if(googleLoader) return googleLoader;
  googleLoader=new Promise((resolve,reject)=>{
    const existing=document.querySelector<HTMLScriptElement>('script[data-vf-google-maps]');
    if(existing){existing.addEventListener('load',()=>resolve(),{once:true});existing.addEventListener('error',()=>reject(new Error('Google Maps failed to load')),{once:true});return;}
    const script=document.createElement('script');
    script.dataset.vfGoogleMaps='true';
    script.async=true;
    script.src=`https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&loading=async&libraries=places&v=weekly`;
    script.onload=()=>resolve(); script.onerror=()=>reject(new Error('Google Maps failed to load'));
    document.head.appendChild(script);
  });
  return googleLoader;
}

function extractAddress(components:any[]){
  const get=(type:string,short=false)=>{const c=components.find(x=>x.types?.includes(type));return c?(short?c.shortText:c.longText)||'':''};
  const streetNumber=get('street_number');
  const route=get('route');
  const address1=[streetNumber,route].filter(Boolean).join(' ');
  const city=get('locality')||get('postal_town')||get('sublocality_level_1');
  const state=get('administrative_area_level_1',true);
  let postal=get('postal_code'); const suffix=get('postal_code_suffix'); if(postal&&suffix) postal=`${postal}-${suffix}`;
  const country=get('country',true)||'US';
  return {address1,city,state,postal_code:postal,country:country==='US'?'USA':country};
}

export default function AddressAutocomplete({value,onChange}:Props){
  const host=useRef<HTMLDivElement>(null); const [status,setStatus]=useState<'loading'|'ready'|'manual'|'error'>('loading');
  const apiKey=(import.meta as any).env.VITE_GOOGLE_MAPS_API_KEY as string|undefined;
  useEffect(()=>{
    let disposed=false; let element:any;
    if(!apiKey){setStatus('manual');return;}
    loadGoogleMaps(apiKey).then(async()=>{
      if(disposed||!host.current)return;
      const google=(window as any).google;
      const places=await google.maps.importLibrary('places');
      element=new places.PlaceAutocompleteElement();
      element.setAttribute('included-primary-types','street_address');
      element.setAttribute('included-region-codes','us');
      element.className='vfPlaceAutocomplete';
      element.setAttribute('placeholder','Start typing a street address…');
      element.addEventListener('gmp-select',async(event:any)=>{
        const place=event.placePrediction.toPlace();
        await place.fetchFields({fields:['addressComponents','formattedAddress']});
        if(place.addressComponents){onChange(extractAddress(place.addressComponents));}
      });
      host.current.replaceChildren(element); setStatus('ready');
    }).catch(()=>setStatus('error'));
    return()=>{disposed=true;if(element?.remove)element.remove();};
  },[apiKey]);
  return <div className="addressAssistant">
    <div className="addressAssistantHead"><div><MapPin size={17}/><div><b>Smart address lookup</b><span>Select the verified address and Valhalla Freight fills City, State and ZIP.</span></div></div>{status==='ready'&&<em><ShieldCheck size={12}/>Google Places</em>}</div>
    {status==='loading'&&apiKey&&<div className="addressLoading"><Search size={14}/>Loading address search…</div>}
    <div ref={host}/>
    {(status==='manual'||status==='error')&&<div className="addressManualNotice"><b>{status==='error'?'Address lookup could not load.':'Address autocomplete is ready to configure.'}</b><span>{status==='manual'?'Add VITE_GOOGLE_MAPS_API_KEY to your .env file to enable Google-style address suggestions. Manual address entry remains available below.':'You can still enter the address manually below.'}</span></div>}
    {status==='ready'&&value.address1&&<div className="addressSelected"><ShieldCheck size={14}/><div><b>{value.address1}</b><span>{value.city}, {value.state} {value.postal_code}</span></div></div>}
  </div>
}
