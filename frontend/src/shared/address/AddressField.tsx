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
 * Valhalla Freight shared verified-address input.
 *
 * v0.7.8 intentionally uses Google's native Places Autocomplete widget instead
 * of maintaining our own prediction dropdown. Google's widget attaches the
 * suggestion container to document.body, which prevents quote-confirmation
 * sidebars/modals from clipping or suppressing suggestions.
 */
export default function AddressField({value,onValueChange,onAddressSelected,placeholder='Start typing an address…',required,autoFocus}:Props){
  const inputRef=useRef<HTMLInputElement>(null);
  const autocompleteRef=useRef<any>(null);
  const listenerRef=useRef<any>(null);
  const [ready,setReady]=useState(false);

  useEffect(()=>{
    let active=true;
    if(!googlePlacesConfigured()){
      console.warn('Valhalla Freight Address Service: Google Places API key is not configured. Autocomplete is disabled.');
      return;
    }

    loadGoogleMaps().then(async()=>{
      if(!active||!inputRef.current)return;
      const google=(window as any).google;

      // Ensure the Places library is available before constructing the widget.
      if(google?.maps?.importLibrary){
        try{ await google.maps.importLibrary('places'); }
        catch(err){ console.warn('Valhalla Freight Address Service: Places library import failed.',err); }
      }
      if(!active||!inputRef.current)return;

      const Autocomplete=google?.maps?.places?.Autocomplete;
      if(!Autocomplete){
        console.warn('Valhalla Freight Address Service: Google Places Autocomplete is unavailable. Verify Maps JavaScript API and Places API are enabled for this key.');
        return;
      }

      const autocomplete=new Autocomplete(inputRef.current,{
        componentRestrictions:{country:'us'},
        fields:['address_components','formatted_address','name'],
        types:['address']
      });
      autocompleteRef.current=autocomplete;

      listenerRef.current=autocomplete.addListener('place_changed',()=>{
        const place=autocomplete.getPlace();
        const components=place?.address_components||[];
        if(!components.length)return;

        const structured=extractStructuredAddress(components);
        if(!structured.address1&&place?.formatted_address){
          structured.address1=String(place.formatted_address).split(',')[0].trim();
        }

        // Commit the street value first, then the entire structured address.
        // The structured callback runs last so City/State/ZIP cannot be erased
        // by a stale parent state update.
        onValueChange(structured.address1||place?.formatted_address||inputRef.current?.value||'');
        onAddressSelected(structured);
      });

      setReady(true);
    }).catch(err=>{
      console.warn('Valhalla Freight Address Service: Google Maps failed to initialize.',err);
    });

    return()=>{
      active=false;
      try{ listenerRef.current?.remove?.(); }catch{/* no-op */}
      listenerRef.current=null;
      autocompleteRef.current=null;
    };
  },[onAddressSelected,onValueChange]);

  // Keep the DOM input synchronized with React state without fighting Google's
  // native autocomplete while the user is typing/selecting a suggestion.
  useEffect(()=>{
    if(inputRef.current&&inputRef.current.value!==value){
      inputRef.current.value=value||'';
    }
  },[value]);

  return <div className="vfAddressField">
    <div className="vfAddressInputWrap">
      <MapPin size={14}/>
      <input
        ref={inputRef}
        required={required}
        autoFocus={autoFocus}
        autoComplete="off"
        defaultValue={value}
        onChange={e=>onValueChange(e.target.value)}
        placeholder={placeholder}
        data-google-places-ready={ready?'true':'false'}
      />
    </div>
  </div>
}
