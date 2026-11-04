import {useCallback,useEffect,useMemo,useRef,useState} from 'react';

// Audible feedback stays enabled. The browser still controls autoplay and output volume.
export function useTerminalSound(){
 const context=useRef(null),sources=useRef(new Set()),mounted=useRef(false);
 const[ready,setReady]=useState(false),[available,setAvailable]=useState(true);
 const ensure=useCallback(()=>{
  try{
   if(!context.current||context.current.state==='closed'){
    const Audio=window.AudioContext||window.webkitAudioContext;
    if(!Audio){if(mounted.current)setAvailable(false);return null;}
    const ac=new Audio();context.current=ac;
    ac.onstatechange=()=>{if(mounted.current&&context.current===ac)setReady(ac.state==='running');};
   }
   return context.current;
  }catch{if(mounted.current){setAvailable(false);setReady(false);}return null;}
 },[]);
 const unlock=useCallback(()=>{
  const ac=ensure();if(!ac)return;
  if(ac.state==='running'){if(mounted.current)setReady(true);return;}
  ac.resume().then(()=>{if(mounted.current&&context.current===ac)setReady(ac.state==='running');}).catch(()=>{if(mounted.current)setReady(false);});
 },[ensure]);
 const stop=useCallback(()=>{
  for(const source of sources.current){try{source.osc.stop();}catch{}source.osc.disconnect();source.gain.disconnect();}
  sources.current.clear();
 },[]);
 const beep=useCallback((frequencies,duration,gap)=>{
  const ac=ensure();if(!ac)return;unlock();
  // Never queue a delayed alarm while autoplay is suspended.
  if(ac.state!=='running')return;
  stop();let start=ac.currentTime+0.015;
  frequencies.forEach(frequency=>{
   const osc=ac.createOscillator(),gain=ac.createGain(),source={osc,gain};
   osc.type='triangle';osc.frequency.value=frequency;
   gain.gain.setValueAtTime(0,start);
   gain.gain.linearRampToValueAtTime(0.8,start+0.012);
   gain.gain.setValueAtTime(0.8,start+duration-0.04);
   gain.gain.linearRampToValueAtTime(0,start+duration);
   osc.connect(gain);gain.connect(ac.destination);sources.current.add(source);
   osc.onended=()=>{osc.disconnect();gain.disconnect();sources.current.delete(source);};
   osc.start(start);osc.stop(start+duration+0.01);start+=duration+gap;
  });
 },[ensure,unlock,stop]);
 const playGranted=useCallback(()=>beep([1047,1568],0.23,0.07),[beep]);
 const playDenied=useCallback(()=>beep([392,294,392],0.3,0.09),[beep]);
 const testSound=useCallback(()=>{
  const ac=ensure();if(!ac)return;
  ac.resume().then(playGranted).catch(()=>{if(mounted.current)setReady(false);});
 },[ensure,playGranted]);
 useEffect(()=>{
  mounted.current=true;unlock();
  const visible=()=>{if(document.visibilityState==='visible')unlock();};
  window.addEventListener('pointerdown',unlock,true);
  window.addEventListener('keydown',unlock,true);
  window.addEventListener('focus',unlock);
  document.addEventListener('visibilitychange',visible);
  return()=>{
   mounted.current=false;window.removeEventListener('pointerdown',unlock,true);
   window.removeEventListener('keydown',unlock,true);window.removeEventListener('focus',unlock);
   document.removeEventListener('visibilitychange',visible);stop();
   const ac=context.current;context.current=null;
   if(ac){ac.onstatechange=null;ac.close().catch(()=>{});}
  };
 },[unlock,stop]);
 return useMemo(()=>({ready,available,playGranted,playDenied,testSound}),[ready,available,playGranted,playDenied,testSound]);
}
