import {api} from '../../services/api';
import type {ShipmentDetail} from './types';
export const shipmentApi={detail:(id:number)=>api<ShipmentDetail>(`/shipments/${id}`)};
