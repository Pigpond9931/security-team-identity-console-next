"""Servicios v1.3: transacciones, permisos vigentes y capacidades con propósito."""
import base64
import hashlib
import hmac
import io
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import time
from datetime import datetime, timezone
from urllib.parse import urlsplit
import db_manager as db
import security as sec
import windows_store as store
import camera_hub

from terms_policy import TITLE as TERMS_TITLE, BODY as TERMS_BODY
ZONE_LICENSE={'DATA_CENTER_VAULT':'LIC-DC-VAULT','SERVER_ROOM':'LIC-SRV-CRIT','MONITORING_CCTV':'LIC-CCTV-MON'}

class Conflict(ValueError):pass

def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def row_user(c,username):
    u=c.execute('SELECT * FROM users WHERE username=?',(str(username),)).fetchone()
    if not u:raise ValueError('Cuenta no encontrada.')
    return u
def zones(u):
    try:return [z for z in json.loads(u['allowed_zones'] or '[]') if z in db.ZONES]
    except (ValueError,TypeError):return []
def accepted(u):return bool(u['terms_accepted'] and u['terms_version']==db.TERMS_VERSION)
def actor(c,session,terms=True):
    u=sec.session_user(c,session)
    if not u or (terms and not accepted(u)):raise PermissionError('Completa autenticación y términos.')
    return u
def global_admin(u):return u['role'] in db.GLOBAL_ROLES
def manager(c,u,username):
    target=row_user(c,username)
    if target['id']==u['id']:raise PermissionError('No puedes ampliar tus propios permisos.')
    if u['role']=='system_admin' or (u['role']=='dpo' and target['role']!='system_admin'):
        return target
    if u['role']=='area_admin' and u['area'] and u['area']==target['area'] and target['role']=='user':
        return target
    raise PermissionError('Cuenta fuera de tu alcance.')
def can_view(c,u,username):return row_user(c,username) if u['username']==username else manager(c,u,username)
def audit(c,u,action,target='',details=''):db.write_audit(c,u['username'] if hasattr(u,'keys') else u,action,details,target)
def terms_info(u):return {'accepted':accepted(u),'accepted_at':u['terms_accepted_at'],'version':u['terms_version']}
def accept(c,u,via):
    if not accepted(u):
        c.execute('UPDATE users SET terms_accepted=1,terms_accepted_at=?,terms_version=? WHERE id=?',(now(),db.TERMS_VERSION,u['id']))
        audit(c,u,'TERMS_ACCEPTED',u['username'],'version='+db.TERMS_VERSION+' via='+via)

def qr_key():
    p=Path(os.environ['ST_KEY_PATH']).parent/'.qr-key'
    with store.file_lock(p.parent/'.qr-key.lock',wait=True):
        if not p.exists():store.atomic_write(p,store.protect(secrets.token_bytes(32)))
        return store.unprotect(p.read_bytes())
def b64(v):return base64.urlsafe_b64encode(v).decode().rstrip('=')
def sign(data):
    value=b64(json.dumps(data,separators=(',',':'),sort_keys=True).encode())
    return 'ST3.'+value+'.'+b64(hmac.new(qr_key(),value.encode(),hashlib.sha256).digest())
def verify(token,purpose):
    try:
        if not isinstance(token,str) or len(token)>2048:raise ValueError()
        prefix,value,sig=token.split('.')
        expected=b64(hmac.new(qr_key(),value.encode(),hashlib.sha256).digest())
        if prefix!='ST3' or not hmac.compare_digest(sig,expected):raise ValueError()
        data=json.loads(base64.urlsafe_b64decode(value+'='*(-len(value)%4)))
        if data['purpose']!=purpose or data['exp']<=time.time() or data['tipo'] not in ('USER','VISITOR'):raise ValueError()
        return data
    except (ValueError,KeyError,TypeError,UnicodeError):raise ValueError('Pase inválido, revocado o expirado.') from None
def qr(token):return base64.b64encode(db.generate_qr_png(token)).decode()
def valid_subject(c,data):
    if data['tipo']=='USER':
        u=row_user(c,data['ref'])
        if not u['is_active'] or u['is_locked'] or not u['mfa_configured'] or u['must_change_password'] or data['sv']!=u['security_version']:raise ValueError('Cuenta bloqueada, inactiva o credencial revocada.')
        return u
    v=c.execute('SELECT * FROM visitors WHERE visitor_id=?',(data['ref'],)).fetchone()
    if not v or v['status']!='ACTIVE' or datetime.fromisoformat(v['valid_until']).timestamp()<=time.time():raise ValueError('Pase de invitado expirado o revocado.')
    return v
def badge(c,kind,subject):
    visitor=kind=='VISITOR'
    exp=int(datetime.fromisoformat(subject['valid_until']).timestamp()) if visitor else int(time.time()+8*3600)
    ref=subject['visitor_id'] if visitor else subject['username']
    zs=[subject['allowed_zone']] if visitor else zones(subject)
    signed={'purpose':'BADGE','tipo':kind,'ref':ref,'sv':0 if visitor else subject['security_version'],'exp':exp}
    terms=accepted(subject)
    requirements=[]
    for zone in zs:
        license_id=ZONE_LICENSE.get(zone) if not visitor else None
        ready=not license_id or bool(c.execute('SELECT 1 FROM user_licenses WHERE matricula=? AND license_id=?',(ref,license_id)).fetchone())
        requirements.append({'zone':zone,'label':db.ZONES[zone],'ready':ready})
    return {'tipo':kind,'matricula':ref,'full_name':subject['full_name'],'role':'VISITOR' if visitor else subject['role'],
        'area':subject['organization'] if visitor else subject['area'] or 'Administración global','zones':zs,
        'zones_labels':[db.ZONES[z] for z in zs],'access_requirements':requirements,'expires_at':exp,'terms_accepted':terms,'token':sign(signed) if terms else None,
        'valid_hint':'Válido hasta '+datetime.fromtimestamp(exp,timezone.utc).isoformat(timespec='minutes')}
def delivery(c,u,kind,subject):
    ref=subject['username'] if kind=='USER' else subject['visitor_id']
    c.execute('DELETE FROM mobile_passes WHERE subject_type=? AND subject_id=?',(kind,ref))
    c.execute("DELETE FROM pass_receipts WHERE subject_type=? AND subject_id=? AND status='pending'",(kind,ref))
    exp=min(time.time()+300,datetime.fromisoformat(subject['valid_until']).timestamp()) if kind=='VISITOR' else time.time()+300
    data={'purpose':'PASS','tipo':kind,'ref':ref,'sv':subject['security_version'] if kind=='USER' else 0,'exp':int(exp),'nonce':secrets.token_urlsafe(24)}
    token=sign(data)
    c.execute('INSERT INTO mobile_passes(token_hash,subject_type,subject_id,security_version,expires_at,created_at) VALUES(?,?,?,?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),kind,ref,data['sv'],exp,now()))
    audit(c,u,'MOBILE_PASS_CREATED',ref,'Entrega privada de un uso con caducidad de cinco minutos')
    return token
def public_pass(c,token,accept_terms=False):
    raise PermissionError('Usa el canje autenticado de entregas móviles.')

def pass_payload(c,data,accept_terms=False):
    subject=valid_subject(c,data)
    if accept_terms:
        if data['tipo']=='USER':accept(c,subject,'MOBILE_PASS');subject=row_user(c,data['ref'])
        elif not accepted(subject):
            c.execute('UPDATE visitors SET terms_accepted=1,terms_accepted_at=?,terms_version=? WHERE visitor_id=?',(now(),db.TERMS_VERSION,data['ref']))
            audit(c,data['ref'],'TERMS_ACCEPTED',data['ref'],'via=MOBILE_PASS version='+db.TERMS_VERSION)
            subject=c.execute('SELECT * FROM visitors WHERE visitor_id=?',(data['ref'],)).fetchone()
    b=badge(c,data['tipo'],subject)
    return {'badge':b,'terms':{'accepted':b['terms_accepted']},'qr_png_base64':qr(b['token']) if b['token'] else None,
            'terms_title':TERMS_TITLE,'terms_body':TERMS_BODY,'terms_version':db.TERMS_VERSION}

def catalog(c):
    return [dict(r) for r in c.execute('''SELECT l.*,COUNT(u.id) AS used,l.seats-COUNT(u.id) AS free FROM licenses_catalog l
        LEFT JOIN user_licenses u ON l.license_id=u.license_id GROUP BY l.license_id ORDER BY l.license_id''')]
def terminal(c,u):
    if not (global_admin(u) or u['role']=='area_admin' or u['is_guard']):raise PermissionError('Sin permiso de terminal.')
def camera_admin(c,u):
    return global_admin(u) or bool(c.execute("SELECT 1 FROM user_licenses WHERE matricula=? AND license_id='LIC-CCTV-ADMIN'",(u['username'],)).fetchone())

def cctv(c,u):
    return camera_admin(c,u) or u['is_guard'] or u['area']=='Monitoring' or bool(c.execute("SELECT 1 FROM user_licenses WHERE matricula=? AND license_id='LIC-CCTV-MON'",(u['username'],)).fetchone())
def operator_zones(u):return list(db.ZONES) if global_admin(u) or u['is_guard'] or u['area']=='Monitoring' else zones(u)
def scope_events(c,u,limit=100):
    zs=operator_zones(u);marks=','.join('?' for z in zs) or "''"
    return [dict(r) for r in c.execute(f'SELECT * FROM access_events WHERE zone IN ({marks}) ORDER BY id DESC LIMIT ?',(*zs,limit))]
def presence(c,u):
    zs=operator_zones(u);marks=','.join('?' for z in zs) or "''"
    return [dict(r) for r in c.execute(f'''SELECT e.* FROM access_events e WHERE verdict='VERIFIED' AND direction='CHECK_IN'
       AND zone IN ({marks}) AND NOT EXISTS(SELECT 1 FROM access_events n WHERE n.verdict='VERIFIED' AND n.subject_type=e.subject_type
       AND n.subject_id=e.subject_id AND n.zone=e.zone AND n.id>e.id) ORDER BY id DESC''',zs)]
def normalize_rfid(value):
    s=str(value).strip().upper()
    if re.fullmatch(r'\d{1,16}',s):return str(int(s))
    h=s.replace(':','').replace('-','').removeprefix('0X')
    if re.fullmatch(r'[0-9A-F]{2,16}',h):return str(int(h,16))
    raise ValueError('UID inválido: usa dígitos del lector o hexadecimal separado por dos puntos.')
def access(c,u,body):
    terminal(c,u)
    zone=body.get('zone');method=body.get('method');direction=body.get('direction','AUTO');ref=str(body.get('ref','')).strip()
    if zone not in operator_zones(u):raise PermissionError('No puedes operar esta puerta.')
    if method not in ('RFID_125KHZ','QR_BADGE') or direction not in ('AUTO','CHECK_IN','CHECK_OUT') or not ref or len(ref)>2048:raise ValueError('Lectura inválida.')
    kind='USER';sid='DESCONOCIDO';name='Credencial desconocida';role='';area='';reason='';subject=None
    try:
        if method=='RFID_125KHZ':
            value=normalize_rfid(ref)
            sid='RFID:'+value
            import rfid_cards
            found=rfid_cards.owners(c,value)
            if len(found)!=1:raise ValueError('UID RFID no registrado o ambiguo.')
            subject=found[0];sid=subject['username'];data={'tipo':'USER','ref':sid,'sv':subject['security_version']}
        else:
            data=verify(ref,'BADGE');kind=data['tipo'];sid=data['ref']
        subject=valid_subject(c,data)
        name=subject['full_name'];role='VISITOR' if kind=='VISITOR' else subject['role'];area=subject['organization'] if kind=='VISITOR' else subject['area'] or 'Administración global'
        if zone=='DATA_CENTER_VAULT' and kind!='USER' and c.execute("SELECT 1 FROM access_settings WHERE key='restricted_four_enabled' AND value='1'").fetchone():
            raise ValueError('Centro de datos reservado a titulares autorizados; no admite pases de invitado.')
        if kind=='USER':
            if not accepted(subject):raise ValueError('MFA o términos pendientes.')
            if zone not in zones(subject):raise ValueError('Sin permiso para esta zona.')
            lic=ZONE_LICENSE.get(zone)
            if lic and not c.execute('SELECT 1 FROM user_licenses WHERE matricula=? AND license_id=?',(sid,lic)).fetchone():raise ValueError('Licencia de zona pendiente o fuera de cupo.')
        else:
            if not accepted(subject):raise ValueError('Términos pendientes del invitado.')
            if zone!=subject['allowed_zone']:raise ValueError('Sin permiso para esta zona.')
        last=c.execute("SELECT * FROM access_events WHERE subject_type=? AND subject_id=? AND zone=? AND verdict='VERIFIED' ORDER BY id DESC LIMIT 1",(kind,sid,zone)).fetchone()
        inside=bool(last and last['direction']=='CHECK_IN')
        if direction=='AUTO':direction='CHECK_OUT' if inside else 'CHECK_IN'
        elif (direction=='CHECK_IN' and inside) or (direction=='CHECK_OUT' and not inside):raise ValueError('Movimiento duplicado o sin entrada previa.')
        if direction=='CHECK_IN':
            import access_terminal
            if access_terminal.full_for_entry(c,kind,sid):raise ValueError('Aforo lleno. Espera a que se registre una salida.')
    except ValueError as e:reason=str(e)
    direction='CHECK_IN' if direction=='AUTO' else direction
    verdict='DENIED' if reason else 'VERIFIED'
    event={'subject_type':kind,'subject_id':sid,'subject_name':name,'role_or_type':role,'zone':zone,'method':method,'direction':direction,'verdict':verdict,'reason':reason,'operator_matricula':u['username'],'created_at':now()}
    event['subject_area']=area
    cur=c.execute('INSERT INTO access_events('+','.join(event)+') VALUES('+','.join('?' for x in event)+')',tuple(event.values()))
    event.update(id=cur.lastrowid,event_id=cur.lastrowid,area=area)
    audit(c,u,'ACCESS_'+verdict,sid,json.dumps({'zone':zone,'method':method,'direction':direction,'reason':reason},ensure_ascii=False))
    return event

def camera_url(value):
    if not isinstance(value,str) or len(value)>2048:raise ValueError('Dirección de cámara inválida.')
    p=urlsplit(value)
    try:ip=ipaddress.ip_address(p.hostname or '')
    except ValueError:raise ValueError('Usa una IP local explícita para la cámara.') from None
    allowed=any(ip in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')) if ip.version==4 else False
    if not allowed or p.scheme not in ('http','https') or p.username or p.password or p.fragment or p.port not in (None,80,81,443,8080,8081,8000,8888,4747):raise ValueError('Cámara: solo IP privada, puerto de vídeo y URL sin credenciales.')
    return value

def threats(c,u):
    if u['role'] not in (*db.GLOBAL_ROLES,'area_admin'):raise PermissionError('Sin permiso de análisis.')
    users=[dict(x) for x in c.execute('SELECT * FROM users') if global_admin(u) or (x['area']==u['area'] and x['role']=='user')]
    ids={x['username'] for x in users};cut=(datetime.now(timezone.utc).timestamp()-86400)
    events=[e for e in scope_events(c,u,250) if datetime.fromisoformat(e['created_at']).timestamp()>=cut]
    logs=[]
    for a in c.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 1000'):
        if not global_admin(u) and a['actor'] not in ids and a['target'] not in ids:continue
        dt=datetime.fromisoformat(a['timestamp']);dt=dt.replace(tzinfo=datetime.now().astimezone().tzinfo) if dt.tzinfo is None else dt
        if dt.timestamp()>=cut:logs.append(dict(a))
    groups=[('TH-01','Alta','Bloqueos y fallos repetidos',[{'matricula':x['username'],'fallos':x['failed_attempts']} for x in users if x['is_locked'] or x['failed_attempts']>=3]+[a for a in logs if a['action'] in ('PASSWORD_FAIL','MFA_FAIL')], 'Confirmar la identidad y revisar intentos antes de desbloquear.','Errores de escritura o reloj del teléfono.'),
      ('TH-02','Media','Cobertura de MFA y términos',[{'matricula':x['username'],'MFA':bool(x['mfa_configured']),'terminos':accepted(x)} for x in users if x['is_active'] and (not x['mfa_configured'] or not accepted(x))],'Completar MFA y aceptación antes de activar credenciales.','Una cuenta recién creada puede estar pendiente.'),
      ('TH-03','Alta','Accesos físicos denegados',[e for e in events if e['verdict']=='DENIED'],'Revisar credencial, zona y operador.','Tarjetas de prueba o escaneos accidentales.'),
      ('TH-04','Baja','Actividad privilegiada reciente',[a for a in logs if a['action'] in ('USER_UPDATED','PASSWORD_RESET','MFA_RESET','SYSTEM_ADMIN_ASSIGNED','LICENSE_ASSIGNED','LICENSE_REVOKED','ZONES_UPDATED','VISITOR_REVOKED')],'Corroborar que el cambio fue autorizado.','El mantenimiento legítimo también genera estos eventos.'),
      ('TH-05','Alta','Credenciales críticas en cuentas bloqueadas',[{'matricula':x['username'],'rfid':x['rfid_uid'],'licencias':[dict(a) for a in c.execute("SELECT license_id FROM user_licenses WHERE matricula=? AND license_id<>'LIC-IAM-STD'",(x['username'],))]} for x in users if x['is_locked'] and (x['rfid_uid'] or c.execute("SELECT 1 FROM user_licenses WHERE matricula=? AND license_id<>'LIC-IAM-STD'",(x['username'],)).fetchone())],'Revisar la retención de credenciales; el verificador deniega cuentas bloqueadas.','Bloqueo temporal por error del titular.')]
    return [{'code':code,'severity':severity,'title':title,'count':len(ev),'evidence':json.dumps(ev[:30],ensure_ascii=False),'recommendation':rec,'false_positive_note':fp} for code,severity,title,ev,rec,fp in groups if ev and (code!='TH-01' or any(x['is_locked'] for x in users) or len(ev)>=3)]

def dispatch(session,method,path,q,body):
    """Lecturas en snapshot sin escritura; mutaciones autorizadas en transacción."""
    if path not in ROUTES.get(method,set()):raise ValueError('Método o ruta no admitidos.')
    if path=='/api/cctv/test':
        # La espera de red no debe bloquear las escrituras de identidad.
        with db.get_connection() as c:
            u=actor(c,session)
            if not camera_admin(c,u):raise PermissionError('Se requiere administración de cámaras para probar direcciones nuevas.')
            import hardening
            url=hardening.camera_target(c,body.get('url',''))
        return camera_hub.probe(url)
    with (sec.read_transaction() if method=='GET' else sec.write_transaction()) as c:
        u=actor(c,session,terms=path!='/api/auth/accept-terms')
        username=q.get('matricula') or body.get('matricula') or u['username']
        if path=='/api/auth/accept-terms':
            if body.get('accepted') is not True or body.get('version')!=db.TERMS_VERSION:raise ValueError('Acepta explícitamente la versión vigente.')
            accept(c,u,'LOGIN');return {'ok':True}
        if path=='/api/mobile-passes/renew':
            if not global_admin(u):raise PermissionError('Solo administración global renueva entregas conjuntas.')
            items=[];skipped=[]
            for target in c.execute('SELECT * FROM users ORDER BY username').fetchall():
                if u['role']=='dpo' and target['role']=='system_admin':continue
                try:valid_subject(c,{'tipo':'USER','ref':target['username'],'sv':target['security_version']})
                except ValueError:
                    skipped.append({'id':target['username'],'name':target['full_name'],'reason':'Completar MFA, contraseña inicial o desbloqueo/activación.'});continue
                items.append({'id':target['username'],'name':target['full_name'],'kind':'USER','pass_token':delivery(c,u,'USER',target)})
            for target in c.execute("SELECT * FROM visitors WHERE status='ACTIVE'").fetchall():
                if datetime.fromisoformat(target['valid_until']).timestamp()<=time.time():continue
                items.append({'id':target['visitor_id'],'name':target['full_name'],'kind':'VISITOR','pass_token':delivery(c,u,'VISITOR',target)})
            audit(c,u,'MOBILE_PASSES_RENEWED',details=str(len(items))+' entregas privadas; no modifica gafetes existentes')
            return {'deliveries':items,'skipped':skipped}
        if path in ('/api/users/qr-badge','/api/users/qr-badge.png','/api/users/mobile-pass'):
            target=can_view(c,u,username)
            valid_subject(c,{'tipo':'USER','ref':username,'sv':target['security_version']})
            if path.endswith('mobile-pass'):return {'pass_token':delivery(c,u,'USER',target)}
            b=badge(c,'USER',target)
            if not b['token']:raise ValueError('Términos pendientes: entrega un enlace móvil para aceptarlos.')
            result={'badge':b,'qr_png_base64':qr(b['token'])}
            if path.endswith('.png'):result.update(png_base64=base64.b64encode(build_wallet_png(b)).decode(),filename='gafete_'+str(target['id'])+'.png')
            return result
        if path=='/api/licenses':return {'licenses':catalog(c)}
        if path=='/api/users/licenses':
            can_view(c,u,username);return {'licenses':[dict(x) for x in c.execute('SELECT * FROM user_licenses WHERE matricula=?',(username,))]}
        if path in ('/api/users/assign-license','/api/users/revoke-license'):
            target=row_user(c,username) if u['role']=='system_admin' and username==u['username'] else manager(c,u,username)
            lic=body.get('license_id');catalogue=c.execute('SELECT * FROM licenses_catalog WHERE license_id=?',(lic,)).fetchone()
            if not catalogue:raise ValueError('Licencia desconocida.')
            if lic=='LIC-CCTV-ADMIN' and not global_admin(u):raise PermissionError('Solo administración global concede o retira administración de cámaras.')
            required_zone=next((zone for zone,license_id in ZONE_LICENSE.items() if license_id==lic),None)
            if not global_admin(u) and required_zone and required_zone not in zones(u):raise PermissionError('Licencia fuera de las zonas que administras.')
            if 'assign' in path:
                if lic in ('LIC-CCTV-ADMIN','LIC-DC-VAULT','LIC-SRV-CRIT') and not target['ever_enrolled'] and c.execute('SELECT 1 FROM initial_password_grants WHERE user_id=? AND shared=1',(target['id'],)).fetchone():raise ValueError('Emite primero una contraseña temporal individual para esta cuenta antes de darle acceso privilegiado.')
                if not target['is_active']:raise ValueError('Cuenta inactiva.')
                if c.execute('SELECT 1 FROM user_licenses WHERE matricula=? AND license_id=?',(username,lic)).fetchone():return {'ok':True}
                if c.execute('SELECT COUNT(*) FROM user_licenses WHERE license_id=?',(lic,)).fetchone()[0]>=catalogue['seats']:raise Conflict('Cupo de licencia agotado.')
                c.execute('INSERT INTO user_licenses(matricula,license_id,assigned_by,assigned_at) VALUES(?,?,?,?)',(username,lic,u['username'],now()));action='LICENSE_ASSIGNED'
            else:c.execute('DELETE FROM user_licenses WHERE matricula=? AND license_id=?',(username,lic));action='LICENSE_REVOKED'
            audit(c,u,action,username,lic);return {'ok':True}
        if path=='/api/users/zones':
            target=can_view(c,u,username)
            if method=='POST':
                manager(c,u,username);zs=body.get('zones')
                if not isinstance(zs,list) or any(z not in db.ZONES for z in zs):raise ValueError('Zonas inválidas.')
                if not global_admin(u) and not set(zs)<=set(zones(u)):raise PermissionError('No puedes conceder una zona fuera de tu alcance.')
                c.execute('UPDATE users SET allowed_zones=? WHERE id=?',(json.dumps(list(dict.fromkeys(zs))),target['id']))
                audit(c,u,'ZONES_UPDATED',username,json.dumps(zs));target=row_user(c,username)
            return {'zones':zones(target)}
        if path in ('/api/access/terminal','/api/access/terminal-settings'):
            import access_terminal
            return access_terminal.configure(c,u,body) if method=='POST' else access_terminal.status(c,u)
        if path=='/api/access/settings':
            if not global_admin(u):raise PermissionError('Solo administración global.')
            if method=='POST':
                capacity=body.get('rfid_capacity')
                if type(capacity)!=int or not 1<=capacity<=40:raise ValueError('Cupo entre 1 y 40.')
                # The historical four-person fixture locks its own limit explicitly.
                # Existing installations may have another approved quota; the old
                # visitor restriction flag must not silently force them back to four.
                locked_limit=c.execute("SELECT value FROM access_settings WHERE key='restricted_identity_limit'").fetchone()
                if locked_limit and capacity!=int(locked_limit['value']):raise ValueError('El perfil restringido fija el cupo de identidades; revisa ese perfil antes de cambiarlo.')
                if c.execute("SELECT COUNT(*) FROM user_licenses WHERE license_id='LIC-DC-VAULT'").fetchone()[0]>capacity:raise Conflict('Revoca primero las licencias que excedan el nuevo cupo.')
                c.execute("UPDATE access_settings SET value=? WHERE key='rfid_capacity'",(str(capacity),));c.execute("UPDATE licenses_catalog SET seats=? WHERE license_id='LIC-DC-VAULT'",(capacity,));audit(c,u,'RFID_CAPACITY_UPDATED',details=str(capacity))
            return {'capacity':int(c.execute("SELECT value FROM access_settings WHERE key='rfid_capacity'").fetchone()[0]),'used':c.execute('SELECT COUNT(*) FROM users WHERE is_active=1 AND rfid_uid IS NOT NULL').fetchone()[0]}
        if path.startswith('/api/access/'):
            if path in ('/api/access/events','/api/access/latest') and cctv(c,u):pass
            else:terminal(c,u)
            if path.endswith('/verify'):return {'result':access(c,u,body)}
            if path.endswith('/checkout'):
                p=next((e for e in presence(c,u) if e['id']==body.get('event_id')),None)
                if not p:raise ValueError('La entrada ya no está vigente.')
                # Salida asistida identificada y auditada; nunca vuelve a tratar una matrícula como UID.
                p={k:v for k,v in p.items() if k not in ('id',)};p.update(direction='CHECK_OUT',operator_matricula=u['username'],created_at=now(),reason='Salida asistida por operador')
                cur=c.execute('INSERT INTO access_events('+','.join(p)+') VALUES('+','.join('?' for k in p)+')',tuple(p.values()));p['id']=cur.lastrowid;audit(c,u,'ACCESS_CHECKOUT',p['subject_id'],'Salida asistida');return {'result':p}
            if path.endswith('/presence'):return {'presence':presence(c,u)}
            events=scope_events(c,u,min(250,max(1,int(q.get('limit',100)))))
            return {'event':events[0] if events else None} if path.endswith('/latest') else {'events':events}
        if path=='/api/visitors/approve-device':
            terminal(c,u)
            import pass_exchange
            return pass_exchange.approve(c,u,body.get('id'),body.get('confirmation'))
        if path.startswith('/api/visitors'):
            terminal(c,u)
            if method=='POST':c.execute("UPDATE visitors SET status='EXPIRED' WHERE status='ACTIVE' AND valid_until<?",(now(),))
            if path.endswith('/delivery'):
                v=valid_subject(c,{'tipo':'VISITOR','ref':body.get('visitor_id')})
                if not global_admin(u) and v['host_matricula']!=u['username']:raise PermissionError('Invitado fuera de tu alcance.')
                return {'visitor':dict(v),'pass_token':delivery(c,u,'VISITOR',v)}
            if path.endswith('/create'):
                z=body.get('allowed_zone');duration=body.get('duration','4h');name=str(body.get('full_name','')).strip()
                if z not in operator_zones(u) or duration not in ('2h','4h','8h','24h') or not name or len(name)>120:raise ValueError('Datos de invitado inválidos.')
                for key in ('organization','visit_reason'):
                    if len(str(body.get(key,'')))>300:raise ValueError('Texto demasiado largo.')
                vid='VIS-'+secrets.token_hex(8).upper();until=datetime.fromtimestamp(time.time()+int(duration[:-1])*3600,timezone.utc).isoformat(timespec='seconds')
                terms=body.get('terms_accepted') is True
                c.execute('INSERT INTO visitors(visitor_id,full_name,organization,visit_reason,host_matricula,allowed_zone,valid_until,terms_accepted,terms_accepted_at,status,qr_token_hash,created_at,terms_version) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)',(vid,name,str(body.get('organization','')),str(body.get('visit_reason','')),u['username'],z,until,int(terms),now() if terms else None,'ACTIVE',None,now(),db.TERMS_VERSION if terms else None))
                v=c.execute('SELECT * FROM visitors WHERE visitor_id=?',(vid,)).fetchone();b=badge(c,'VISITOR',v)
                if b['token']:c.execute('UPDATE visitors SET qr_token_hash=? WHERE visitor_id=?',(hashlib.sha256(b['token'].encode()).hexdigest(),vid))
                audit(c,u,'VISITOR_CREATED',vid)
                if terms:audit(c,u,'TERMS_ACCEPTED',vid,'Aceptación presencial atestiguada por operador, version='+db.TERMS_VERSION)
                return {'visitor':dict(v),'pass_token':delivery(c,u,'VISITOR',v),'badge':b,'qr_png_base64':qr(b['token']) if b['token'] else None,'png_base64':base64.b64encode(build_wallet_png(b)).decode() if b['token'] else None}
            if path.endswith('/revoke'):
                v=c.execute('SELECT * FROM visitors WHERE visitor_id=?',(body.get('visitor_id'),)).fetchone()
                if not v or (not global_admin(u) and v['host_matricula']!=u['username']):raise PermissionError('Invitado fuera de alcance.')
                c.execute("UPDATE visitors SET status='REVOKED' WHERE visitor_id=?",(v['visitor_id'],));audit(c,u,'VISITOR_REVOKED',v['visitor_id']);return {'ok':True}
            return {'visitors':[{**dict(v),'terms_accepted':int(accepted(v)),'status':'EXPIRED' if v['status']=='ACTIVE' and datetime.fromisoformat(v['valid_until']).timestamp()<=time.time() else v['status']} for v in c.execute('SELECT * FROM visitors ORDER BY created_at DESC LIMIT 250') if global_admin(u) or v['host_matricula']==u['username']], 'pending_devices':[dict(r) for r in c.execute("SELECT r.id,r.confirmation,r.subject_id,v.full_name,v.host_matricula FROM pass_receipts r JOIN visitors v ON v.visitor_id=r.subject_id WHERE r.subject_type='VISITOR' AND r.status='pending' AND r.expires>?",(time.time(),)) if global_admin(u) or r['host_matricula']==u['username']]}
        if path=='/api/threats':return {'findings':threats(c,u),'window_hours':24,'generated_at':now()}
        if path=='/api/users/initial-password-group':
            if not global_admin(u):raise PermissionError('Solo administración global habilita el ingreso grupal.')
            if body.get('acknowledged') is not True:raise ValueError('Confirma el uso temporal de una contraseña común.')
            import initial_passwords
            return initial_passwords.issue_group(c,u['username'])
        if path=='/api/users/initial-password':
            if not global_admin(u):raise PermissionError('Solo administración global habilita el primer ingreso.')
            target=manager(c,u,username)
            import initial_passwords
            return initial_passwords.issue(c,target['username'],u['username'])
        if path=='/api/users/activation':
            target=manager(c,u,username)
            if not global_admin(u):raise PermissionError('Solo administración global habilita el primer ingreso.')
            import hardening
            return {'activation_ticket':hardening.activation_issue(c,target['username'],u['username'])}
        if path=='/api/cctv/destinations':
            if not camera_admin(c,u):raise PermissionError('Sin administración de cámaras.')
            import hardening
            if method=='POST':
                url=camera_url(body.get('url',''));action=body.get('action')
                if action=='request':
                    c.execute("INSERT INTO camera_destinations VALUES(?,'pending',?,NULL,?) ON CONFLICT(url) DO NOTHING",(url,u['username'],now()))
                elif action in ('approve','revoke'):
                    if not global_admin(u):raise PermissionError('Solo administración global aprueba destinos IP.')
                    if action=='approve':c.execute("INSERT INTO camera_destinations VALUES(?,'approved',?,?,?) ON CONFLICT(url) DO UPDATE SET status='approved',approved_by=excluded.approved_by,updated_at=excluded.updated_at",(url,u['username'],u['username'],now()))
                    else:
                        c.execute("UPDATE camera_destinations SET status='revoked',updated_at=? WHERE url=?",(now(),url))
                        camera_hub.reconcile([dict(ch) for ch in c.execute("SELECT ch.* FROM camera_channels ch JOIN camera_destinations d ON d.url=ch.url AND d.status='approved'")])
                else:raise ValueError('Acción de destino inválida.')
                audit(c,u,'CCTV_DESTINATION_'+str(action).upper(),details=url)
            return {'destinations':[dict(r) for r in c.execute('SELECT * FROM camera_destinations ORDER BY updated_at DESC')],'can_approve':global_admin(u)}
        if path=='/api/cctv/network':
            if not camera_admin(c,u):raise PermissionError('Se requiere administración de cámaras.')
            import socket
            hints=[]
            for family,_,_,_,address in socket.getaddrinfo(socket.gethostname(),None,socket.AF_INET):
                try:
                    ip=ipaddress.ip_address(address[0])
                    if any(ip in ipaddress.ip_network(n) for n in ('10.0.0.0/8','172.16.0.0/12','192.168.0.0/16')):hints.append(address[0])
                except ValueError:pass
            return {'server_addresses':list(dict.fromkeys(hints)),'note':'Usa la IP actual que muestra IP Camera Lite en el teléfono. La conexión debe llegar desde esta laptop; algunas redes universitarias aíslan dispositivos.'}
        if path=='/api/cctv/remove':
            if not camera_admin(c,u):raise PermissionError('Se requiere administración de cámaras para eliminar un canal.')
            channel_id=body.get('id');expected=body.get('expected')
            if type(channel_id)!=int or channel_id<1 or not isinstance(expected,dict):raise ValueError('Selecciona una cámara guardada.')
            ch=c.execute('SELECT * FROM camera_channels WHERE id=?',(channel_id,)).fetchone()
            if not ch:raise Conflict('La cámara ya no existe. Actualiza la lista.')
            if expected!={k:ch[k] for k in ('name','url','profile','updated_at')}:raise Conflict('La cámara cambió en otra sesión. Actualiza la lista antes de eliminarla.')
            c.execute('DELETE FROM camera_channels WHERE id=?',(channel_id,))
            camera_hub.reconcile([dict(row) for row in c.execute('SELECT * FROM camera_channels')])
            audit(c,u,'CCTV_IP_REMOVED',details=ch['name'])
            return {'ok':True,'removed_id':channel_id}
        if path=='/api/cctv/channels':
            if not cctv(c,u):raise PermissionError('Sin permiso CCTV.')
            if method=='POST':
                if not camera_admin(c,u):raise PermissionError('Se requiere administración de cámaras para configurar canales.')
                channels=body.get('channels')
                if not isinstance(channels,list) or len(channels)>camera_hub.MAX_CHANNELS:raise ValueError('Máximo ocho canales.')
                checked=[]
                for i,ch in enumerate(channels):
                    if not ch.get('url'):continue
                    profile=ch.get('profile','balanced')
                    if profile not in camera_hub.PROFILES:raise ValueError('Perfil de vídeo inválido.')
                    checked.append((i+1,str(ch.get('name','Canal'))[:60],__import__('hardening').camera_target(c,ch['url']),now(),profile))
                c.execute('DELETE FROM camera_channels');c.executemany('INSERT INTO camera_channels(id,name,url,updated_at,profile) VALUES(?,?,?,?,?)',checked);audit(c,u,'CCTV_CONFIG_UPDATED',details=str(len(checked))+' canales')
                camera_hub.reconcile([dict(ch) for ch in c.execute('SELECT * FROM camera_channels')])
            return {'channels':[dict(ch) for ch in c.execute('SELECT * FROM camera_channels ORDER BY id')],'can_edit':camera_admin(c,u),'live':camera_hub.existing_status(),'max_channels':camera_hub.MAX_CHANNELS,'max_video_views':16}
        raise ValueError('Operación no encontrada.')

ROUTES={
 'GET':set('/api/access/terminal /api/cctv/destinations /api/users/qr-badge /api/users/qr-badge.png /api/licenses /api/users/licenses /api/users/zones /api/access/settings /api/access/latest /api/access/events /api/access/presence /api/visitors /api/threats /api/cctv/channels /api/cctv/network'.split()),
 'POST':set('/api/users/initial-password-group /api/users/initial-password /api/cctv/remove /api/access/terminal-settings /api/cctv/destinations /api/users/activation /api/visitors/approve-device /api/visitors/delivery /api/auth/accept-terms /api/users/mobile-pass /api/mobile-passes/renew /api/users/assign-license /api/users/revoke-license /api/users/zones /api/access/settings /api/access/verify /api/access/checkout /api/visitors/create /api/visitors/revoke /api/cctv/channels /api/cctv/test'.split())}

def _qr_png(data: str, box=8) -> bytes:
    import qrcode  # dependencia ya presente en el proyecto
    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_M,
                       box_size=box, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#182323", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def qr_png_base64(data: str) -> str:
    """QR en PNG codificado en base64 (para incrustar como data URI)."""
    return base64.b64encode(_qr_png(data)).decode("ascii")


def _font(size):
    """Carga una fuente razonable; cae a la por defecto de Pillow si no hay TTF."""
    from PIL import ImageFont
    for ruta in (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:/Windows/Fonts/segoeuib.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
    ):
        if os.path.exists(ruta):
            try:
                return ImageFont.truetype(ruta, size)
            except OSError:
                continue
    return ImageFont.load_default()


def build_wallet_png(badge: dict) -> bytes:
    """
    Genera la credencial vertical estilo Wallet (PNG de alta resolución) con el
    QR grande, nombre, matrícula, rol, zonas y vigencia. Lista para descargar
    o compartir por WhatsApp.
    """
    from PIL import Image, ImageDraw, ImageOps
    W, H = 720, 1180
    bg = "#f6f7f6"
    dark = "#182323"
    green = "#155d45"
    gray = "#5d6e63"

    img = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(img)

    # Cabecera
    d.rectangle([0, 0, W, 210], fill=dark)
    d.rectangle([0, 210, W, 222], fill=green)
    d.text((48, 60), "SECURITY TEAM", font=_font(52), fill="white")
    d.text((48, 130), "Identity Console · UPY", font=_font(30), fill="#9fe3c5")


    # QR centrado (alto contraste)
    qr_img = Image.open(io.BytesIO(_qr_png(badge["token"], box=10))).convert("RGB")
    qr_size = 440
    qr_img = ImageOps.contain(qr_img, (qr_size, qr_size), method=Image.Resampling.NEAREST)
    qx = (W - qr_img.width) // 2
    qy = 250
    img.paste(qr_img, (qx, qy))

    y = qy + qr_img.height + 40
    def fit(text,size):
        while size>14 and d.textbbox((0,0),text,font=_font(size))[2]>W-96:size-=1
        return _font(size)
    d.text((W // 2, y), badge["full_name"], font=fit(badge['full_name'],36), fill=dark, anchor="mm")
    y += 52
    d.text((W // 2, y), f"ID: {badge['matricula']}", font=_font(30), fill=gray, anchor="mm")
    y += 48
    label=f"{db.ROLE_LABELS.get(badge.get('role'),badge.get('role','')).upper()} · {badge.get('area','')}"
    d.text((W // 2, y), label, font=fit(label,26), fill=green, anchor="mm")

    # Zonas autorizadas
    y += 60
    d.text((48, y), "ZONAS AUTORIZADAS", font=_font(24), fill=gray)
    y += 40
    for z in badge.get("zones_labels", []) or ["—"]:
        d.text((60, y), f"• {z}", font=_font(26), fill=dark)
        y += 40

    # Pie
    d.rectangle([0, H - 90, W, H], fill=dark)
    d.text((W // 2, H - 45), badge.get("valid_hint", ""), font=_font(22),
           fill="#9fe3c5", anchor="mm")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


