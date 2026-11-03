"""Vínculos efímeros: un teléfono lee QR sin heredar la sesión administrativa."""
import hashlib,secrets,threading,time
import db_manager as db
import security as sec
import features as f

LOCK=threading.RLock()
LINKS={}
MAX_LINKS=200
PRIVATE={'/api/scanner/create','/api/scanner/status','/api/scanner/approve','/api/scanner/configure','/api/scanner/revoke'}
PUBLIC={'/api/scanner/claim','/api/scanner/poll','/api/scanner/read','/api/scanner/disconnect'}

def digest(value):
    if not isinstance(value,str) or not 20<=len(value)<=160:raise ValueError('Vínculo no válido. Genera otro QR en la laptop.')
    return hashlib.sha256(value.encode()).hexdigest()

def _operator(c,link,owner_alive):
    if time.time()>=link['expires'] or not owner_alive(link['sid'],link['auth']):
        raise PermissionError('El vínculo terminó. Inicia sesión en la laptop y vuelve a vincular.')
    user=f.actor(c,link['auth']);f.terminal(c,user)
    if link['zone'] not in f.operator_zones(user):raise PermissionError('El operador perdió permiso para esta puerta.')
    return user

def _summary(link):
    return {'id':link['id'],'status':link['status'],'zone':link['zone'],'zone_label':db.ZONES[link['zone']],
        'direction':link['direction'],'phone_name':link.get('phone_name',''),'confirmation':link.get('confirmation',''),
        'expires_at':link['expires'],'seconds_left':max(0,int(link['expires']-time.time())),
        'connected':bool(link.get('seen') and time.time()-link['seen']<8),'last_result':link.get('last_result')}

def _configure(c,user,body,link):
    zone=body.get('zone');direction=body.get('direction')
    if zone not in f.operator_zones(user) or direction not in ('AUTO','CHECK_IN','CHECK_OUT'):
        raise PermissionError('Zona o acción fuera de tu alcance.')
    link.update(zone=zone,direction=direction)

def dispatch(path,body,sid,state,owner_alive):
    with LOCK:
        for key in [k for k,v in LINKS.items() if v['expires']<time.time()]:LINKS.pop(key,None)
        with sec.write_transaction() as c:
            if path in PRIVATE:
                if state.get('stage')!='dashboard':raise PermissionError('Completa primero el acceso en la laptop.')
                user=f.actor(c,state.get('auth'));f.terminal(c,user)
                if path.endswith('/create'):
                    if len(LINKS)>=MAX_LINKS:raise ValueError('Hay demasiados vínculos activos. Intenta más tarde.')
                    # Un vínculo por terminal/sesión; generar otro revoca el anterior.
                    for key in [k for k,v in LINKS.items() if v['sid']==sid]:LINKS.pop(key,None)
                    ticket=secrets.token_urlsafe(32);key=secrets.token_urlsafe(12)
                    link={'id':key,'sid':sid,'auth':dict(state['auth']),'ticket_hash':digest(ticket),'status':'waiting',
                          'expires':min(time.time()+300,state['created']+1800),'seen':0}
                    _configure(c,user,body,link);LINKS[key]=link
                    f.audit(c,user,'SCANNER_LINK_CREATED',details='Escáner QR limitado a '+link['zone'])
                    return {**_summary(link),'ticket':ticket}
                link=LINKS.get(str(body.get('id','')))
                if not link or link['sid']!=sid:raise PermissionError('Este vínculo no pertenece a tu terminal.')
                _operator(c,link,owner_alive)
                if path.endswith('/approve'):
                    if link['status']!='pending' or not secrets.compare_digest(str(body.get('confirmation','')),link['confirmation']):
                        raise ValueError('Compara el código del teléfono y vuelve a intentar.')
                    link.update(status='paired',expires=min(time.time()+1800,state['created']+1800))
                    f.audit(c,user,'SCANNER_LINK_APPROVED',details=link['phone_name']+'; '+link['zone'])
                elif path.endswith('/configure'):
                    _configure(c,user,body,link);f.audit(c,user,'SCANNER_LINK_CONFIGURED',details=link['zone'])
                elif path.endswith('/revoke'):
                    LINKS.pop(link['id'],None);f.audit(c,user,'SCANNER_LINK_REVOKED');return {'ok':True}
                return _summary(link)
            if path not in PUBLIC:raise ValueError('Ruta de escáner desconocida.')
            if path.endswith('/claim'):
                hashed=digest(body.get('ticket'))
                link=next((v for v in LINKS.values() if v.get('ticket_hash')==hashed and v['status']=='waiting'),None)
                if not link:raise PermissionError('Este QR ya se usó o venció. Genera otro en la laptop.')
                _operator(c,link,owner_alive)
                token=secrets.token_urlsafe(32)
                link.update(status='pending',phone_hash=digest(token),ticket_hash=None,seen=time.time(),
                            confirmation=str(secrets.randbelow(1000000)).zfill(6),
                            phone_name=str(body.get('name','Teléfono'))[:50])
                return {**_summary(link),'phone_token':token}
            hashed=digest(body.get('phone_token'))
            link=next((v for v in LINKS.values() if v.get('phone_hash')==hashed),None)
            if not link:raise PermissionError('El teléfono está desvinculado. Escanea un QR nuevo.')
            user=_operator(c,link,owner_alive);link['seen']=time.time()
            if path.endswith('/read'):
                if link['status']!='paired':raise PermissionError('Confirma primero el teléfono en la laptop.')
                ref=str(body.get('ref','')).strip()
                if not ref or len(ref)>2048:raise ValueError('QR no válido.')
                ref_hash=hashlib.sha256(ref.encode()).hexdigest()
                if link.get('last_hash')==ref_hash and time.time()-link.get('read_at',0)<3:
                    return {'result':None,'duplicate':True,'message':'Esta lectura ya se registró. Espera unos segundos antes de repetirla.'}
                if time.time()-link.get('read_at',0)<.5:raise f.Conflict('Espera un momento antes de leer otro gafete.')
                result=f.access(c,user,{'ref':ref,'method':'QR_BADGE','zone':link['zone'],'direction':link['direction']})
                f.audit(c,user,'SCANNER_QR_READ',result['subject_id'],link['phone_name']+'; '+link['zone'])
                link.update(last_hash=ref_hash,read_at=time.time(),last_result=result)
                return {'result':result,'duplicate':False}
            if path.endswith('/disconnect'):
                LINKS.pop(link['id'],None);f.audit(c,user,'SCANNER_LINK_REVOKED',details='Desconectado desde el teléfono');return {'ok':True}
            return _summary(link)
