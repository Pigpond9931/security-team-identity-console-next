import {CameraInventory} from './camera-management.jsx';
import {TerminalClock,TerminalDecision,TerminalQuickEvents,TerminalPresence} from './terminal-design.jsx';
import {SurveillanceCenter} from './surveillance.jsx';
import {TerminalAreaPicker,TerminalOperations} from './terminal-controls.jsx';
import {ActivationIssuer,CameraDestinations} from './security-workflows.jsx';
import {AccessFeedback} from './access-feedback.jsx';
import {BrowserCameras,CameraHud} from './browser-cameras.jsx';
/* ============================================================================
 * SECURITY TEAM · Identity Console
 * Archivo: 04_frontend_components.jsx
 * Destino: IMPORTAR desde frontend/app.jsx y montar en las pestañas/modales.
 * ----------------------------------------------------------------------------
 * Componentes de los 7 módulos de la v1.3.0. Respeta la estética existente:
 * fondo #f6f7f6, sidebar #182323, verde #155d45, texto #5d6e63, Manrope,
 * iconos lucide-react y diseño responsivo.
 *
 * CONVENCIONES ASUMIDAS (adáptalas a tu app.jsx):
 *   - `api(path, {method, body})` : fetch a la API con cookies + CSRF.
 *   - `toast(msg, type)`          : notificación existente (o usa alerta simple).
 * Resuelve estas dos dependencias al integrar (ver 07_MASTER_PROMPT_CODEX.md).
 * ==========================================================================*/

import jsQR from "jsqr";
import {PhonePairing} from "./phone-scanner.jsx";
import {cameraAddressPaste,normalizeCameraAddress} from './camera-url.js';
import React, { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  ShieldCheck, ShieldX, IdCard, QrCode, ScanLine, Camera, Users, KeyRound,
  Activity, Video, AlertTriangle, Download, Share2, Smartphone, CheckCircle2,
  XCircle, RefreshCw, LogIn, LogOut, Volume2, VolumeX, ClipboardPaste,
} from "lucide-react";

const humanTime=s=>s?new Date(s).toLocaleString('es-MX'):'—';
export function BatchDeliveries({api}){
 const[data,setData]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');
 async function renew(){setBusy(true);try{setData(await api('/api/mobile-passes/renew',{body:{}}));setError('')}catch(e){setError(e.message)}finally{setBusy(false)}}
 function download(){const cell=value=>'"'+(/^[=+\-@\t\r]/.test(String(value))?"'":'')+String(value??'').replaceAll('"','""')+'"';const rows=[['ID','Titular','Tipo','Enlace privado de entrega'],...data.deliveries.map(v=>[v.id,v.name,v.kind,v.pass_url])];const a=document.createElement('a');a.href='data:text/csv;charset=utf-8,'+encodeURIComponent('\ufeff'+rows.map(row=>row.map(cell).join(',')).join('\r\n'));a.download='entregas-privadas-security-team.csv';a.click();}
 return <article className="v130-panel"><div className="v130-panel-head"><Smartphone/><h3>Entregas móviles del equipo</h3></div><p className="v130-muted">Si cambia el enlace del túnel, prepara las entregas de las cuentas habilitadas y los invitados vigentes en un paso. Las credenciales ya descargadas conservan su vigencia.</p><div className="v130-row wrap"><button className="v130-btn" disabled={busy} onClick={renew}>{busy?'Preparando enlaces…':'Renovar entregas móviles'}</button>{data&&<><button className="v130-btn" onClick={download}>Descargar lista privada CSV</button><button className="v130-btn" onClick={()=>setData(null)}>Ocultar entregas</button></>}</div>{error&&<p role="alert">{error}</p>}{data&&<><p role="status">{data.deliveries.length} enlaces preparados · {data.skipped.length} cuentas pendientes de habilitación.</p><p className="v130-muted">Entrega cada enlace únicamente a su titular. Este archivo contiene pases privados; no lo publiques en el grupo. Vigencia de entrega: cinco minutos.</p><details><summary>Ver entregas y pendientes</summary>{data.deliveries.map(v=><p key={v.id}>{v.id} · {v.name} · <a href={v.pass_url} target="_blank" rel="noreferrer">Abrir entrega privada</a></p>)}{data.skipped.map(v=><p key={v.id}>{v.id} · {v.name}: {v.reason}</p>)}</details></>}</article>;
}
export function QRBadgePanel({matricula,api,toast}){
 const[data,setData]=useState(null),[delivery,setDelivery]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false);
 const query='?matricula='+encodeURIComponent(matricula);
 useEffect(()=>{let active=true;setError('');setData(null);api('/api/users/qr-badge'+query).then(v=>active&&setData(v)).catch(e=>active&&setError(e.message));return()=>{active=false};},[matricula,api]);
 async function png(share=false){try{const r=await api('/api/users/qr-badge.png'+query);await shareFile(r,share);}catch(e){setError(e.message);}}
 async function issue(){setBusy(true);try{setDelivery(await api('/api/users/mobile-pass',{body:{matricula}}));}catch(e){setError(e.message);}finally{setBusy(false);}}
 return <article className="v130-panel"><div className="v130-panel-head"><IdCard/><h3>Gafete Digital QR</h3></div>{error&&<p role="status" className="v130-muted">{error}</p>}
 {data&&<div className="v130-badge-card"><div className="v130-badge-top">SECURITY TEAM</div><img className="v130-qr" src={'data:image/png;base64,'+data.qr_png_base64} alt="Gafete QR de acceso"/><h3>{data.badge.full_name}</h3><p>{data.badge.matricula} · {data.badge.role}</p><p>{data.badge.zones_labels.join(' · ')}</p><small>{data.badge.valid_hint}</small></div>}
 <div className="v130-row wrap">{data&&<><button className="v130-btn" onClick={()=>png()}>Descargar Credencial PNG</button><button className="v130-btn" onClick={()=>png(true)}>Compartir a Celular / WhatsApp</button></>}<button className="v130-btn primary" disabled={busy} onClick={issue}>Preparar entrega al celular</button></div>
 {delivery&&<Delivery data={delivery}/>}<p className="v130-muted v130-small">La firma protege la integridad; una fotografía puede copiarse. La terminal consulta vigencia, estado y permisos en cada lectura.</p></article>;
}
async function shareFile(r,share){const file=base64ToFile(r.png_base64,r.filename||'credencial.png');if(share&&navigator.canShare?.({files:[file]})){try{await navigator.share({files:[file],title:'Credencial SECURITY TEAM'});}catch(e){if(e.name!=='AbortError')throw e;}}else{await downloadBase64Png(r.png_base64,r.filename);if(share)window.open('https://wa.me/?text='+encodeURIComponent('Te enviaré mi credencial SECURITY TEAM como imagen adjunta.'),'_blank','noopener,noreferrer');}}
function Delivery({data}){return <div className="v130-created"><h4>Entrega privada al teléfono</h4><p>Escanea este enlace para leer los términos y activar tu gafete. Caduca en un máximo de cinco minutos. Compártelo solo con el titular.</p><img className="v130-qr" src={'data:image/png;base64,'+data.delivery_qr} alt="Enlace QR de entrega al celular"/><div className="v130-row wrap"><a className="v130-btn" href={data.pass_url} target="_blank" rel="noreferrer">Abrir pase móvil</a><button className="v130-btn" onClick={()=>navigator.clipboard?.writeText(data.pass_url)}>Copiar enlace privado</button></div><small>También puedes mostrar la credencial activada para que el titular le tome una fotografía. Los enlaces de entrega requieren conexión; una imagen guardada puede mostrarse sin Internet.</small></div>}
export function MobilePass({api,token}){
 const[data,setData]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[claimed,setClaimed]=useState(!token);
 const load=useCallback(async()=>{try{setData(await (!claimed&&token?api('/api/public-pass/preview',{body:{token}}):api('/api/public-pass')));setError('')}catch(e){setError(e.message)}},[api,token,claimed]);
 useEffect(()=>{api('/api/terms').then(load).catch(e=>setError(e.message))},[load]);
 useEffect(()=>{if(!claimed||!data?.pending_approval)return;const t=setInterval(load,1500);return()=>clearInterval(t)},[load,claimed,data?.pending_approval]);
 async function claim(){setBusy(true);try{await api('/api/terms');await api('/api/public-pass/claim',{body:{token}});history.replaceState(null,'','/pass');setClaimed(true);setData(null);setError('')}catch(e){setError(e.message)}finally{setBusy(false)}}
 async function accept(){setBusy(true);try{setData(await api('/api/public-pass/accept-terms',{body:{accepted:true,version:data.terms_version}}))}catch(e){setError(e.message)}finally{setBusy(false)}}
 if(error)return <main className="v130-pass"><h2>Pase no disponible</h2><p role="alert">{error}</p><a href="/">Iniciar sesión</a><p>Solicita una entrega nueva al anfitrión si venció o ya fue canjeada.</p></main>;
 if(!data)return <main className="v130-pass">Comprobando pase…</main>;
 if(data.requires_claim)return <main className="phone-scanner"><h1>Entrega privada de gafete</h1><p>{data.requires_login?'Inicia sesión con la matrícula y autenticador del titular en este navegador antes de canjear la entrega. Puedes mostrar tu QR directamente desde Mi QR.':'Canjea la entrega y compara el código con el anfitrión para autorizar este dispositivo.'}</p><button className="v130-btn primary" disabled={busy} onClick={claim}>Canjear entrega privada</button><a href="/" target="_blank" rel="noreferrer" className="v130-btn">Iniciar sesión como titular</a><p>El enlace caduca en cinco minutos y solo puede canjearse una vez. No se consume al previsualizarlo.</p></main>;
 if(data.pending_approval)return <main className="phone-scanner"><h1>Confirma tu teléfono con el anfitrión</h1><strong className="phone-confirm-code">{data.confirmation}</strong><p>El gafete se habilita cuando el anfitrión compare este código y autorice el dispositivo.</p></main>;
 if(!data.terms.accepted)return <TermsModal compact title={data.terms_title} body={data.terms_body} version={data.terms_version} busy={busy} onAccept={accept}/>;
 return <main className="v130-pass"><div className="v130-pass-card"><div className="v130-badge-top">SECURITY TEAM · GAFETE</div><img className="v130-qr big" src={'data:image/png;base64,'+data.qr_png_base64} alt="Gafete QR activado"/><h2>{data.badge.full_name}</h2><p>{data.badge.matricula} · {data.badge.role}</p><p>{data.badge.zones_labels.join(' · ')}</p><p>{data.badge.valid_hint}</p><button className="v130-btn" onClick={async()=>{try{await shareFile(await api('/api/public-pass?download=1'),false)}catch(e){setError(e.message)}}}>Descargar Credencial PNG</button><p>Sesión de entrega: 15 minutos. Descarga el gafete para conservar la imagen durante su vigencia.</p></div></main>;
}
export function UserAccess({target,actor,api,toast,readonly=false}){
 const[selected,setSelected]=useState([]),[error,setError]=useState('');
 useEffect(()=>{api('/api/users/zones?matricula='+encodeURIComponent(target.username)).then(r=>setSelected(r.zones)).catch(e=>setError(e.message));},[target.id,api]);
 async function save(){try{await api('/api/users/zones',{body:{matricula:target.username,zones:selected}});toast('Zonas actualizadas.');setError('');}catch(e){setError(e.message)}}
 return <><div className="v130-panel"><h3>Permisos de zonas</h3>{error&&<p role="alert">{error}</p>}{ZONES.map(z=><label className="v130-check" key={z.id}><input type="checkbox" disabled={readonly} checked={selected.includes(z.id)} onChange={e=>setSelected(e.target.checked?[...selected,z.id]:selected.filter(x=>x!==z.id))}/>{z.label}</label>)}{!readonly&&<button className="v130-btn" onClick={save}>Guardar zonas</button>}{!target.mfa_configured&&['system_admin','dpo'].includes(actor.role)&&!readonly&&<ActivationIssuer api={api} matricula={target.username}/>}<TermsStatusChip accepted={!!target.terms_accepted} acceptedAt={humanTime(target.terms_accepted_at)}/></div><LicensesPanel api={api} matricula={target.username} toast={toast} readonly={readonly&&actor.role!=='system_admin'}/><QRBadgePanel matricula={target.username} api={api} toast={toast}/></>;
}
export function VisitorsPanel({api,toast}){
 const[terms,setTerms]=useState(null);useEffect(()=>{api('/api/terms').then(setTerms).catch(()=>{})},[api]);
 const[list,setList]=useState([]),[pending,setPending]=useState([]),[created,setCreated]=useState(null),[error,setError]=useState(''),[busy,setBusy]=useState(false),[form,setForm]=useState({full_name:'',organization:'',visit_reason:'',allowed_zone:'GENERAL_ACCESS',duration:'4h',terms_accepted:false});
 const load=useCallback(()=>api('/api/visitors').then(r=>{setList(r.visitors);setPending(r.pending_devices||[])}).catch(e=>setError(e.message)),[api]);useEffect(()=>{load();const t=setInterval(load,2000);return()=>clearInterval(t)},[load]);
 const change=(k,v)=>setForm(f=>({...f,[k]:v}));
 async function create(e){e.preventDefault();setBusy(true);try{setCreated(await api('/api/visitors/create',{body:form}));await load();setError('');}catch(e){setError(e.message)}finally{setBusy(false)}}
 return <article className="v130-panel"><div className="v130-panel-head"><Users/><h2>Gestión de Invitados</h2></div>{error&&<p role="alert">{error}</p>}<form onSubmit={create}><div className="v130-row wrap">{[['full_name','Nombre completo'],['organization','Organización'],['visit_reason','Motivo de visita']].map(([key,label])=><label key={key}>{label}<input required={key==='full_name'} value={form[key]} maxLength={key==='full_name'?120:300} onChange={e=>change(key,e.target.value)}/></label>)}</div><div className="v130-row wrap"><label>Zona permitida<select value={form.allowed_zone} onChange={e=>change('allowed_zone',e.target.value)}>{ZONES.map(z=><option key={z.id} value={z.id}>{z.label}</option>)}</select></label><label>Duración<select value={form.duration} onChange={e=>change('duration',e.target.value)}>{['2h','4h','8h','24h'].map(d=><option key={d}>{d}</option>)}</select></label></div><p className="v130-muted">El invitado puede leer los términos desde el pase móvil. Marca la casilla solo si acaba de leerlos y aceptarlos presencialmente; queda registrado que tú lo atestiguaste.</p><label className="v130-check"><input type="checkbox" checked={form.terms_accepted} onChange={e=>change('terms_accepted',e.target.checked)}/>El titular aceptó presencialmente los términos mostrados</label><details><summary>Leer términos para aceptación presencial</summary>{terms?.body.puntos.map(([title,text])=><p key={title}><strong>{title}. </strong>{text}</p>)}</details><button className="v130-btn primary" disabled={busy}>Crear pase de invitado</button></form>
 {pending.map(d=><section className="phone-confirm" key={d.id}><h3>Confirmar teléfono de {d.full_name}</h3><strong className="phone-confirm-code">{d.confirmation}</strong><p>Comprueba presencialmente que este es el código del teléfono del invitado.</p><button className="v130-btn primary" onClick={async()=>{try{await api('/api/visitors/approve-device',{body:{id:d.id,confirmation:d.confirmation}});await load()}catch(e){setError(e.message)}}}>Confirmar teléfono del invitado</button></section>)}
 {created&&<div className="v130-created"><h3>{created.visitor.full_name}</h3>{created.qr_png_base64&&<><img className="v130-qr" src={'data:image/png;base64,'+created.qr_png_base64} alt="QR temporal del invitado"/><div className="v130-row wrap"><button className="v130-btn" onClick={()=>shareFile({...created,filename:'invitado.png'},false)}>Descargar Credencial PNG</button><button className="v130-btn" onClick={()=>shareFile({...created,filename:'invitado.png'},true)}>Compartir a Celular / WhatsApp</button></div></>}<Delivery data={created}/></div>}
 <div className="table-scroll"><table className="v130-table"><thead><tr><th>Invitado</th><th>Zona</th><th>Vigencia</th><th>Términos</th><th>Estado</th><th>Acción</th></tr></thead><tbody>{list.map(v=><tr key={v.visitor_id}><td>{v.full_name}<small>{v.visitor_id} · {v.organization}</small></td><td>{ZONE_LABEL(v.allowed_zone)}</td><td>{humanTime(v.valid_until)}</td><td>{v.terms_accepted?'Aceptados':'Pendientes'}</td><td>{v.status}</td><td>{v.status==='ACTIVE'&&<><button className="v130-btn" onClick={async()=>{try{setCreated(await api('/api/visitors/delivery',{body:{visitor_id:v.visitor_id}}));await load();setError('')}catch(e){setError(e.message)}}}>Renovar entrega</button><button className="v130-btn" onClick={async()=>{try{await api('/api/visitors/revoke',{body:{visitor_id:v.visitor_id}});await load();}catch(e){setError(e.message)}}}>Revocar pase</button></>}</td></tr>)}</tbody></table></div></article>;
}


export function AccessTerminal({api,toast}){
 const[terminalData,setTerminalData]=useState(null),[tab,setTab]=useState('operate'),[method,setMethod]=useState('rfid'),[processing,setProcessing]=useState(false),[online,setOnline]=useState(null),[focused,setFocused]=useState(false);
 const[zone,setZone]=useState('GENERAL_ACCESS'),[direction,setDirection]=useState('AUTO'),[ref,setRef]=useState(''),[rfid,setRfid]=useState(''),[kiosk,setKiosk]=useState(false),[last,setLast]=useState(null),[flash,setFlash]=useState(null),[presence,setPresence]=useState([]),[error,setError]=useState(''),[devices,setDevices]=useState([]),[device,setDevice]=useState(''),[camera,setCamera]=useState(false),[capacity,setCapacity]=useState(null);
 const sound=useTerminalSound(),soundRef=useRef(sound);soundRef.current=sound;
 const video=useRef(null),stream=useRef(null),seen=useRef(null),reading=useRef(false),input=useRef(null),timer=useRef(null),cameraGeneration=useRef(0);
 useEffect(()=>{const frame=requestAnimationFrame(()=>input.current?.focus({preventScroll:true}));return()=>cancelAnimationFrame(frame)},[]);
 const loadPresence=useCallback(async()=>{const r=await api('/api/access/terminal');setTerminalData(r);setPresence(r.presence)},[api]);
 function changeZone(value){if(reading.current)return;stopCamera();setRfid('');setZone(value);setError('');requestAnimationFrame(()=>input.current?.focus({preventScroll:true}))}
 function dismissFeedback(){setFlash(null);requestAnimationFrame(()=>{if(!document.querySelector('.access-feedback'))input.current?.focus({preventScroll:true})})}
 function show(event){if(!event||Number(event.id)<=Number(seen.current))return;seen.current=event.id;setLast(event);setFlash(event);event.verdict==='VERIFIED'?soundRef.current.playGranted():soundRef.current.playDenied();loadPresence().catch(e=>setError(e.message));}
 useEffect(()=>{let stopped=false,polling=false,initial=true,cycles=0;async function poll(){if(polling)return;polling=true;try{const r=await api('/api/access/latest?limit=1');if(!stopped){setOnline(true);if(initial){initial=false;if(seen.current===null){seen.current=r.event?.id||0;setLast(r.event)}}else if(r.event&&Number(r.event.id)>Number(seen.current))show(r.event);else if(++cycles%5===0)loadPresence().catch(e=>setError(e.message));}}catch(e){if(!stopped){setOnline(false);setError(e.message)}}finally{polling=false;}}poll();loadPresence().catch(e=>setError(e.message));api('/api/access/settings').then(setCapacity).catch(()=>{});const id=setInterval(poll,1000);return()=>{stopped=true;clearInterval(id);stopCamera();};},[api]);
 async function verify(value,method){if(reading.current)return;reading.current=true;setProcessing(true);dismissFeedback();try{const r=await api('/api/access/verify',{body:{ref:value,method,zone,direction}});show(r.result);setError('');}catch(e){setError(e.message)}finally{reading.current=false;setProcessing(false);}}
 function stopCamera(){cameraGeneration.current++;clearTimeout(timer.current);stream.current?.getTracks().forEach(t=>t.stop());stream.current=null;setCamera(false);}
 async function startCamera(){stopCamera();const generation=cameraGeneration.current;try{if(!navigator.mediaDevices?.getUserMedia)throw Error('Este navegador requiere HTTPS y permiso de cámara. También puedes cargar una imagen QR.');const activeStream=await navigator.mediaDevices.getUserMedia({video:device?{deviceId:{exact:device},width:{ideal:640},height:{ideal:480}}:{facingMode:{ideal:'environment'},width:{ideal:640},height:{ideal:480}}});if(generation!==cameraGeneration.current){activeStream.getTracks().forEach(t=>t.stop());return}stream.current=activeStream;video.current.srcObject=activeStream;await video.current.play();setCamera(true);setDevices((await navigator.mediaDevices.enumerateDevices()).filter(d=>d.kind==='videoinput'));const canvas=document.createElement('canvas');async function tick(){if(stream.current!==activeStream)return;try{const value=decodeQR(video.current,canvas);if(value){stopCamera();await verify(value,'QR_BADGE');return}}catch{}timer.current=setTimeout(tick,200)}tick();setError('');}catch(e){stopCamera();setError(e.message)}}
 async function capture(file){if(!file)return;try{if(file.size>12*1024*1024)throw Error('Usa una imagen de hasta 12 MB.');const bmp=await createImageBitmap(file);try{const value=decodeQR(bmp,document.createElement('canvas'),1600);if(!value)throw Error('No se encontró un QR legible. Acerca la imagen y evita reflejos.');await verify(value,'QR_BADGE')}finally{bmp.close()}}catch(e){setError(e.message)}}
 function selectTab(value,focus=true){if(reading.current)return;stopCamera();setRfid('');setTab(value);if(value==='operate'&&focus)requestAnimationFrame(()=>input.current?.focus({preventScroll:true}))}
 function selectMethod(value){if(reading.current)return;stopCamera();setMethod(value);if(value==='rfid')requestAnimationFrame(()=>input.current?.focus({preventScroll:true}))}
 const tabs=[['operate','Operación'],['activity','Actividad'],...(terminalData?.can_configure?[['settings','Configuración']]:[])];
 function tabKey(e){if(!['ArrowRight','ArrowLeft','Home','End'].includes(e.key))return;e.preventDefault();const i=tabs.findIndex(([id])=>id===tab),next=e.key==='Home'?0:e.key==='End'?tabs.length-1:(i+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;selectTab(tabs[next][0],false);document.getElementById('terminal-tab-'+tabs[next][0])?.focus()}
 async function checkout(id){if(reading.current)return;reading.current=true;setProcessing(true);try{show((await api('/api/access/checkout',{body:{event_id:id}})).result);setError('')}catch(e){setError(e.message)}finally{reading.current=false;setProcessing(false)}}
 return <div className={'v130-terminal terminal-console '+(kiosk?'terminal-kiosk':'')}>
 {flash&&<AccessFeedback key={flash.id} event={flash} zoneLabel={ZONE_LABEL(flash.zone)} onClose={dismissFeedback} onScan={value=>verify(value,'RFID_125KHZ')}/>}
 <header className="terminal-banner"><div><span className="terminal-eyebrow">SECURITY TEAM / CONTROL DE ACCESO</span><h2>Terminal de Acceso</h2><p>Una credencial. Una decisión. Un registro.</p></div><TerminalClock/><div className="terminal-banner-actions"><span className={'terminal-online '+(online===true?'connected':'')} role="status"><i/>{online===null?'Conectando terminal':online?'Terminal conectada':'Sin conexión confirmada'}</span><div><button className="v130-btn terminal-sound" aria-pressed={sound.enabled} onClick={()=>sound.setEnabled(!sound.enabled)}>{sound.enabled?<Volume2 size={16}/>:<VolumeX size={16}/>}Sonido de Terminal: {sound.enabled?'Activo':'Silencio'}</button><button className="v130-btn" onClick={()=>{stopCamera();setRfid('');setKiosk(!kiosk);if(kiosk)requestAnimationFrame(()=>input.current?.focus({preventScroll:true}))}}>{kiosk?'Salir de pantalla de kiosco':'Pantalla de kiosco'}</button></div></div></header>
 <div className="terminal-tabs" role="tablist" aria-label="Secciones de la terminal" hidden={kiosk}>{tabs.map(([id,label])=><button key={id} id={'terminal-tab-'+id} type="button" role="tab" tabIndex={tab===id?0:-1} aria-selected={tab===id} aria-controls={'terminal-panel-'+id} onKeyDown={tabKey} onClick={()=>selectTab(id)}>{id==='operate'?<ScanLine size={17}/>:id==='activity'?<Activity size={17}/>:<KeyRound size={17}/>} {label}</button>)}</div>
 {error&&<p className="terminal-error" role="alert"><AlertTriangle size={18}/>{error}</p>}
 <div id="terminal-panel-operate" role="tabpanel" aria-labelledby="terminal-tab-operate" hidden={tab!=='operate'||kiosk}>
 <TerminalOperations data={terminalData} zone={zone} api={api} onData={setTerminalData} onError={setError} view="summary"/>

 <div className="terminal-workspace"><div className="terminal-area-rail"><TerminalAreaPicker data={terminalData} zone={zone} onChange={changeZone} active={tab==='operate'&&!kiosk&&!processing}/></div><article className="terminal-reader"><header><div><span className="terminal-eyebrow">LECTURA DE CREDENCIALES</span><h3>{processing?'Verificando identidad…':'Presenta una credencial'}</h3><p className="terminal-active-zone">{ZONE_LABEL(zone)}</p></div><ScanLine size={26}/></header><div className="terminal-methods" role="group" aria-label="Método de lectura">{[['rfid','Tarjeta RFID',IdCard],['qr','Gafete QR',QrCode],['phone','Teléfono',Smartphone]].map(([id,label,Icon])=><button type="button" key={id} disabled={processing} aria-pressed={method===id} onClick={()=>selectMethod(id)}><Icon size={19}/>{label}</button>)}</div>
 <div className="terminal-rfid-intro" hidden={method!=='rfid'}><div className={'terminal-scan-art '+(processing?'checking':'')} aria-hidden="true"><span/><IdCard size={64} strokeWidth={1.3}/><i/></div><h4>{processing?'Comprobando permisos':'Acerca tu tarjeta al lector'}</h4><p>El lector USB enviará la credencial y Enter. El resultado se mostrará automáticamente.</p></div>
 <div className="terminal-qr-tools" hidden={method!=='qr'}><div className="terminal-qr-preview"><video hidden={!camera} className="v130-video" ref={video} muted playsInline/>{!camera&&<div><QrCode size={42}/><strong>Escanea el gafete</strong><span>Usa la webcam, una imagen o el contenido del QR.</span></div>}</div><div className="v130-row wrap"><label>Cámara<select value={device} disabled={processing} onChange={e=>{setDevice(e.target.value);stopCamera()}}><option value="">Trasera / predeterminada</option>{devices.map(d=><option key={d.deviceId} value={d.deviceId}>{d.label||'Cámara'}</option>)}</select></label><button className="v130-btn" disabled={processing} onClick={camera?stopCamera:startCamera}><Camera size={17}/>{camera?'Apagar cámara':'Encender cámara QR'}</button></div><label className="terminal-upload"><Download size={19}/><span>Capturar / cargar imagen QR<small>Selecciona una imagen o toma una foto</small></span><input type="file" aria-label="Imagen QR de la terminal" accept="image/*" capture="environment" disabled={processing} onChange={e=>{capture(e.target.files[0]);e.target.value=''}}/></label><details className="terminal-manual-qr"><summary><ClipboardPaste size={16}/>Introducir contenido QR</summary><div className="v130-row wrap"><input aria-label="Token QR" placeholder="Pega el contenido del QR" value={ref} onChange={e=>setRef(e.target.value)}/><button className="v130-btn" disabled={processing||!ref.trim()} onClick={()=>verify(ref,'QR_BADGE')}>Verificar QR</button></div></details></div>
 <div hidden={method!=='phone'}><PhonePairing api={api} zone={zone} direction={direction}/></div>
 <div className={'terminal-reader-entry '+(focused?'is-focused':'')}><div className="terminal-reader-status"><span className={focused?'ready':''}><i/>{processing?'Verificando…':focused?'Lector preparado':'Preparar lector para recibir'}</span><small>USB · 125 kHz</small></div><label>Lector RFID USB 125 kHz<input ref={input} autoComplete="off" spellCheck={false} className="v130-rfid-input" placeholder="Pasa la tarjeta y Enter" value={rfid} maxLength={32} disabled={processing} onFocus={()=>setFocused(true)} onBlur={()=>setFocused(false)} onChange={e=>setRfid(e.target.value)} onKeyDown={e=>{if(e.key==='Enter'){e.preventDefault();if(rfid.trim())verify(rfid,'RFID_125KHZ');setRfid('');}}}/></label><button className="v130-btn" disabled={processing} onClick={()=>input.current?.focus()}><IdCard size={16}/>Preparar lector USB</button></div><details className="terminal-reading-options"><summary>Opciones de zona y movimiento</summary><div className="terminal-route"><div><span className="terminal-route-icon"><ShieldCheck size={21}/></span><div><span>ACCESO SELECCIONADO</span><strong>{ZONE_LABEL(zone)}</strong></div></div><label>Zona / Puerta<select aria-label="Zona / Puerta" value={zone} disabled={processing} onChange={e=>changeZone(e.target.value)}>{(terminalData?.zones||ZONES).map(z=><option key={z.id} value={z.id}>{z.label}</option>)}</select></label><label>Acción<select value={direction} disabled={processing} onChange={e=>setDirection(e.target.value)}><option value="AUTO">Automático Entrada/Salida</option><option value="CHECK_IN">Check-In (Entrada)</option><option value="CHECK_OUT">Check-Out (Salida)</option></select></label></div></details><footer><ShieldCheck size={15}/>Cada lectura comprueba identidad y permisos en el servidor.</footer></article>
 <aside className="terminal-result-column"><TerminalDecision event={last} zoneLabel={last?ZONE_LABEL(last.zone):''}/><TerminalQuickEvents events={terminalData?.events} zones={terminalData?.zones} onActivity={()=>selectTab('activity')}/></aside></div></div>
 <div id="terminal-panel-activity" role="tabpanel" aria-labelledby="terminal-tab-activity" hidden={tab!=='activity'||kiosk}><div className="terminal-section-title"><div><span className="terminal-eyebrow">BITÁCORA DEL PUNTO DE CONTROL</span><h3>Actividad y presencia</h3><p>Consulta los movimientos autorizados para tu cuenta.</p></div><Activity size={26}/></div><TerminalOperations data={terminalData} zone={zone} api={api} onData={setTerminalData} onError={setError} view="history"/><TerminalPresence presence={presence} zones={terminalData?.zones} onCheckout={checkout} busy={processing}/></div>
 {terminalData?.can_configure&&<div id="terminal-panel-settings" role="tabpanel" aria-labelledby="terminal-tab-settings" hidden={tab!=='settings'||kiosk}><div className="terminal-section-title"><div><span className="terminal-eyebrow">ADMINISTRACIÓN DE LA TERMINAL</span><h3>Configuración de acceso</h3><p>Los ajustes se aplican en el servidor a todas las terminales.</p></div><KeyRound size={25}/></div><TerminalOperations data={terminalData} zone={zone} api={api} onData={setTerminalData} onError={setError} view="settings"/>{capacity&&<details className="terminal-policy"><summary>Administrar tarjetas y licencias de bóveda</summary><div className="v130-info"><p>Tarjetas RFID registradas: {capacity.used}. Cupo máximo de personas autorizadas en bóveda: {capacity.capacity}. Las demás zonas mantienen sus permisos; registrar otra tarjeta no concede acceso a bóveda.</p><label>Cupo de bóveda<input type="number" min="1" max="40" value={capacity.capacity} onChange={e=>setCapacity({...capacity,capacity:Number(e.target.value)})}/></label><button className="v130-btn" onClick={async()=>{try{setCapacity(await api('/api/access/settings',{body:{rfid_capacity:capacity.capacity}}));setError('');}catch(e){setError(e.message)}}}>Guardar cupo</button></div></details>}</div>}
 {kiosk&&<TerminalDecision event={last} zoneLabel={last?ZONE_LABEL(last.zone):''} large/>}<p className="terminal-footnote"><ShieldCheck size={14}/>Las decisiones se registran en la bitácora. Esta terminal no acciona una cerradura física.</p></div>;
}

function decodeQR(source,canvas,max=640){
 const width=source.videoWidth||source.width,height=source.videoHeight||source.height;if(!width||!height)return null;
 const ratio=Math.min(1,max/Math.max(width,height));canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);
 const context=canvas.getContext('2d',{willReadFrequently:true});context.drawImage(source,0,0,canvas.width,canvas.height);
 const pixels=context.getImageData(0,0,canvas.width,canvas.height);return jsQR(pixels.data,pixels.width,pixels.height,{inversionAttempts:'dontInvert'})?.data;
}
const CAMERA_PROFILES=[['smooth','Mayor fluidez · 640 px / hasta 24 fps'],['balanced','Equilibrado · 960 px / hasta 24 fps'],['detail','Más detalle · 1280 px / hasta 25 fps']];
function CameraCard({channel,chIndex,editable,live,onChange,onRemove,api,revision}){
 const[result,setResult]=useState(null),[testing,setTesting]=useState(false),[configuring,setConfiguring]=useState(!channel.id);
 useEffect(()=>{setResult(null)},[channel.url,channel.profile,revision]);
 useEffect(()=>{if(channel.id&&!channel._dirty)setConfiguring(false)},[channel.id,channel._dirty]);
 let parsed;try{parsed=new URL(channel.url)}catch{};
 const match=channel.url.match(/^(https?):\/\/([^/:]*)(?::([^/]*))?(\/.*)?$/),parts={scheme:match?.[1]||'http',host:match?.[2]||'',port:match?.[3]??(match?.[1]==='https'?'443':'80'),path:match?.[4]||'/video'};
 function edit(part,value){const pasted=['host','path'].includes(part)&&cameraAddressPaste(value);if(pasted){onChange({...channel,url:pasted,_dirty:true});return;}const next={...parts,[part]:value.trim()};onChange({...channel,url:next.scheme+'://'+next.host+':'+next.port+(next.path.startsWith('/')?'':'/')+next.path,_dirty:true});}
 async function test(){setTesting(true);setResult(null);try{const url=normalizeCameraAddress(channel.url);if(url!==channel.url)onChange({...channel,url,_dirty:true});setResult(await api('/api/cctv/test',{body:{url}}))}catch(e){setResult({ok:false,message:e.message})}finally{setTesting(false)}}
 return <section className="v130-cam"><div className="v130-camera-title"><span className={'v130-live-dot '+(live?.connected?'online':'')}/><strong>Canal {chIndex+1}</strong><span className="v130-muted">{channel._dirty?'Cambios sin guardar':live?.connected?'En directo':'Sin señal'}</span></div>
 {editable&&channel.id&&<button className="v130-btn" onClick={()=>setConfiguring(!configuring)}>{configuring?'Cerrar configuración':'Cambiar IP / configuración'}</button>}
 {!configuring&&<h3>{channel.name}</h3>}
 {editable&&configuring&&<><label>Nombre del canal<input value={channel.name} maxLength={60} onChange={e=>onChange({...channel,name:e.target.value,_dirty:true})}/></label><div className="v130-row wrap"><label>IP del teléfono<input inputMode="decimal" placeholder="192.168.1.50" value={parts.host} onChange={e=>edit('host',e.target.value)}/></label><label>Puerto<input inputMode="numeric" value={parts.port} onChange={e=>edit('port',e.target.value)}/></label></div>
 <label>Ruta del vídeo<input value={parts.path} placeholder="/video" onChange={e=>edit('path',e.target.value)}/></label><small className="v130-muted">Aquí va solo la ruta, por ejemplo /video. Si pegas la dirección MJPEG completa, se separarán automáticamente la IP, el puerto y la ruta.</small>
 <div className="v130-row wrap"><button className="v130-btn" onClick={()=>onChange({...channel,url:'http://'+(parsed?.hostname||'192.168.1.50')+':8080/video',_dirty:true})}>Ejemplo Android</button><button className="v130-btn" onClick={()=>onChange({...channel,url:'http://'+(parsed?.hostname||'192.168.1.50')+':8081/video',_dirty:true})}>Ejemplo iPhone / iPad</button></div>
 <small className="v130-muted">Son ejemplos editables. Usa el puerto y la ruta HTTP MJPEG/JPEG que muestra tu versión de la aplicación.</small>
 <details><summary>Dirección completa / ajustes avanzados</summary><label>URL local de cámara<input value={channel.url} onChange={e=>onChange({...channel,url:e.target.value,_dirty:true})}/></label></details>
 <label>Calidad y fluidez<select value={channel.profile||'balanced'} onChange={e=>onChange({...channel,profile:e.target.value,_dirty:true})}>{CAMERA_PROFILES.map(([id,text])=><option key={id} value={id}>{text}</option>)}</select></label>
 <div className="v130-row wrap"><button className="v130-btn" disabled={testing} onClick={test}>{testing?'Probando conexión…':'Probar conexión'}</button>{!channel.id&&<button className="v130-btn" onClick={onRemove}>Descartar canal</button>}</div>{result&&<p role="status" className={result.ok?'v130-connection-ok':'v130-connection-error'}>{result.message}{result.ok&&' · '+result.connect_ms+' ms al conectar'}</p>}</>}
 <small className="v130-muted">Guarda los ajustes y abre Vigilancia para ver este canal.</small>
 </section>;
}
function CctvConfiguration({api}){
 const[channels,setChannels]=useState([]),[editable,setEditable]=useState(false),[events,setEvents]=useState([]),[error,setError]=useState(''),[notice,setNotice]=useState(''),[rev,setRev]=useState(0),[preview,setPreview]=useState(false),[live,setLive]=useState({}),[network,setNetwork]=useState(null),[saving,setSaving]=useState(false),[page,setPage]=useState(0),[maxChannels,setMaxChannels]=useState(8);const video=useRef(null),stream=useRef(null);
 useEffect(()=>{let active=true;api('/api/cctv/channels').then(r=>{if(!active)return;setChannels(r.channels);setMaxChannels(r.max_channels||8);setEditable(r.can_edit);if(r.can_edit)api('/api/cctv/network').then(v=>active&&setNetwork(v)).catch(()=>{});}).catch(e=>setError(e.message));let busy=false;async function poll(){if(busy)return;busy=true;try{const [e,c]=await Promise.all([api('/api/access/events?limit=12'),api('/api/cctv/channels')]);if(active){setEvents(e.events);setLive(c.live);setChannels(current=>current.some(ch=>ch._dirty)?current:c.channels)}}catch(e){if(active)setError(e.message)}finally{busy=false}}poll();const id=setInterval(poll,2000);return()=>{active=false;clearInterval(id);stream.current?.getTracks().forEach(t=>t.stop())}},[api]);
 async function save(){setSaving(true);setNotice('');try{const normalized=channels.map(ch=>({...ch,url:normalizeCameraAddress(ch.url)}));const r=await api('/api/cctv/channels',{body:{channels:normalized}});setChannels(r.channels);setRev(v=>v+1);setError('');setNotice('Configuración guardada. Abre Vigilancia para ver los canales.');}catch(e){setError(e.message)}finally{setSaving(false)}}
 return <div className="v130-cctv"><article className="v130-panel"><div className="v130-panel-head"><Video/><h2>Centro de Monitoreo CCTV</h2><span className="v130-chip">Hasta {maxChannels} cámaras</span></div>
 <p className="v130-muted">Fecha y hora de Ciudad de México sobre cada vista. Los indicadores cambian si se pierde la señal. Sin grabación de vídeo.</p><CameraInventory api={api} refreshKey={rev} onRemoved={ch=>{if(ch.kind==='ip'){setChannels(current=>current.filter(item=>item.id!==ch.id));setPage(0)}setNotice('Cámara eliminada. Ya puedes agregar otra.');setRev(value=>value+1)}}/><BrowserCameras api={api} managementOnly refreshKey={rev}/>{editable&&<CameraDestinations api={api}/>}<details className="ip-camera-section"><summary>Cámaras con IP Camera Lite / dirección local</summary>
 {editable&&<div className="v130-camera-guide"><h3>Conectar tu teléfono en tres pasos</h3><ol><li>Conecta la laptop y el teléfono a una red que permita comunicación entre dispositivos. Activa el servidor HTTP en IP Camera Lite y el permiso de red local en iPhone/iPad.</li><li>Copia aquí la IP, el puerto y la ruta del vídeo que muestra la aplicación. Pulsa <strong>Probar conexión</strong>.</li><li>Elige un perfil y pulsa <strong>Guardar canales</strong>. Al cambiar de lugar, actualiza la IP del canal y vuelve a guardar.</li></ol><p>Para comenzar con poco retraso: configura el teléfono a 640 × 480 o 720p y 24–30 fps si el dispositivo lo permite. Usa «Mayor fluidez» si tu Wi-Fi es lento. Bajar la calidad aquí aligera la salida; el teléfono también debe reducir su transmisión de origen.</p>{network&&<small>Laptop servidor: {network.server_addresses.join(' / ')||'sin dirección local detectada'}. Una red universitaria puede aislar equipos; el túnel público no elimina ese aislamiento.</small>}</div>}
 {error&&<p role="alert">{error}</p>}{notice&&<p role="status">{notice}</p>}
 {!channels.length&&<div className="v130-camera-empty"><Camera size={36}/><h3>Tu monitoreo comienza aquí</h3><p>Añade un teléfono como cámara. Su dirección local se guarda en este servidor.</p></div>}
 <div className="v130-row wrap"><button className="v130-btn" disabled={page===0} onClick={()=>setPage(p=>p-1)}>Cámaras anteriores</button><span>Grupo {page+1} de {Math.max(1,Math.ceil(channels.length/4))} · hasta 4 vistas a la vez</span><button className="v130-btn" disabled={(page+1)*4>=channels.length} onClick={()=>setPage(p=>p+1)}>Siguientes cámaras</button></div><div className="v130-cctv-grid">{channels.slice(page*4,page*4+4).map((ch,localIndex)=>{const i=page*4+localIndex;return <CameraCard key={i} channel={ch} chIndex={i} editable={editable} live={live[String(ch.id)]} api={api} revision={rev} onChange={next=>{setNotice('');setChannels(v=>v.map((x,j)=>j===i?next:x))}} onRemove={()=>{setChannels(v=>v.filter((x,j)=>j!==i));setPage(p=>Math.min(p,Math.max(0,Math.ceil((channels.length-1)/4)-1)))}}/>})}</div>
 {editable&&<div className="v130-row wrap"><button className="v130-btn" disabled={channels.length>=maxChannels||saving} onClick={()=>{setPage(Math.floor(channels.length/4));setChannels(v=>[...v,{name:'Canal '+(v.length+1),url:'http://192.168.1.50:8080/video',profile:'smooth',_dirty:true}])}}>Agregar canal</button><button className="v130-btn primary" disabled={saving} onClick={save}>{saving?'Guardando…':'Guardar canales'}</button></div>}
 <details className="v130-local-camera"><summary>Cámara local de este dispositivo</summary><p>Esta prueba usa la cámara del equipo que abre la página. No configura ni comparte un teléfono como canal IP.</p><video hidden={!preview} ref={video} className="v130-video" muted playsInline/><button className="v130-btn" onClick={async()=>{if(preview){stream.current?.getTracks().forEach(t=>t.stop());setPreview(false);return}try{stream.current=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:640},height:{ideal:480}}});video.current.srcObject=stream.current;await video.current.play();setPreview(true)}catch(e){setError('No se pudo abrir la cámara local. Comprueba el permiso del navegador.')}}}>{preview?'Apagar prueba local':'Probar cámara local de este dispositivo'}</button></details></details></article>
 <article className="v130-panel"><h3>Últimos Check-In / Check-Out</h3>{!events.length&&<p className="v130-muted">Los movimientos aparecerán aquí.</p>}{events.map(e=><p key={e.id}><strong>{e.verdict==='VERIFIED'?'Verificado':'Denegado'}</strong> · {e.subject_name} · {ZONE_LABEL(e.zone)} · {e.direction==='CHECK_IN'?'Entrada':'Salida'} · {humanTime(e.created_at)}</p>)}</article></div>;
}

/* ------------------------------------------------------------------ */
/* Zonas y utilidades compartidas                                      */
/* ------------------------------------------------------------------ */
export const ZONES = [
  { id: "DATA_CENTER_VAULT", label: "Bóveda Principal Data Center" },
  { id: "SERVER_ROOM", label: "Sala de Servidores Críticos" },
  { id: "MONITORING_CCTV", label: "Centro de Monitoreo CCTV" },
  { id: "GENERAL_ACCESS", label: "Acceso General" },
];

const ZONE_LABEL = (id) => (ZONES.find((z) => z.id === id) || {}).label || id;

async function downloadBase64Png(b64, filename) {
  const a = document.createElement("a");
  a.href = "data:image/png;base64," + b64;
  a.download = filename || "credencial.png";
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function base64ToFile(b64, filename) {
  const bytes = atob(b64);
  const arr = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) arr[i] = bytes.charCodeAt(i);
  return new File([arr], filename, { type: "image/png" });
}

/* ====================================================================
 * MÓDULO 1 · Términos y Condiciones
 * ==================================================================*/
export function TermsModal({ title, body, version, onAccept, busy, compact }) {
  const [consent,setConsent]=useState(false);
  if (!body) return null;
  return (
    <div className={"v130-overlay" + (compact ? " compact" : "")}>
      <div className="v130-modal">
        <div className="v130-modal-head">
          <ShieldCheck size={22} />
          <h3>{title || "Términos y Condiciones"}</h3>
          <span className="v130-chip">{version}</span>
        </div>
        <div className="v130-modal-body">
          <p className="v130-muted">{body.intro}</p>
          {body.puntos.map(([t, d]) => (
            <div className="v130-term" key={t}>
              <CheckCircle2 size={18} />
              <div><strong>{t}</strong><p>{d}</p></div>
            </div>
          ))}
          <p className="v130-muted v130-small">{body.footer}</p>
        </div>
        <div className="v130-modal-foot"><label className="v130-check"><input type="checkbox" checked={consent} onChange={e=>setConsent(e.target.checked)}/>He leído y acepto las condiciones y el aviso de privacidad.</label>
          <button className="v130-btn primary" disabled={busy||!consent} onClick={onAccept}>
            <ShieldCheck size={16} /> Acepto Términos y Activar mi Gafete
          </button>
        </div>
      </div>
    </div>
  );
}

export function TermsStatusChip({ accepted, acceptedAt }) {
  return accepted ? (
    <span className="v130-chip ok"><CheckCircle2 size={14} /> Firmado {acceptedAt ? "· " + acceptedAt : ""}</span>
  ) : (
    <span className="v130-chip warn"><AlertTriangle size={14} /> Pendiente</span>
  );
}

/* ====================================================================
 * MÓDULO 2 · Gafete QR (usuario) + compartir/descargar
 * ==================================================================*/
export function useTerminalSound() {
  const ctxRef = useRef(null);
  const [enabled, setEnabled] = useState(false);
  const enabledRef = useRef(false);
  useEffect(() => { enabledRef.current = enabled; }, [enabled]);

  const ensure = useCallback(() => {
    if (!ctxRef.current) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) ctxRef.current = new AC();
    }
    return ctxRef.current;
  }, []);

  const beep = useCallback((freqs, dur = 0.14, gap = 0.06) => {
    if (!enabledRef.current) return;
    const ac = ensure(); if (!ac) return;
    let t = ac.currentTime;
    freqs.forEach((f) => {
      const osc = ac.createOscillator(); const gain = ac.createGain();
      osc.type = "sine"; osc.frequency.value = f;
      gain.gain.setValueAtTime(0.0001, t);
      gain.gain.exponentialRampToValueAtTime(0.25, t + 0.02);
      gain.gain.exponentialRampToValueAtTime(0.0001, t + dur);
      osc.connect(gain); gain.connect(ac.destination);
      osc.start(t); osc.stop(t + dur + 0.02);
      t += dur + gap;
    });
  }, [ensure]);

  const playGranted = useCallback(() => beep([880, 1320]), [beep]);
  const playDenied = useCallback(() => beep([220, 165], 0.2, 0.08), [beep]);

  // Identidad estable: evita re-disparar el intervalo de polling en cada render.
  const toggle=useCallback((value)=>{const ac=ensure();if(value)ac?.resume();setEnabled(value);},[ensure]);
  useEffect(()=>()=>{ctxRef.current?.close();},[]);
  return useMemo(() => ({ enabled, setEnabled:toggle, playGranted, playDenied }),
                   [enabled, playGranted, playDenied]);
}

/* ====================================================================
 * MÓDULO 3 · Terminal de Acceso (kiosco + escáner móvil)
 * ==================================================================*/
export function LicensesPanel({ api, matricula, toast, readonly=false }) {
  const [lics, setLics] = useState([]);
  const [mine, setMine] = useState([]);
  const load = useCallback(async () => {
    try {
      const r = await api("/api/licenses"); setLics(r.licenses || []);
      if (matricula) { const m = await api("/api/users/licenses?matricula=" + encodeURIComponent(matricula)); setMine(m.licenses || []); }
    } catch (e) { /* noop */ }
  }, [api, matricula]);
  useEffect(() => { load(); }, [load]);
  const held = new Set(mine.map((m) => m.license_id));

  const toggle = async (license_id) => {
    const body = { matricula, license_id };
    try {
      if (held.has(license_id)) await api("/api/users/revoke-license", { method: "POST", body });
      else await api("/api/users/assign-license", { method: "POST", body });
      load();
    } catch (e) { toast && toast("No se pudo completar (¿cupo agotado?)", "error"); }
  };

  return (
    <div className="v130-panel">
      <div className="v130-panel-head"><KeyRound size={18} /><h3>Catálogo Académico de Licencias Internas</h3></div>
      <p className="v130-muted v130-small">
        Simulación de aprovisionamiento (no son suscripciones reales de Microsoft 365).
      </p>
      {lics.map((l) => {
        const pct = Math.round((l.used / l.seats) * 100);
        return (
          <div className="v130-license" key={l.license_id}>
            <div className="v130-license-info">
              <strong>{l.name}</strong>
              <span className="v130-muted v130-small">{l.license_id} · {l.used}/{l.seats} cupos</span>
              <div className="v130-bar"><div className={"pct-"+Math.max(0,Math.min(100,pct))} /></div>
            </div>
            {matricula && !readonly && (
              <button className={"v130-btn mini " + (held.has(l.license_id) ? "danger" : "")}
                      disabled={!held.has(l.license_id) && l.free === 0}
                      onClick={() => toggle(l.license_id)}>
                {held.has(l.license_id) ? <><XCircle size={14} /> Revocar</> : <><CheckCircle2 size={14} /> Asignar</>}
              </button>
            )}
          </div>
        );
      })}
    </div>
  );
}

/* ====================================================================
 * MÓDULO 6 · Análisis de Amenazas
 * ==================================================================*/
export function ThreatAnalysisPanel({ api }) {
  const [data, setData] = useState(null);
  const load = useCallback(async () => {
    try { const r = await api("/api/threats"); setData(r); } catch (e) { setData({ error:e.message,findings: [] }); }
  }, [api]);
  useEffect(() => { load(); }, [load]);
  const color = { Alta: "bad", Media: "warn", Baja: "muted" };

  return (
    <div className="v130-panel">
      <div className="v130-panel-head"><AlertTriangle size={18} /><h3>Análisis de Amenazas</h3>
        <button className="v130-btn mini" onClick={load}><RefreshCw size={14} /> Reanalizar</button>
      </div>
      {!data && <p className="v130-muted">Analizando…</p>}
      {data?.error&&<p role="alert">{data.error}</p>}{data && !data.error && data.findings.length === 0 && <p className="v130-muted">Sin hallazgos relevantes. ✅</p>}
      {data && data.findings.map((h) => (
        <div className={"v130-finding " + color[h.severity]} key={h.code}>
          <div className="v130-finding-head">
            <span className={"v130-chip " + color[h.severity]}>{h.severity}</span>
            <strong>{h.code} · {h.title}</strong>
            <span className="v130-muted v130-small">{h.count} dato(s)</span>
          </div>
          <p><b>Evidencia:</b> {h.evidence}</p>
          <p><b>Recomendación:</b> {h.recommendation}</p>
          <p className="v130-muted v130-small"><b>Falsos positivos:</b> {h.false_positive_note}</p>
        </div>
      ))}
    </div>
  );
}

/* ====================================================================
 * MÓDULO 7 · Centro de Monitoreo CCTV
 * ==================================================================*/

export function CctvPanel({api}){
 const[tab,setTab]=useState('watch'),[editable,setEditable]=useState(false);
 useEffect(()=>{let alive=true;api('/api/cctv/channels').then(r=>{if(alive){setEditable(r.can_edit);if(!r.can_edit)setTab('watch')}}).catch(()=>{});return()=>{alive=false}},[api]);
 return <div><div className="surveillance-tabs" role="tablist" aria-label="Modo de CCTV"><button role="tab" aria-selected={tab==='watch'} onClick={()=>setTab('watch')}>Vigilancia</button>{editable&&<button role="tab" aria-selected={tab==='settings'} onClick={()=>setTab('settings')}>Configurar cámaras</button>}</div>{tab==='watch'?<SurveillanceCenter api={api}/>:<CctvConfiguration api={api}/>}</div>
}
