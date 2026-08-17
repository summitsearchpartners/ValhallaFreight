import {useCallback,useEffect,useState} from 'react';
import {customerApi} from './api';
import type {Customer360} from './types';

export function useCustomer360(id:number){
  const [data,setData]=useState<Customer360|null>(null);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');
  const refresh=useCallback(async()=>{setLoading(true);setError('');try{setData(await customerApi.get(id))}catch(e:any){setError(e?.message||'Unable to load customer')}finally{setLoading(false)}},[id]);
  useEffect(()=>{refresh()},[refresh]);
  return {data,loading,error,refresh};
}
