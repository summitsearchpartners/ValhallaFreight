import React,{useEffect,useState} from 'react';
import {View,Text,Image,ActivityIndicator,StyleSheet} from 'react-native';
type Props={source?:{uri:string};fallbackSource?:{uri:string};label:string;loading:boolean;error?:string};
export default function EvidencePhoto({source,fallbackSource,label,loading,error}:Props){
 const [failed,setFailed]=useState<string[]>([]);
 useEffect(()=>setFailed([]),[source?.uri,fallbackSource?.uri]);
 const current=[source,fallbackSource].find(value=>value&&!failed.includes(value.uri));
 if(current)return <Image source={current} accessibilityLabel={label} onError={()=>setFailed(previous=>previous.includes(current.uri)?previous:[...previous,current.uri])} style={s.photo} resizeMode="contain"/>;
 if(error||failed.length>0)return <View accessibilityRole="alert" style={s.message}><Text style={s.error}>{error||`${label} could not be displayed. Tap Reload saved photos, or retake this photo if it is a new capture.`}</Text></View>;
 if(loading)return <View accessibilityLabel={'Loading '+label} style={s.message}><ActivityIndicator color="#ff914d"/><Text style={s.copy}>Loading {label.toLowerCase()}…</Text></View>;
 return null;
}
const s=StyleSheet.create({photo:{height:260,width:'100%',backgroundColor:'#edf2f7',borderRadius:12,marginVertical:14},message:{padding:18,borderRadius:12,borderWidth:1,borderColor:'#3b5667',marginVertical:12},copy:{color:'#b4c8d6',lineHeight:22,marginTop:10},error:{color:'#ff8585',lineHeight:22}});
