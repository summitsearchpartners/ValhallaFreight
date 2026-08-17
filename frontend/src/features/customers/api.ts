import {api} from '../../services/api';
import type {Customer360,CustomerSummary,CustomerLocation,CustomerContact,CustomerActivity} from './types';

export const customerApi={
  list:()=>api<CustomerSummary[]>('/customers'),
  get:(id:number)=>api<Customer360>(`/customers/${id}/360`),
  create:(payload:any)=>api<CustomerSummary>('/customers',{method:'POST',body:JSON.stringify(payload)}),
  update:(id:number,payload:any)=>api<CustomerSummary>(`/customers/${id}`,{method:'PATCH',body:JSON.stringify(payload)}),
  addLocation:(id:number,payload:any)=>api<CustomerLocation>(`/customers/${id}/locations`,{method:'POST',body:JSON.stringify(payload)}),
  addContact:(id:number,payload:any)=>api<CustomerContact>(`/customers/${id}/contacts`,{method:'POST',body:JSON.stringify(payload)}),
  addActivity:(id:number,payload:any)=>api<CustomerActivity>(`/customers/${id}/activities`,{method:'POST',body:JSON.stringify(payload)}),
};
