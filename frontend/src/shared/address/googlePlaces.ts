export type StructuredAddress = {
  name?:string;
  address1:string;
  address2?:string;
  city:string;
  state:string;
  postal_code:string;
  country:string;
  contact_name?:string;
  phone?:string;
  email?:string;
  instructions?:string;
  dock_hours?:string;
  location_id?:number;
  // ZIP returned by Google/saved location before the rated-lane ZIP is enforced in the UI.
  // Used at shipment approval to verify the selected facility truly belongs to the rated ZIP.
  verified_postal_code?:string;
  verified_city?:string;
  verified_state?:string;
};

let googleLoader:Promise<void>|null=null;

export function googlePlacesConfigured(){
  return Boolean((import.meta as any).env.VITE_GOOGLE_MAPS_API_KEY);
}

export function loadGoogleMaps(){
  const apiKey=(import.meta as any).env.VITE_GOOGLE_MAPS_API_KEY as string|undefined;
  if(!apiKey) return Promise.reject(new Error('Google Places API key is not configured'));
  if((window as any).google?.maps?.importLibrary) return Promise.resolve();
  if(googleLoader) return googleLoader;
  googleLoader=new Promise((resolve,reject)=>{
    const existing=document.querySelector<HTMLScriptElement>('script[data-vf-google-maps]');
    if(existing){
      if((window as any).google?.maps?.importLibrary){resolve();return;}
      existing.addEventListener('load',()=>resolve(),{once:true});
      existing.addEventListener('error',()=>reject(new Error('Google Maps failed to load')),{once:true});
      return;
    }
    const script=document.createElement('script');
    script.dataset.vfGoogleMaps='true';
    script.async=true;
    script.src=`https://maps.googleapis.com/maps/api/js?key=${encodeURIComponent(apiKey)}&loading=async&v=weekly&libraries=places`;
    script.onload=()=>resolve();
    script.onerror=()=>reject(new Error('Google Maps failed to load'));
    document.head.appendChild(script);
  });
  return googleLoader;
}

export function extractStructuredAddress(components:any[]):StructuredAddress{
  const get=(type:string,short=false)=>{
    const component=components.find((x:any)=>x.types?.includes(type));
    if(!component)return '';
    // Places API (New) uses longText/shortText while the legacy Places
    // details service returns long_name/short_name. Supporting both keeps
    // the shared address component resilient across Google API variants.
    return (short?(component.shortText||component.short_name):(component.longText||component.long_name))||'';
  };
  const streetNumber=get('street_number');
  const route=get('route');
  const address1=[streetNumber,route].filter(Boolean).join(' ').trim();
  const city=get('locality')||get('postal_town')||get('sublocality_level_1')||get('administrative_area_level_2');
  const state=get('administrative_area_level_1',true);
  let postal=get('postal_code');
  const suffix=get('postal_code_suffix');
  if(postal&&suffix) postal=`${postal}-${suffix}`;
  const countryCode=get('country',true)||'US';
  return {address1,city,state,postal_code:postal,country:countryCode==='US'?'USA':countryCode};
}
