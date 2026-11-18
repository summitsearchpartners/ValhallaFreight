import {api} from '../../services/api';
import type {DashboardSummary,PerformanceResponse,RecentShipment,IntelligenceSummary} from './types';
export const dashboardApi={
  summary:()=>api<DashboardSummary>('/dashboard/summary'),
  performance:(start:string,end:string)=>api<PerformanceResponse>(`/dashboard/performance?start_date=${start}&end_date=${end}`),
  recent:(limit=8)=>api<RecentShipment[]>(`/dashboard/recent-shipments?limit=${limit}`),
  intelligence:()=>api<IntelligenceSummary>('/dashboard/intelligence'),
  importFreight:async(file:File)=>{
    const fd=new FormData();fd.append('file',file);
    const payload=await api<any>('/shipments/import',{method:'POST',body:fd});
    return payload as {imported:number;skipped:number;errors:string[]};
  }
};
