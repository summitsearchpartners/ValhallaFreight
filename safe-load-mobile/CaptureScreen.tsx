import React,{useEffect,useRef,useState} from 'react';
import {View,Text,Pressable,StyleSheet,Image,ActivityIndicator,BackHandler} from 'react-native';
import {SafeAreaView} from 'react-native-safe-area-context';
import {CameraView} from 'expo-camera';
import {manipulateAsync,SaveFormat} from 'expo-image-manipulator';
import {File} from 'expo-file-system';
import {choosePictureSize} from './capturePolicy';
import {PhotoReviewFlow} from './photoReviewFlow';
import {guideCrop,type Rect} from './cropGeometry';
import type {CameraContext} from './cameraApi';
export type CaptureKind='idPhoto'|'idBackPhoto'|'vinPhoto';
type Props={kind:CaptureKind;context:CameraContext;onPhoto:(uri:string)=>Promise<void>;onScan:(result:any)=>void;onCancel:()=>void};
export default function CaptureScreen({kind,onPhoto,onCancel}:Props){
 const camera=useRef<CameraView>(null),alive=useRef(true),lock=useRef(false);
 const flow=useRef<PhotoReviewFlow|null>(null);if(!flow.current)flow.current=new PhotoReviewFlow(uri=>{try{new File(uri).delete()}catch{}});
 const [candidate,setCandidate]=useState(''),[ready,setReady]=useState(false),[working,setWorking]=useState(false),[hint,setHint]=useState('Starting camera…'),[torch,setTorch]=useState(false),[zoom,setZoom]=useState(0),[round,setRound]=useState(0),[pictureSize,setPictureSize]=useState<string>(),[preview,setPreview]=useState({width:360,height:400}),[guide,setGuide]=useState<Rect|null>(null);
 const id=kind!=='vinPhoto';
 function remove(uri:string){try{new File(uri).delete()}catch{}}
 function cancel(){alive.current=false;flow.current?.cancel();onCancel()}
 useEffect(()=>{alive.current=true;const back=BackHandler.addEventListener('hardwareBackPress',()=>{cancel();return true});return()=>{alive.current=false;flow.current?.cancel();back.remove()}},[]);
 async function cameraReady(){try{if(!pictureSize){const size=choosePictureSize(await camera.current!.getAvailablePictureSizesAsync());if(alive.current&&size)setPictureSize(size)}}catch{}finally{if(alive.current){setReady(true);setHint('Position the '+(kind==='idBackPhoto'?'ID back':id?'ID front':'truck VIN')+' inside the outline, then tap Take Photo.')}}}
 async function take(){
  if(!ready||lock.current||!alive.current||!guide)return;
  const generation=flow.current!.begin();if(generation===null)return;lock.current=true;setWorking(true);let raw='',cropped='';
  try{
   const picture=await camera.current?.takePictureAsync({quality:.95,shutterSound:false});if(!picture?.uri)throw Error('No camera image captured. Try again.');raw=picture.uri;
   if(!alive.current){remove(raw);return}
   {const crop=guideCrop(picture,preview,guide);const result=await manipulateAsync(raw,[{crop}],{compress:.95,format:SaveFormat.JPEG});cropped=result.uri;if(raw!==cropped)remove(raw);raw=''}
   if(flow.current!.present(cropped,generation)){setCandidate(cropped);setHint('Review the framed photo. Accept keeps this exact image. Retake discards it.')}cropped='';
  }catch(e:any){if(raw)remove(raw);if(cropped)remove(cropped);flow.current!.failed(generation);if(alive.current)setHint(e.message)}finally{lock.current=false;if(alive.current)setWorking(false)}
 }
 async function rotatePhoto(degrees:number){
  if(lock.current||!candidate)return;lock.current=true;setWorking(true);const previous=candidate;
  try{const result=await manipulateAsync(previous,[{rotate:degrees}],{compress:.95,format:SaveFormat.JPEG});if(flow.current!.replace(result.uri,previous)&&alive.current){setCandidate(result.uri);setHint('Check the text is upright, then Accept Photo.')}}catch(e:any){if(alive.current)setHint(e.message)}finally{lock.current=false;if(alive.current)setWorking(false)}
 }
 async function accept(){if(lock.current)return;lock.current=true;setWorking(true);try{await flow.current!.accept(onPhoto)}catch(e:any){if(alive.current)setHint(e.message)}finally{lock.current=false;if(alive.current)setWorking(false)}}
 function retake(){if(flow.current!.retake()){setCandidate('');setGuide(null);setReady(false);setRound(n=>n+1);setHint('Reposition the document, then take a new photo.')}}
 const button=(label:string,action:()=>void,disabled=false)=><Pressable accessibilityRole="button" disabled={disabled} accessibilityLabel={label} onPress={action} style={[s.button,disabled&&{opacity:.45}]}><Text style={s.buttonText}>{label}</Text></Pressable>;
 return <SafeAreaView style={s.screen}><View style={s.header}><View style={s.row}><Text style={s.title}>{candidate?'Review Photo':kind==='idBackPhoto'?'ID Back Photo':id?'ID Front Photo':'Truck VIN Photo'}</Text><Pressable accessibilityRole="button" accessibilityLabel="Cancel capture" onPress={cancel} style={{padding:12}}><Text style={{color:'#ffad70',fontWeight:'800'}}>Cancel</Text></Pressable></View><Text style={s.copy}>{candidate?'Check that all details are legible before accepting.':id?'Keep all four card edges inside the outline. '+(kind==='idBackPhoto'?'Include the entire barcode.':'Avoid glare and hold steady.'):'Fit the entire 17-character VIN inside the outline. Only this area will be saved. Avoid reflections.'}</Text></View>
 <View style={s.preview} onLayout={e=>setPreview(e.nativeEvent.layout)}>{candidate?<Image accessibilityLabel="Cropped photo for review" source={{uri:candidate}} resizeMode="contain" style={StyleSheet.absoluteFill}/>:<><CameraView key={kind+'-'+round} ref={camera} style={StyleSheet.absoluteFill} facing="back" mode="picture" autofocus="on" enableTorch={torch} zoom={zoom} pictureSize={pictureSize} onCameraReady={cameraReady} onMountError={e=>setHint(e.message)}/><View pointerEvents="none" style={s.guideLayer}><View onLayout={e=>setGuide(e.nativeEvent.layout)} style={[s.guide,{width:Math.min(preview.width*.86,preview.height*.68*(id?1.586:3.4)),aspectRatio:id?1.586:3.4}]}/></View></>}
 </View><View style={s.footer}><View style={s.row}>{working&&<ActivityIndicator color="#42d7ae"/>}<Text accessibilityLiveRegion="polite" style={s.hint}>{hint}</Text></View>{candidate?<><View style={s.row}>{button('↶ Rotate left',()=>{void rotatePhoto(-90)},working)}{button('Rotate right ↷',()=>{void rotatePhoto(90)},working)}</View><View style={s.row}>{button(working?'Saving…':'Accept Photo',()=>{void accept()},working)}{button('Retake',retake,working)}</View></>:<><View style={s.row}>{button(torch?'Torch off':'Torch on',()=>setTorch(!torch))}{button('Zoom '+(1+zoom*4).toFixed(1)+'×',()=>setZoom(z=>z>=.3?0:z+.15))}</View>{button('Take Photo',()=>{void take()},!ready||working||!guide)}</>}</View></SafeAreaView>
}
const s=StyleSheet.create({screen:{flex:1,backgroundColor:'#091622'},header:{padding:16},row:{flexDirection:'row',alignItems:'center',gap:10},title:{flex:1,fontSize:22,fontWeight:'800',color:'#f1f7fc'},copy:{fontSize:13,color:'#aec1d0',lineHeight:21,marginTop:8},preview:{flex:1,minHeight:90,overflow:'hidden',backgroundColor:'#030a0f'},guideLayer:{position:'absolute',top:0,left:0,right:0,bottom:0,justifyContent:'center',alignItems:'center'},guide:{borderWidth:3,borderColor:'#ff914d',borderRadius:16},footer:{padding:16},hint:{flex:1,color:'#d4e6f2',lineHeight:20,fontSize:13,minHeight:44},button:{padding:14,borderRadius:10,backgroundColor:'#294759',alignItems:'center',marginTop:8,flexGrow:1},buttonText:{color:'#fff',fontWeight:'700',fontSize:14}});
