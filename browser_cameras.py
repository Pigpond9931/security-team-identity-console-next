"""Cámaras efímeras: capacidades de publicación, señalización y último JPEG en RAM."""
import base64, hashlib, io, secrets, threading, time
from PIL import Image
import db_manager as db
import security as sec
import features as f

LOCK=threading.RLock()
FRAMES=threading.Condition(LOCK)
CHANNELS={}
PRIVATE={'/api/browser-camera/'+p for p in ('list','create','status','approve','revoke','view','viewer-poll','viewer-signal','leave','frame')}
PUBLIC={'/api/browser-camera/'+p for p in ('claim','poll','signal','upload','upload-frame','disconnect')}

def digest(token):
    if not isinstance(token,str) or not 20<=len(token)<=160:raise PermissionError('Vínculo de cámara inválido.')
    return hashlib.sha256(token.encode()).hexdigest()

def alive(ch,owner_alive,c):
    if ch['expires']<=time.time() or not owner_alive(ch['sid'],ch['auth']):raise PermissionError('La cámara se desvinculó o venció. Genera otro enlace en CCTV.')
    u=f.actor(c,ch['auth'])
    if not f.camera_admin(c,u):raise PermissionError('El propietario ya no puede publicar cámaras.')
    return u

def summary(ch):
    return {k:ch[k] for k in ('id','name','zone','zone_label','status','confirmation','expires')}|{'connected':bool(ch.get('publishing')) and time.time()-ch.get('seen',0)<8,'viewers':len(ch['peers']),'server_time':time.time(),'frame_age_ms':round((time.time()-ch['uploaded'])*1000) if ch['uploaded'] else None}

def collect(c,owner_alive):
    for key,ch in list(CHANNELS.items()):
        try:alive(ch,owner_alive,c)
        except PermissionError:CHANNELS.pop(key);continue
        for pid,p in list(ch['peers'].items()):
            if time.time()-p['seen']>20 or not owner_alive(p['sid'],p['auth']):ch['peers'].pop(pid)

def dispatch(path,body,sid,state,owner_alive):
    action=path.rsplit('/',1)[-1]
    with LOCK, sec.write_transaction() as c:
        collect(c,owner_alive)
        if path in PRIVATE:
            if state.get('stage')!='dashboard':raise PermissionError('Inicia sesión para acceder a CCTV.')
            u=f.actor(c,state.get('auth'))
            if not f.cctv(c,u):raise PermissionError('Sin permiso CCTV.')
            state['auth']['cctv_session']=True
            if action=='list':
                editing=f.camera_admin(c,u);total=len(CHANNELS)+c.execute('SELECT COUNT(*) FROM camera_channels').fetchone()[0]
                return {'channels':[summary(ch)|{'can_manage':editing,'can_pair':editing and ch['sid']==sid} for ch in CHANNELS.values()],
                    'can_edit':editing,'max_channels':8,'total_channels':total,'available_slots':max(0,8-total)}
            if action=='create':
                if not f.camera_admin(c,u):raise PermissionError('Se requiere administración de cámaras para vincular dispositivos.')
                if len(CHANNELS)+c.execute('SELECT COUNT(*) FROM camera_channels').fetchone()[0]>=8:raise ValueError('Ya hay ocho cámaras. Quita un canal antes de añadir otro.')
                name=str(body.get('name','Cámara móvil')).strip()[:60];zone=body.get('zone')
                if not name or zone not in db.ZONES:raise ValueError('Escribe un nombre y selecciona una zona.')
                ticket=secrets.token_urlsafe(32);key=secrets.token_urlsafe(12)
                ch={'id':key,'sid':sid,'auth':dict(state['auth']),'name':name,'zone':zone,'zone_label':db.ZONES[zone],
                    'status':'waiting','confirmation':'','ticket_hash':digest(ticket),'expires':min(time.time()+300,sec.session_deadline(state['auth'])),
                    'peers':{},'frame':None,'seq':0,'uploaded':0}
                CHANNELS[key]=ch;f.audit(c,u,'CCTV_BROWSER_CREATED',details=name+'; '+zone)
                return summary(ch)|{'ticket':ticket}
            ch=CHANNELS.get(str(body.get('id','')))
            if not ch:raise PermissionError('La cámara se desvinculó o venció.')
            if action=='revoke':
                if not f.camera_admin(c,u):raise PermissionError('Se requiere administración de cámaras para eliminar un canal.')
                CHANNELS.pop(ch['id']);ch['peers'].clear();ch.update(frame=None,frame_raw=None);FRAMES.notify_all()
                f.audit(c,u,'CCTV_BROWSER_REVOKED',details=ch['name']);return {'ok':True}
            if action in ('status','approve'):
                if ch['sid']!=sid or not f.camera_admin(c,u):raise PermissionError('Este vínculo pertenece a otra sesión.')
                if action=='approve':
                    if ch['status']!='pending' or not secrets.compare_digest(str(body.get('confirmation','')),ch['confirmation']):raise ValueError('Compara el código del teléfono antes de confirmar.')
                    ch.update(status='paired',expires=min(time.time()+sec.CCTV_SESSION_SECONDS,sec.session_deadline(state['auth'])));f.audit(c,u,'CCTV_BROWSER_APPROVED',details=ch['name'])
                return summary(ch)
            if ch['status']!='paired':raise PermissionError('Confirma primero la cámara.')
            if action=='view':
                if len(ch['peers'])>=4 or sum(len(v['peers']) for v in CHANNELS.values())>=16:raise ValueError('Límite de espectadores. Pausa otra vista de cámara.')
                pid=secrets.token_urlsafe(18);ch['peers'][pid]={'sid':sid,'auth':dict(state['auth']),'seen':time.time(),'to_phone':[],'to_viewer':[],'fallback':False,'offered':False,'answered':False,'nc':0,'pc':0,'frame_at':0}
                return {'peer':pid,**summary(ch)}
            peer=ch['peers'].get(str(body.get('peer','')))
            if not peer or peer['sid']!=sid or peer['auth']!=state['auth']:raise PermissionError('Vista caducada. Vuelve a abrir la cámara.')
            peer['seen']=time.time()
            if action=='leave':ch['peers'].pop(body['peer']);return {'ok':True}
            if action=='frame':
                peer['fallback']=True
                if time.time()-peer['frame_at']<.09:return {'seq':ch['seq']}
                peer['frame_at']=time.time()
                fresh=ch['frame'] if time.time()-ch['uploaded']<3 and body.get('seq')!=ch['seq'] else None
                if fresh is None and ch.get('frame_raw') and time.time()-ch['uploaded']<3 and body.get('seq')!=ch['seq']:fresh=base64.b64encode(ch['frame_raw']).decode()
                return {'seq':ch['seq'],'jpeg':fresh,'captured_at':ch['uploaded']}
            if action=='viewer-poll':
                msgs=peer['to_viewer'];peer['to_viewer']=[]
                return {'messages':msgs,**summary(ch)}
            target='to_phone';sender='viewer'
        else:
            if path not in PUBLIC:raise ValueError('Ruta de cámara desconocida.')
            if action=='claim':
                hashed=digest(body.get('ticket'));ch=next((v for v in CHANNELS.values() if v['status']=='waiting' and v['ticket_hash']==hashed),None)
                if not ch:raise PermissionError('QR usado o vencido. Genera otro vínculo en CCTV.')
                token=secrets.token_urlsafe(32);ch.update(status='pending',ticket_hash=None,phone_hash=digest(token),confirmation=str(secrets.randbelow(1000000)).zfill(6),seen=time.time())
                return summary(ch)|{'phone_token':token}
            hashed=digest(body.get('phone_token'));ch=next((v for v in CHANNELS.values() if v.get('phone_hash')==hashed),None)
            if not ch:raise PermissionError('La cámara se desvinculó o venció. Genera otro enlace en CCTV.')
            ch['seen']=time.time()
            if action=='disconnect':
                u=alive(ch,owner_alive,c);CHANNELS.pop(ch['id']);f.audit(c,u,'CCTV_BROWSER_REVOKED',details=ch['name']);return {'ok':True}
            if action=='poll':
                ch['publishing']=body.get('publishing') is True
                messages=[]
                for pid,p in ch['peers'].items():
                    messages.extend({'peer':pid,**m} for m in p['to_phone']);p['to_phone']=[]
                return summary(ch)|{'messages':messages,'peers':list(ch['peers']),'fallback':any(p['fallback'] for p in ch['peers'].values())}
            if ch['status']!='paired':raise PermissionError('Confirma la cámara en la consola.')
            if action in ('upload','upload-frame'):
                binary=action=='upload-frame';encoded=None
                if binary:
                    source=body.get('source_seq');raw=body.get('_raw_jpeg')
                    if type(source)!=int or not 0<source<2**53:raise ValueError('Secuencia inválida.')
                    if not isinstance(raw,bytes) or not 0<len(raw)<=195000:raise ValueError('Cuadro demasiado grande.')
                    # Dos envíos pueden viajar a la vez: nunca publicar un cuadro atrasado.
                    if source<=ch.get('source_seq',0):return {'ok':True,'accepted':False}
                    now=time.monotonic();budget=min(4,ch.get('upload_budget',4)+(now-ch.get('budget_at',now))*30)
                    ch.update(upload_budget=budget,budget_at=now)
                    if budget<1:return {'ok':True,'accepted':False}
                    ch['upload_budget']-=1
                else:
                    if time.time()-ch['uploaded']<.09:raise f.Conflict('Demasiados cuadros.')
                    encoded=body.get('jpeg','')
                    if not isinstance(encoded,str) or len(encoded)>260000:raise ValueError('Cuadro demasiado grande.')
                try:
                    if not binary:raw=base64.b64decode(encoded,validate=True)
                    with Image.open(io.BytesIO(raw)) as image:
                        if image.format!='JPEG' or max(image.size)>1280 or min(image.size)<16:raise ValueError()
                        image.verify()
                except Exception:raise ValueError('JPEG inválido.')
                ch.update(frame=encoded,frame_raw=raw,seq=ch['seq']+1,uploaded=time.time())
                if binary:ch['source_seq']=source
                FRAMES.notify_all()
                return {'ok':True,'accepted':True}
            peer=ch['peers'].get(str(body.get('peer','')))
            if not peer:raise f.Conflict('El espectador ya no está conectado.')
            target='to_viewer';sender='phone'
        # Solo señalización WebRTC; ningún token permite consultar datos de usuarios.
        msg=body.get('message');kind=msg.get('type') if isinstance(msg,dict) else None
        if kind in ('offer','answer'):
            flag='offered' if sender=='viewer' else 'answered'
            if kind!=('offer' if sender=='viewer' else 'answer') or peer[flag]:raise ValueError('Descripción WebRTC fuera de secuencia.')
            if not isinstance(msg.get('sdp'),str) or len(msg['sdp'])>32000:raise ValueError('Descripción WebRTC inválida.')
            peer[flag]=True
        elif kind=='candidate':
            count='nc' if sender=='viewer' else 'pc'
            if peer[count]>=40 or not isinstance(msg.get('candidate'),dict) or len(str(msg['candidate']))>2000:raise ValueError('Candidato WebRTC inválido.')
            peer[count]+=1
        else:raise ValueError('Señal WebRTC inválida.')
        if len(peer[target])>=48:raise ValueError('Cola de señalización completa.')
        clean={'type':kind,'sdp':msg['sdp']} if kind in ('offer','answer') else {'type':kind,'candidate':msg['candidate']}
        peer[target].append(clean);return {'ok':True}

def stream_open(body,sid,state,owner_alive):
    """Use the same session-bound peer and permission checks as WebRTC signaling."""
    dispatch('/api/browser-camera/frame',body,sid,state,owner_alive)

def stream_latest(body,previous,timeout=1):
    """One newest frame in RAM; no per-viewer frame queue or database wait."""
    with FRAMES:
        key=body['id'];pid=body['peer']
        FRAMES.wait_for(lambda:key not in CHANNELS or pid not in CHANNELS[key]['peers'] or CHANNELS[key]['seq']!=previous,timeout)
        ch=CHANNELS.get(key)
        if not ch or pid not in ch['peers']:raise PermissionError('Vista cerrada.')
        return ch['seq'],ch.get('frame_raw'),ch['uploaded']
