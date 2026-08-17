export type DashboardSummary={
  active_shipments:number;active_shipments_previous:number;active_shipments_delta_pct:number|null;
  revenue_month:number;revenue_previous_month:number;revenue_delta_pct:number|null;
  gross_profit_month:number;gross_profit_previous_month:number;gross_profit_delta_pct:number|null;
  carrier_cost_month:number;avg_margin_pct:number;delivered_on_time_pct:number|null;
  delivered_on_time_previous_pct:number|null;delivered_on_time_delta_points:number|null;
  delivered_qualifying_shipments:number;open_quotes:number;
};
export type PerformancePoint={period_start:string;label:string;revenue:number;gross_profit:number;carrier_cost:number;shipments:number};
export type PerformanceResponse={start_date:string;end_date:string;bucket:string;points:PerformancePoint[]};
export type RecentShipment={id:number;shipment_number:string;customer_name:string;customer_id:number;carrier_name?:string;carrier_scac?:string;origin:any;destination:any;customer_charge:number;status:string;pro_number?:string;created_at:string};
export type MarginException={shipment_id:number;shipment_number:string;customer_name:string;carrier_name?:string;expected_carrier_cost:number;final_carrier_cost:number;variance:number;expected_gp:number;final_gp:number;gp_impact:number};
export type SavingsOpportunity={quote_id:number;quote_number:string;customer_name:string;lowest_customer_price:number;highest_customer_price:number;savings_amount:number;savings_pct:number;created_at:string};
export type IntelligenceSummary={margin_exception_count:number;protected_gp:number;margin_exceptions:MarginException[];avg_opportunity_savings_pct:number;opportunity_count:number;savings_opportunities:SavingsOpportunity[]};
