import {api} from '../../services/api';
import type {ShipmentDetail} from './types';
export const shipmentApi={detail:(id:number)=>api<ShipmentDetail>(`/shipments/${id}`),update:(id:number,payload:any)=>api<ShipmentDetail>(`/shipments/${id}`,{method:'PATCH',body:JSON.stringify(payload)})};
