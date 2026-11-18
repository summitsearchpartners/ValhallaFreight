import {useEffect,useRef,useState} from 'react';
import {rotatePhoto} from './rotatePhoto';
export default function ReadablePhoto({src,alt,style,onError}:any){
 const [display,setDisplay]=useState(src),[working,setWorking]=useState(false),[error,setError]=useState('');
 const epoch=useRef(0),urls=useRef<string[]>([]);
 useEffect(()=>{epoch.current++;setDisplay(src);setError('');setWorking(false);return()=>{epoch.current++;urls.current.forEach(url=>URL.revokeObjectURL(url));urls.current=[]}},[src]);
 async function rotate(degrees:number){const round=epoch.current;setWorking(true);setError('');try{const response=await fetch(display);if(!response.ok)throw Error('Photo could not be loaded for rotation.');const blob=await response.blob();const result=await rotatePhoto(new File([blob],'preview.jpg',{type:blob.type}),degrees);if(epoch.current!==round)return;const url=URL.createObjectURL(result);urls.current.push(url);setDisplay(url)}catch(e:any){if(epoch.current===round)setError(e.message)}finally{if(epoch.current===round)setWorking(false)}}
 return <div className="slReadablePhoto"><a href={display} target="_blank" rel="noreferrer" title="Open full-size photo"><img src={display} alt={alt} style={style} onError={onError}/></a><div className="slPhotoTools"><button type="button" className="btn secondary" disabled={working} onClick={()=>rotate(-90)} aria-label={'Rotate '+alt+' left'}>↶ Rotate left</button><button type="button" className="btn secondary" disabled={working} onClick={()=>rotate(90)} aria-label={'Rotate '+alt+' right'}>Rotate right ↷</button><small>View only · saved evidence is unchanged.</small></div>{error&&<p className="slError" role="alert">{error}</p>}</div>
}
