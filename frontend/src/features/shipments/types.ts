export type ShipmentDetail={
 id:number;shipment_number:string;status:string;pro_number?:string;bol_number?:string;customer_id:number;customer_name?:string;carrier_id?:number;carrier_name?:string;carrier_scac?:string;
 origin:any;destination:any;handling_units:any[];accessorials:any[];carrier_cost:number;final_carrier_cost?:number|null;customer_charge:number;pickup_date?:string;estimated_delivery?:string;scheduled_pickup_at?:string|null;requested_delivery_at?:string|null;actual_pickup_at?:string|null;delivered_at?:string|null;created_at:string;
 tracking_events:{id:number;code:string;status:string;description?:string;location?:string;event_time:string;source:string}[];
};
