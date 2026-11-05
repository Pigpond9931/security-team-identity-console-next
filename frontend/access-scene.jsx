import React,{useEffect,useRef,useState} from 'react';
import {Pause,Play,ArrowUpRight} from 'lucide-react';

// Original local artwork. No video downloads, telemetry or GPU dependency.
// The nested metallic ribbons suggest one continuous, controlled path.
export function AccessScene({children}){
 const canvasRef=useRef(null),surfaceRef=useRef(null),clockRef=useRef(0);
 const [paused,setPaused]=useState(false),[reduced,setReduced]=useState(document.documentElement.dataset.motion==='reduced');
 useEffect(()=>{
  const canvas=canvasRef.current,host=surfaceRef.current,ctx=canvas.getContext('2d');
  if(!ctx)return;
  let frame=0,time=clockRef.current,last=0,width=1,height=1,visible=true,disposed=false;
  let pointer={x:0,y:0},smoothed={x:0,y:0};
  const ring=[];
  // A tubular torus knot, assembled from individual reflective ribbons.
  for(let i=0;i<240;i++){
   const t=i/240*Math.PI*2,r=108+36*Math.cos(3*t);
   ring.push([r*Math.cos(2*t),r*Math.sin(2*t),36*Math.sin(3*t)]);
  }
  const project=(p,angle)=>{
   let [x,y,z]=p;
   const a=angle+smoothed.x*.12,c=Math.cos(a),s=Math.sin(a);
   [x,z]=[x*c+z*s,-x*s+z*c];
   const tilt=.78+smoothed.y*.09;
   [y,z]=[y*Math.cos(tilt)-z*Math.sin(tilt),y*Math.sin(tilt)+z*Math.cos(tilt)];
   const scale=Math.min(width/380,height/365),depth=600/(600-z);
   return [width*.5+x*scale*depth,height*.49+y*scale*depth,z,depth];
  };
  const draw=()=>{
   ctx.clearRect(0,0,width,height);
   smoothed.x+=(pointer.x-smoothed.x)*.045;smoothed.y+=(pointer.y-smoothed.y)*.045;
   const angle=-.28+Math.sin(time*.16)*.23;
   const pieces=[];
   for(let band=0;band<20;band++){
    const u=(band/20)*Math.PI*2,un=((band+.72)/20)*Math.PI*2;
    for(let i=0;i<ring.length;i++){
     const next=(i+1)%ring.length;
     const point=(index,v)=>{
      const p=ring[index],t=index/ring.length*Math.PI*2;
      const radial=[Math.cos(2*t),Math.sin(2*t),0];
      return project([p[0]+radial[0]*Math.cos(v)*23,p[1]+radial[1]*Math.cos(v)*23,p[2]+Math.sin(v)*23],angle);
     };
     const p=[point(i,u),point(next,u),point(next,un),point(i,un)];
     pieces.push({p,z:p.reduce((n,v)=>n+v[2],0)/4,u,t:i/ring.length});
    }
   }
   pieces.sort((a,b)=>a.z-b.z);
   for(const {p,z,u,t} of pieces){
    const highlight=Math.pow(Math.max(0,Math.cos(u-1.1+Math.sin(t*6.28+time*.35)*.55)),7);
    const silver=Math.max(20,Math.min(240,56+(z+120)*.31+highlight*135));
    ctx.fillStyle=`rgb(${Math.round(silver*.77)},${Math.round(silver*.91)},${Math.round(Math.min(255,silver*1.08))})`;
    ctx.beginPath();ctx.moveTo(p[0][0],p[0][1]);
    for(let j=1;j<4;j++)ctx.lineTo(p[j][0],p[j][1]);
    ctx.closePath();ctx.fill();
   }
  };
  const tick=now=>{
   if(disposed)return;
   if(now-last>=1000/24){time+=Math.min((now-last)/1000,.06);clockRef.current=time;last=now;draw();}
   frame=requestAnimationFrame(tick);
  };
  const sync=()=>{
   cancelAnimationFrame(frame);frame=0;
   const reduce=document.documentElement.dataset.motion==='reduced';
   setReduced(reduce);
   const running=!paused&&!reduce&&!document.hidden&&visible;
   canvas.dataset.animation=running?'running':'paused';
   if(running){last=performance.now();frame=requestAnimationFrame(tick);}else draw();
  };
  const resize=()=>{
   const rect=host.getBoundingClientRect();width=rect.width;height=rect.height;
   const ratio=Math.min(devicePixelRatio||1,1.5);
   canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);
   ctx.setTransform(ratio,0,0,ratio,0,0);draw();
  };
  const move=e=>{
   const rect=host.getBoundingClientRect();
   pointer={x:(e.clientX-rect.left)/rect.width-.5,y:(e.clientY-rect.top)/rect.height-.5};
  };
  const leave=()=>{pointer={x:0,y:0};};
  const observer=new MutationObserver(sync);observer.observe(document.documentElement,{attributes:true,attributeFilter:['data-motion']});
  const sizing=new ResizeObserver(resize);sizing.observe(host);
  const visibility=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;sync();});visibility.observe(host);
  document.addEventListener('visibilitychange',sync);host.addEventListener('pointermove',move);host.addEventListener('pointerleave',leave);
  resize();sync();
  return()=>{disposed=true;cancelAnimationFrame(frame);observer.disconnect();sizing.disconnect();visibility.disconnect();document.removeEventListener('visibilitychange',sync);host.removeEventListener('pointermove',move);host.removeEventListener('pointerleave',leave);};
 },[paused]);
 return <section className="auth-story cinematic-story">
  <div className="scene-brand">{children}<span className="scene-edition">NEXT / 01</span></div>
  <div className="scene-art" ref={surfaceRef}><div className="scene-halo"/><canvas ref={canvasRef} aria-hidden="true"/><span className="scene-coordinate" aria-hidden="true">ST — 01 / CONTINUIDAD</span></div>
  <div className="auth-story-content"><span className="eyebrow light">IDENTIDAD. ACCESO. CONFIANZA.</span><h1>La confianza<br/>empieza <em>contigo.</em></h1><p>Personas, permisos y espacios.<br/>Todo conectado, bajo tu control.</p></div>
  <div className="auth-story-footer"><span>SECURITY TEAM <i/> UPY <ArrowUpRight size={13}/></span><button type="button" className="scene-pause" disabled={reduced} aria-pressed={paused||reduced} onClick={()=>setPaused(v=>!v)}>{paused||reduced?<Play size={12}/>:<Pause size={12}/>}<span>{reduced?'Movimiento reducido':paused?'Reanudar animación':'Pausar animación'}</span></button></div>
 </section>;
}
