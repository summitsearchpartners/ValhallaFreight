import {useEffect,useRef,useState} from 'react';
import {Pause,Play} from 'lucide-react';

export default function LoginBackdrop(){
 const video=useRef<HTMLVideoElement>(null);
 const [allowed,setAllowed]=useState(false),[paused,setPaused]=useState(false),[playing,setPlaying]=useState(false),[failed,setFailed]=useState(false);
 useEffect(()=>{
  const desktop=window.matchMedia('(min-width: 981px)');
  const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');
  const connection=(navigator as Navigator&{connection?:{saveData?:boolean}}).connection;
  const update=()=>setAllowed(desktop.matches&&!reduced.matches&&!connection?.saveData);
  update();desktop.addEventListener('change',update);reduced.addEventListener('change',update);
  return()=>{desktop.removeEventListener('change',update);reduced.removeEventListener('change',update)};
 },[]);
 useEffect(()=>{
  const element=video.current;if(!element)return;
  const update=()=>{
   if(paused||document.hidden||!allowed)element.pause();
   else void element.play().catch(()=>setPlaying(false));
  };
  update();document.addEventListener('visibilitychange',update);
  return()=>{document.removeEventListener('visibilitychange',update);element.pause()};
 },[allowed,paused,failed]);
 return <>
  <div className="loginFilm" aria-hidden="true">
   <div className="loginFilmPoster"/>
   {allowed&&!failed&&<video ref={video} className="loginFilmVideo" autoPlay muted loop playsInline preload="metadata" tabIndex={-1}
     poster="/media/freight-road-film-poster.jpg" disablePictureInPicture
     onPlaying={()=>setPlaying(true)} onPause={()=>setPlaying(false)} onError={()=>{setFailed(true);setPlaying(false)}}>
     <source src="/media/freight-road-film.webm" type="video/webm"/>
     <source src="/media/freight-road-film.mp4" type="video/mp4"/>
    </video>}
   <div className="loginFilmShade"/><div className="loginFilmGrain"/>
  </div>
  {allowed&&!failed&&<button type="button" className="loginFilmControl" aria-label={playing?'Pause background video':'Play background video'}
   onClick={()=>{if(playing){setPaused(true);video.current?.pause()}else{setPaused(false);void video.current?.play().catch(()=>setPlaying(false))}}}>
    {playing?<Pause size={13}/>:<Play size={13}/>}<span>{playing?'Pause film':'Play film'}</span>
   </button>}
 </>;
}
