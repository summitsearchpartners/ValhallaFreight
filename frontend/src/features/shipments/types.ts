export type ShipmentDetail={
 customer_invoice?:{invoice_number:string;amount:number;status:string;due_date?:string|null}|null;transport_mode?:string;invoice_issued?:boolean;quote_id?:number|null;
 id:number;shipment_number:string;status:string;pro_number?:string;bol_number?:string;customer_id:number;customer_name?:string;carrier_id?:number;carrier_name?:string;carrier_scac?:string;
 po_number?:string|null;customer_reference?:string|null;package_count?:number|null;package_type?:string|null;commodity_description?:string|null;nmfc_number?:string|null;hazmat_emergency_contact?:string|null;hazmat_emergency_phone?:string|null;declared_value?:number|null;payment_terms?:string;
 origin:any;destination:any;handling_units:any[];accessorials:any[];carrier_cost:number;final_carrier_cost?:number|null;customer_charge:number;pickup_date?:string;estimated_delivery?:string;scheduled_pickup_at?:string|null;requested_delivery_at?:string|null;actual_pickup_at?:string|null;delivered_at?:string|null;created_at:string;
 tracking_events:{id:number;code:string;status:string;description?:string;location?:string;event_time:string;source:string}[];
 documents?:{id:number;document_type:string;name:string;content_type?:string;size_bytes:number;uploaded_by_role:string;uploaded_by:string;created_at:string;url:string}[];
 carrier_submissions?:{id:number;provider?:string|null;is_test?:boolean;status:string;provider_reference?:string|null;pro_number?:string|null;error?:string|null;created_at:string}[];
};
