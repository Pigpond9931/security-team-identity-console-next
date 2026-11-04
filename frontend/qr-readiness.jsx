import React from 'react';
import {CheckCircle2, AlertTriangle} from 'lucide-react';

export function QrZoneReadiness({badge}) {
  const entries = badge.access_requirements || badge.zones.map((zone,index)=>({zone,label:badge.zones_labels[index],ready:null}));
  return <div className="qr-live-zones"><dt>Zonas asignadas</dt><dd>
    {entries.map(entry=><span key={entry.zone} className={entry.ready===false?'zone-pending':''}>
      {entry.ready===false?<AlertTriangle size={14}/>:<CheckCircle2 size={14}/>}<span>{entry.label}
      {entry.ready===false&&<small>Habilitación interna pendiente</small>}</span>
    </span>)}
    <p className="qr-readiness-note">La zona y su habilitación interna deben estar asignadas. La terminal comprueba también vigencia, estado de cuenta y aforo en cada lectura.</p>
  </dd></div>;
}

export function QrExpiry({badge}) {
  return <small>{badge.expires_at?'Vigente hasta '+new Date(badge.expires_at*1000).toLocaleString('es-MX',{
    timeZone:'America/Mexico_City',day:'2-digit',month:'short',hour:'2-digit',minute:'2-digit'})+' · Ciudad de México':badge.valid_hint}</small>;
}
