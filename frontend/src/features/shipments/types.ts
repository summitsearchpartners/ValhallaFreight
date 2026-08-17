export type ShipmentDetail={
 id:number;shipment_number:string;status:string;pro_number?:string;bol_number?:string;customer_id:number;customer_name?:string;carrier_id?:number;carrier_name?:string;carrier_scac?:string;
 origin:any;destination:any;handling_units:any[];accessorials:any[];carrier_cost:number;final_carrier_cost?:number|null;customer_charge:number;pickup_date?:string;estimated_delivery?:string;delivered_at?:string;created_at:string;
 tracking_events:{id:number;code:string;status:string;description?:string;location?:string;event_time:string;source:string}[];
};
