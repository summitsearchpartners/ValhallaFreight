import {useEffect} from 'react';
import {getAccessToken} from '../../services/api';
import {manufacturerSupport} from '../../services/manufacturerSupport';
export default function useSafeLoadEvents(userId?:number){
 useEffect(()=>{if(!userId)return;const controller=new AbortController();let timer:ReturnType<typeof setTimeout>;
 async function connect(){try{const support=manufacturerSupport();const headers:Record<string,string>={Authorization:'Bearer '+getAccessToken()};if(support){headers['X-Company-Id']=String(support.customer_id);headers['X-Portal-Session']=support.portal_token;headers['X-Portal-Workspace']='manufacturer'}
 const response=await fetch((import.meta.env.VITE_API_URL||'http://localhost:8000/api/v1')+'/safe-load/events',{headers,signal:controller.signal});if(!response.ok||!response.body)return;
 const reader=response.body.getReader();const decoder=new TextDecoder();let text='';while(true){const chunk=await reader.read();if(chunk.done)break;text+=decoder.decode(chunk.value,{stream:true});let index;while((index=text.indexOf('\n\n'))>=0){const event=text.slice(0,index);text=text.slice(index+2);if(event.startsWith('data:')){window.dispatchEvent(new Event('safe-load-updated'));window.dispatchEvent(new Event('operational-notification-updated'))}}}
 }catch{}finally{if(!controller.signal.aborted)timer=setTimeout(connect,1500)}}void connect();return()=>{controller.abort();clearTimeout(timer)};
 },[userId]);
}
