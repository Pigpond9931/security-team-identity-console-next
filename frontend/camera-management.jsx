import React,{useEffect,useRef,useState} from 'react';
import {createPortal} from 'react-dom';
import {Camera,RefreshCw,Smartphone,Trash2} from 'lucide-react';
import './camera-management.css';

export async function removeCamera(api,ch){
 if(ch.kind==='web')return api('/api/browser-camera/revoke',{body:{id:ch.id}});
 return api('/api/cctv/remove',{body:{id:ch.id,expected:{name:ch.name,url:ch.url,profile:ch.profile,updated_at:ch.updated_at}}});
}

function RemovalDialog({ch,busy,error,onCancel,onConfirm}){
 const dialog=useRef(null),cancel=useRef(null);
 useEffect(()=>{cancel.current?.focus({preventScroll:true});const overflow=document.body.style.overflow;document.body.style.overflow='hidden';return()=>{document.body.style.overflow=overflow}},[]);
 function key(e){
  if(e.key==='Escape'){e.preventDefault();e.stopPropagation();if(!busy)onCancel()}
  if(e.key==='Tab'){const items=[...dialog.current.querySelectorAll('button:not(:disabled)')];if(!items.length){e.preventDefault();return}const first=items[0],last=items.at(-1);if(e.shiftKey&&document.activeElement===first){e.preventDefault();last.focus()}else if(!e.shiftKey&&document.activeElement===last){e.preventDefault();first.focus()}}
 }
 return createPortal(<div className="camera-removal-overlay"><div ref={dialog} className="camera-removal-dialog" role="alertdialog" aria-modal="true" aria-labelledby="camera-removal-title" aria-describedby="camera-removal-description" onKeyDown={key} aria-busy={busy}><div className="camera-removal-icon"><Trash2 size={25}/></div><span className="camera-management-eyebrow">ADMINISTRACIÓN CCTV</span><h2 id="camera-removal-title">¿Eliminar esta cámara?</h2><strong className="camera-removal-name">{ch.name}</strong><p id="camera-removal-description">Se quitará de CCTV y se liberará un espacio para otra cámara. Si está transmitiendo, dejará de verse en la consola.</p>{error&&<p role="alert" className="camera-management-error">{error}</p>}<footer><button ref={cancel} className="v130-btn" disabled={busy} onClick={onCancel}>Cancelar</button><button className="v130-btn camera-remove-button" disabled={busy} onClick={onConfirm}><Trash2 size={16}/>{busy?'Eliminando…':'Eliminar cámara'}</button></footer></div></div>,document.fullscreenElement||document.body);
}

export function useCameraRemoval(api,onRemoved){
 const[pending,setPending]=useState(null),[busy,setBusy]=useState(false),[error,setError]=useState('');const previous=useRef(null),callback=useRef(onRemoved);callback.current=onRemoved;
 function close(){setPending(null);setError('');requestAnimationFrame(()=>{const target=previous.current?.isConnected?previous.current:document.querySelector('[data-camera-inventory-title]');target?.focus({preventScroll:true})})}
 async function confirm(){if(busy||!pending)return;setBusy(true);setError('');try{await removeCamera(api,pending);const removed=pending;close();callback.current?.(removed)}catch(e){setError(e.message)}finally{setBusy(false)}}
 return {request(ch){previous.current=document.activeElement;setError('');setPending(ch)},dialog:pending?<RemovalDialog ch={pending} busy={busy} error={error} onCancel={close} onConfirm={confirm}/>:null};
}

export function CameraInventory({api,refreshKey,onRemoved}){
 const[channels,setChannels]=useState([]),[capacity,setCapacity]=useState(null),[canEdit,setCanEdit]=useState(false),[error,setError]=useState(''),[notice,setNotice]=useState(''),[loading,setLoading]=useState(true);const request=useRef(0),alive=useRef(true),inFlight=useRef(false);
 async function load(){if(inFlight.current)return;inFlight.current=true;const sequence=++request.current;try{const [ip,web]=await Promise.all([api('/api/cctv/channels'),api('/api/browser-camera/list',{body:{}})]);if(!alive.current||sequence!==request.current)return;setChannels([...web.channels.map(ch=>({...ch,key:'web:'+ch.id,kind:'web'})),...ip.channels.map(ch=>({...ch,key:'ip:'+ch.id,kind:'ip',can_manage:ip.can_edit,connected:ip.live?.[String(ch.id)]?.connected}))]);setCapacity({total:web.total_channels,max:web.max_channels,free:web.available_slots});setCanEdit(web.can_edit);setError('')}catch(e){if(alive.current&&sequence===request.current){setError(e.message);if(e.status===401||e.status===403){setChannels([]);setCanEdit(false)}}}finally{inFlight.current=false;if(alive.current&&sequence===request.current)setLoading(false)}}
 useEffect(()=>{alive.current=true;load();const t=setInterval(load,2000);return()=>{alive.current=false;request.current++;clearInterval(t)}},[api,refreshKey]);
 const removal=useCameraRemoval(api,ch=>{request.current++;setCapacity(v=>v?{...v,total:Math.max(0,v.total-1),free:Math.min(v.max,v.free+1)}:v);setChannels(v=>v.filter(c=>c.key!==ch.key));setNotice('Cámara «'+ch.name+'» eliminada. Ya puedes agregar otra.');load();onRemoved?.(ch)});
 return <section className="camera-inventory" aria-label="Lista de cámaras"><header><div><span className="camera-management-eyebrow">CANALES REGISTRADOS</span><h3 tabIndex={-1} data-camera-inventory-title>Lista de cámaras</h3><p>Elimina los canales que ya no uses para vincular otros dispositivos.</p></div><button type="button" className="v130-btn" onClick={load}><RefreshCw size={15}/>Actualizar lista</button></header>{capacity&&<div className="camera-capacity" role="status"><strong>{capacity.total} / {capacity.max} cámaras</strong><span>{capacity.free===0?'Sin espacios disponibles':capacity.free+' espacio'+(capacity.free===1?'':'s')+' disponible'+(capacity.free===1?'':'s')}</span></div>}{error&&<p className="camera-management-error" role="alert">{error}</p>}{notice&&<p className="camera-management-notice" role="status">{notice}</p>}{loading?<p>Cargando cámaras…</p>:!channels.length?<div className="camera-inventory-empty"><Camera size={26}/><p>No hay cámaras registradas. Puedes vincular una nueva.</p></div>:<div className="camera-inventory-list">{channels.map(ch=><article className="camera-inventory-row" key={ch.key}><div className="camera-inventory-type">{ch.kind==='web'?<Smartphone size={21}/>:<Camera size={21}/>}</div><div className="camera-inventory-details"><h4>{ch.name}</h4><small>{ch.kind==='web'?'Navegador · '+ch.zone_label:'Cámara IP'}</small><span className={'camera-inventory-status '+(ch.connected?'connected':'')}>{ch.connected?'Con señal':ch.kind==='ip'?'Se conecta al abrir':ch.status==='waiting'?'Esperando dispositivo':ch.status==='pending'?'Pendiente de confirmación':'Sin señal'}</span></div>{canEdit&&ch.can_manage&&<button type="button" className="v130-btn camera-remove-outline" aria-label={'Eliminar cámara '+ch.name} onClick={()=>removal.request(ch)}><Trash2 size={16}/>Eliminar cámara</button>}</article>)}</div>}{removal.dialog}</section>
}
