export type RateOption={
  carrier_id:number;carrier_name:string;scac:string;service:string;transit_days:number;
  base_charge:number|string;fuel:number|string;accessorials:number|string;carrier_cost:number|string;
  customer_price:number|string;gross_profit:number|string;margin_pct:number|string;
  muse_revision?:string;provider?:string|null;selected?:boolean;selected_at?:string;source?:string;provider_quote_id?:string|null;movement_type?:string|null;warnings?:string[];
};
export type QuoteRecord={
  id:number;quote_number:string;customer_id:number;customer_name?:string|null;status:string;
  origin:Record<string,string>;destination:Record<string,string>;handling_units:any[];accessorials:string[];
  options:RateOption[];muse_preview?:MusePreview|null;selected_option?:RateOption|null;created_at:string;expires_at?:string|null;requested_pickup_at?:string|null;requested_delivery_at?:string|null;shipment_id?:number|null;shipment_number?:string|null;payment_terms?:string;
};

export type MuseRateInput={carrier_name:string;customer_price:string;carrier_id?:number|null;carrier_cost?:string|null;transit_days?:number|null};
export type MuseRate=MuseRateInput&{revision:string};
export type MusePreview={provider:'muse_freight';status:'preview';service:string;services:string[];rate:MuseRate|null};
export type MuseAccountStatus={account_verified:boolean;credit_application_url:string};
export type MusePreviewSelection=MuseAccountStatus&{first_selection:boolean;show_onboarding:boolean;selected:boolean;manufacturer_id:number;application_status:string;rate:MuseRate};
export type RateResponse={quote_number:string;options:RateOption[];muse_preview?:MusePreview|null};
