import React,{useEffect,useRef} from 'react';
import {createPortal} from 'react-dom';
import {ShieldCheck,ShieldX,ArrowRight,ScanLine} from 'lucide-react';

// Permite seguir usando el lector tipo teclado mientras el aviso ocupa la pantalla.
export function AccessFeedback({event,zoneLabel,onClose,onScan}){
 const next=useRef(null),actions=useRef({onClose,onScan});actions.current={onClose,onScan};
 useEffect(()=>{
  const previousOverflow=document.body.style.overflow;document.body.style.overflow='hidden';
  next.current?.focus({preventScroll:true});let buffer='',lastKey=0;
  const timeout=setTimeout(()=>actions.current.onClose(),4000);
  function keydown(e){
   if(e.ctrlKey||e.metaKey||e.altKey||e.isComposing)return;
   if(e.key==='Escape'){e.preventDefault();actions.current.onClose();return}
   if(e.key==='Tab'){e.preventDefault();next.current?.focus();return}
   if(e.key==='Enter'){
    e.preventDefault();e.stopPropagation();
    const value=Date.now()-lastKey<1000?buffer:'';buffer='';
    if(value)actions.current.onScan(value);else actions.current.onClose();return;
   }
   if(e.key.length===1&&/^[0-9a-fA-F:-]$/.test(e.key)){
    e.preventDefault();e.stopPropagation();if(Date.now()-lastKey>1000)buffer='';lastKey=Date.now();
    buffer=(buffer+e.key).slice(-32);
   }
  }
  window.addEventListener('keydown',keydown,true);
  return()=>{clearTimeout(timeout);window.removeEventListener('keydown',keydown,true);document.body.style.overflow=previousOverflow};
 },[event.id]);
 const granted=event.verdict==='VERIFIED',Icon=granted?ShieldCheck:ShieldX;
 return createPortal(<div className={'access-feedback '+(granted?'granted':'denied')} role="dialog" aria-modal="true" aria-label="Resultado de acceso" aria-describedby="access-feedback-description">
  <header><span>SECURITY TEAM · CONTROL DE ACCESO</span><span>{event.method==='RFID_125KHZ'?'TARJETA RFID':'GAFETE QR'}</span></header>
  <div className="access-feedback-content" aria-live="assertive" aria-atomic="true">
   <div className="access-feedback-icon"><Icon size={72} strokeWidth={1.5}/></div>
   <p className="access-feedback-eyebrow">{granted?(event.direction==='CHECK_OUT'?'SALIDA REGISTRADA':'ENTRADA REGISTRADA'):'CREDENCIAL NO AUTORIZADA'}</p>
   <h2 id="access-feedback-title">{granted?'Acceso permitido':'Acceso denegado'}</h2>
   <h3>{event.subject_name}</h3><p className="access-feedback-identity">{event.subject_id}</p>
   <div className="access-feedback-details"><span>{zoneLabel}</span><time dateTime={event.created_at}>{new Date(event.created_at).toLocaleString('es-MX',{timeZone:'America/Mexico_City',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit',second:'2-digit'})} · CDMX</time></div>
   <p id="access-feedback-description">{event.reason||'Identidad y permisos comprobados.'}</p>
   <button ref={next} className="access-feedback-next" onClick={onClose}><ScanLine size={19}/>Siguiente lectura<ArrowRight size={19}/></button>
   <small>Se cierra en 4 segundos. Puedes pasar otra tarjeta ahora.</small>
  </div><footer><span>Decisión registrada en la bitácora</span><span>No acciona una cerradura física</span></footer>
 </div>,document.body);
}
