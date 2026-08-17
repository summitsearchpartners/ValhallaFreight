export type CustomerSummary = {
  id:number; code:string; name:string; status:string; industry?:string|null; billing_email?:string|null;
  default_markup_pct:number|string; credit_limit:number|string; location_count:number; contact_count:number;
  shipment_count:number; active_shipment_count:number; revenue_total:number|string;
};
export type CustomerProfile = {
  id:number; customer_id:number; legal_name?:string|null; website?:string|null; phone?:string|null;
  account_manager?:string|null; sales_owner?:string|null; payment_terms:string; tax_exempt:boolean; credit_hold:boolean;
  onboarding_status:string; preferred_contact_method:string; billing_address?:Record<string,string>|null;
  operating_preferences?:Record<string,unknown>; created_at:string; updated_at:string;
};
export type CustomerLocation = {
  id:number; customer_id:number; name:string; location_type:string; address1:string; address2?:string|null; city:string; state:string;
  postal_code:string; country:string; contact_name?:string|null; phone?:string|null; email?:string|null; dock_hours?:string|null;
  appointment_required:boolean; liftgate_default:boolean; residential:boolean; limited_access:boolean; instructions?:string|null; active:boolean; created_at:string;
};
export type CustomerContact = {
  id:number; customer_id:number; first_name:string; last_name:string; title?:string|null; email?:string|null; phone?:string|null; mobile?:string|null;
  role:string; primary:boolean; billing_contact:boolean; quote_contact:boolean; active:boolean; created_at:string;
};
export type CustomerActivity = {id:number; customer_id:number; activity_type:string; subject:string; body?:string|null; created_by?:string|null; created_at:string};
export type ShipmentMini = {id:number; shipment_number:string; status:string; origin:Record<string,string>; destination:Record<string,string>; carrier_id?:number|null; customer_charge:number|string; pickup_date?:string|null};
export type Customer360 = {customer:CustomerSummary; profile?:CustomerProfile|null; locations:CustomerLocation[]; contacts:CustomerContact[]; activities:CustomerActivity[]; shipments:ShipmentMini[]};
