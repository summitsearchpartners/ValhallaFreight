export type RateOption={
  carrier_id:number;carrier_name:string;scac:string;service:string;transit_days:number;
  base_charge:number|string;fuel:number|string;accessorials:number|string;carrier_cost:number|string;
  customer_price:number|string;gross_profit:number|string;margin_pct:number|string;
  selected?:boolean;selected_at?:string;
};
export type QuoteRecord={
  id:number;quote_number:string;customer_id:number;customer_name?:string|null;status:string;
  origin:Record<string,string>;destination:Record<string,string>;handling_units:any[];accessorials:string[];
  options:RateOption[];selected_option?:RateOption|null;created_at:string;expires_at?:string|null;requested_pickup_at?:string|null;requested_delivery_at?:string|null;shipment_id?:number|null;shipment_number?:string|null;
};
