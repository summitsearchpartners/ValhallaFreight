export type CarrierSummary={
  id:number;scac:string;name:string;mode:string;modes:string[];active:boolean;api_enabled:boolean;preferred:boolean;preferred_rank?:number|null;
  authority_status:string;onboarding_status:string;safety_rating:string;compliance_ok:boolean;shipments:number;delivered_shipments:number;
  on_time_delivery_pct:number;on_time_pickup_pct:number;avg_transit_days:number;carrier_spend:number;customer_revenue:number;gross_profit:number;margin_pct:number;avg_cost:number;claims:number;claim_amount:number;claims_pct:number;
};
export type CarrierProfile={mc_number?:string|null;dot_number?:string|null;authority_status:string;payment_terms:string;factoring_company?:string|null;cargo_limit:number;auto_liability_limit:number;insurance_expires_at?:string|null;preferred:boolean;legal_name?:string|null;website?:string|null;main_phone?:string|null;dispatch_email?:string|null;billing_email?:string|null;address1?:string|null;city?:string|null;state?:string|null;postal_code?:string|null;country?:string|null;onboarding_status:string;safety_rating:string;preferred_rank?:number|null;notes?:string|null};
export type CarrierDetail={
  carrier:{id:number;scac:string;name:string;mode:string;active:boolean;api_enabled:boolean};profile:CarrierProfile;
  contacts:any[];terminals:any[];compliance:any[];capabilities:any[];service_areas:any[];lanes:any[];contracts:any[];documents:any[];activities:any[];pricing_rules:any[];
  performance:{shipments:number;delivered_shipments:number;on_time_delivery_pct:number;on_time_pickup_pct:number;avg_transit_days:number;carrier_spend:number;customer_revenue:number;gross_profit:number;margin_pct:number;avg_cost:number;claims:number;claim_amount:number;claims_pct:number};
  lane_rollup:any[];recent_shipments:any[];
};
