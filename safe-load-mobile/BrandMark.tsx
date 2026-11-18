import React from 'react';
import {View} from 'react-native';
import {SvgXml} from 'react-native-svg';
import {lockArtwork} from './lockArtwork';
export default function BrandMark(){return <View accessible accessibilityRole="image" accessibilityLabel="Safe Load armored lock emblem" style={{width:60,height:69}}><SvgXml xml={lockArtwork} width={60} height={69}/></View>}
