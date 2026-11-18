export type ManufacturerSupport={customer_id:number;company_name:string;portal_type:'manufacturer';portal_token:string;expires_at:string};
const key='vf_manufacturer_support';
export function manufacturerSupport():ManufacturerSupport|null{try{return JSON.parse(sessionStorage.getItem(key)||'null')}catch{return null}}
export function saveManufacturerSupport(value:ManufacturerSupport){sessionStorage.setItem(key,JSON.stringify(value))}
export function clearManufacturerSupport(){sessionStorage.removeItem(key)}
