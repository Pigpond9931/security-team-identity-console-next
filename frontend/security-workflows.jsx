import React,{useEffect,useState} from 'react';
import {ShieldCheck,Link2,Camera} from 'lucide-react';

export function PrivacyNotice({api}){
 const[data,setData]=useState(null),[error,setError]=useState('');
 return <details className="privacy-notice" onToggle={e=>{if(e.currentTarget.open&&!data)api('/api/terms').then(setData).catch(e=>setError(e.message))}}><summary>Aviso de privacidad del proyecto</summary>{error&&<p role="alert">{error}</p>}{data&&<><p>{data.body.intro}</p>{data.body.puntos.map(([title,text])=><p key={title}><strong>{title}. </strong>{text}</p>)}<p>{data.body.footer}</p></>}</details>
}

export function ActivationPage({api}){
 const[error,setError]=useState(''),[done,setDone]=useState(false);
 useEffect(()=>{let active=true;async function run(){try{await api('/api/terms');const token=new URLSearchParams(location.hash.slice(1)).get('ticket');if(!token)throw Error('Solicita un enlace privado de activación a la administración.');await api('/api/auth/activate',{body:{ticket:token}});history.replaceState(null,'','/activate');if(active)setDone(true)}catch(e){if(active)setError(e.message)}}run();return()=>{active=false}},[api]);
 return <main className="phone-scanner"><header><ShieldCheck/>SECURITY TEAM · PRIMER INGRESO</header><h1>Activación privada</h1>{error?<p role="alert">{error}</p>:<p>{done?'Este navegador ya está habilitado durante cinco minutos. Inicia sesión con tu matrícula y la contraseña inicial para registrar tu contraseña privada y autenticador.':'Comprobando activación…'}</p>}{done&&<a href="/" className="v130-btn primary">Continuar al inicio de sesión</a>}<p>Entrega este enlace únicamente al titular. La administración nunca necesita conocer su contraseña privada ni sus códigos del autenticador.</p></main>
}

export function ActivationIssuer({api,matricula}){
 const[data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[copied,setCopied]=useState(false);
 useEffect(()=>{setData(null);setError('');setCopied(false)},[matricula]);
 return <article className="v130-panel"><h3>Primer ingreso sin enlace ni QR</h3><p>Verifica la identidad del titular y entrégale una contraseña temporal individual. Se muestra aquí una sola vez, vence en 24 horas y se consume al iniciar la configuración. La persona crea su contraseña privada y configura su autenticador.</p>{error&&<p role="alert">{error}</p>}<button className="v130-btn primary" disabled={busy} onClick={async()=>{setBusy(true);setError('');setCopied(false);setData(null);try{setData(await api('/api/users/initial-password',{body:{matricula}}))}catch(e){setError(e.message)}finally{setBusy(false)}}}><ShieldCheck size={16}/>{data?'Generar otra y revocar la anterior':'Generar contraseña temporal individual'}</button>{data&&<div role="status"><p><strong>Matrícula: {matricula}</strong></p><code className="mono" style={{overflowWrap:'anywhere',userSelect:'all'}}>{data.temporary_password}</code><p>Vence: {new Date(data.expires_at*1000).toLocaleString('es-MX')}. Tiene cinco minutos para completar contraseña y MFA después de utilizarla.</p><button className="v130-btn" onClick={async()=>{try{await navigator.clipboard.writeText(data.temporary_password);setCopied(true)}catch(e){setError('Selecciona y copia la contraseña manualmente.')}}}>{copied?'Contraseña copiada':'Copiar contraseña temporal'}</button><button className="v130-btn" onClick={()=>{setData(null);setCopied(false)}}>Ocultar contraseña</button><p>Entrégala únicamente al titular. Si cancela o deja vencer la configuración, genera otra. No se puede consultar después.</p></div>}</article>
}

export function CameraDestinations({api}){
 const[data,setData]=useState(null),[url,setUrl]=useState(''),[error,setError]=useState('');
 async function load(){try{setData(await api('/api/cctv/destinations'))}catch(e){setError(e.message)}}
 useEffect(()=>{load()},[api]);
 async function act(action,value=url){try{setData(await api('/api/cctv/destinations',{body:{action,url:value}}));setError('');if(action==='request')setUrl('')}catch(e){setError(e.message)}}
 if(!data)return null;
 return <details className="v130-camera-guide"><summary>Destinos de cámaras IP aprobados</summary><p>El servidor solo conecta con estas direcciones exactas. Al cambiar la IP, solicita el nuevo destino y pide su aprobación a un administrador global. Las cámaras del navegador no necesitan esta aprobación de red.</p>{error&&<p role="alert">{error}</p>}<label>Dirección completa a autorizar<input value={url} maxLength={2048} placeholder="http://192.168.1.50:8081/video" onChange={e=>setUrl(e.target.value)}/></label><button className="v130-btn" onClick={()=>act('request')}><Camera size={16}/>Solicitar destino de cámara</button>{data.destinations.map(d=><div className="camera-destination" key={d.url}><strong>{d.url}</strong><span>{d.status==='approved'?'Aprobado':d.status==='revoked'?'Revocado':'Pendiente'}</span>{data.can_approve&&<button className="v130-btn" onClick={()=>act(d.status==='approved'?'revoke':'approve',d.url)}>{d.status==='approved'?'Revocar destino':'Aprobar destino'}</button>}</div>)}</details>
}
