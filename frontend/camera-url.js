// Acepta pegar la dirección del teléfono en IP o ruta sin duplicar el origen.
export function cameraAddressPaste(value) {
  const text=String(value??'').trim().replace(/^\/+(?=https?:\/\/)/i,'');
  if(!/^https?:\/\//i.test(text))return null;
  try {const url=new URL(text);return ['http:','https:'].includes(url.protocol)?url.href:null;}catch{return null;}
}

export function normalizeCameraAddress(value) {
  const text=String(value??'').trim(),address=cameraAddressPaste(text);
  if(!address)return text;
  const outer=new URL(address),nested=cameraAddressPaste(outer.pathname+outer.search);
  // Repara el caso legado /http://misma-ip:puerto/video, conservando su origen.
  if(nested&&new URL(nested).origin===outer.origin)return nested;
  return address;
}
