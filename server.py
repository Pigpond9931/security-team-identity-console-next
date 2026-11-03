"""Servidor local Python: API de identidad y aplicación React del mismo origen."""
import argparse
import base64
from contextlib import closing
import json
import mimetypes
import os
from pathlib import Path
import secrets
import sqlite3
import threading
import time
from http import cookies
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer as BaseHTTPServer
from urllib.parse import urlsplit, parse_qs, quote
import webbrowser

ROOT=Path(__file__).resolve().parent
WEB_ROOT=ROOT/'web'
DATA=Path(os.environ.get('ST_DATA_DIR',str(ROOT/'data')))
DATA.mkdir(parents=True,exist_ok=True)
os.environ['ST_DB_PATH']=str(DATA/'identity.sqlite')
os.environ['ST_KEY_PATH']=str(DATA/'.mfa-key')
import db_manager as db
import security as secure
import windows_store as store
import features
import phone_links
import browser_cameras
import hardening
import pass_exchange

SESSIONS={}
SESSION_LOCK=threading.RLock()
RATE={}
RATE_LOCK=threading.Lock()
PUBLIC_ORIGIN=''

def configure_public(url):
    global PUBLIC_ORIGIN
    value=urlsplit(url)
    if value.scheme!='https' or not value.hostname or value.username or value.password or value.query or value.fragment or value.path not in ('','/'):
        raise ValueError('La dirección pública debe ser un origen HTTPS exacto.')
    PUBLIC_ORIGIN='https://'+value.netloc.lower()

class ThreadingHTTPServer(BaseHTTPServer):
    daemon_threads=True
    def __init__(self,*args,**kwargs):
        self.slots=threading.BoundedSemaphore(64)
        self.video_slots=threading.BoundedSemaphore(16)
        super().__init__(*args,**kwargs)
    def process_request(self,request,address):
        if not self.slots.acquire(blocking=False):
            try:request.sendall(b'HTTP/1.0 503 Busy\r\nContent-Length: 0\r\n\r\n')
            finally:self.close_request(request)
            return
        try:super().process_request(request,address)
        except BaseException:self.slots.release();raise
    def process_request_thread(self,*args):
        try:super().process_request_thread(*args)
        finally:self.slots.release()

def initialize():
    """Inicializa el directorio configurado sin importar datos de otra instalación."""
    store.private_directory(DATA)
    fresh=not Path(db.DB_PATH).exists()
    db.init_db()
    db.seed_users()  # Marca bases importadas sin insertar y no repite el seed.
    secure.migrate()
    db.migrate_extensions()
    with secure.write_transaction() as conn:hardening.migrate(conn)
    # Crear la clave antes de aceptar inscripciones MFA concurrentes.
    secure.cipher()
    secure.encrypt_existing_secrets()

def make_session():
    # Cota de memoria: no desplaza sesiones autenticadas para admitir desconocidos.
    now=time.time()
    for key in [k for k,v in SESSIONS.items() if now-v['created']>1800]:SESSIONS.pop(key,None)
    if len(SESSIONS)>=4096:raise SessionCapacity()
    sid=secrets.token_urlsafe(32)
    state={'csrf':secrets.token_urlsafe(32),'created':time.time(),'stage':'login'}
    SESSIONS[sid]=state
    return sid,state

class SessionCapacity(Exception):pass

class Handler(BaseHTTPRequestHandler):
    def handle_one_request(self):
        try:return super().handle_one_request()
        except SessionCapacity:
            self.close_connection=True
            return self.response(503,{'error':'Capacidad temporal de sesiones alcanzada. Intenta más tarde.'})

    server_version='IdentityConsole'
    sys_version=''

    def end_headers(self):
        headers={'Content-Security-Policy':hardening.CSP+('; upgrade-insecure-requests' if self.public_request() else ''),'Permissions-Policy':'camera=(self), microphone=(), geolocation=(), payment=(), usb=()','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','X-Robots-Tag':'noindex, nofollow, noarchive'}
        if self.public_request() and self.headers.get('X-Forwarded-Proto','https')!='http':headers['Strict-Transport-Security']='max-age=31536000; includeSubDomains'
        for name,value in headers.items():
            if not any(h.lower().startswith((name.lower()+':').encode()) for h in self._headers_buffer):self.send_header(name,value)
        super().end_headers()

    def redirect_https(self):
        if self.public_request() and getattr(self.server,'trusted_proxy','') and self.headers.get('X-Forwarded-Proto','').lower()=='http':
            target=self.public_origin()+quote(urlsplit(self.path).path,safe='/:%@!$&()*+,;=-._~')
            query=urlsplit(self.path).query
            if query:target+='?'+quote(query,safe='=&%+/:@-._~')
            self.send_response(308);self.send_header('Location',target);self.send_header('Content-Length','0');self.send_header('Cache-Control','no-store');self.end_headers();return True
        return False

    def send_error(self,code,message=None,explain=None):
        return self.response(code,{'error':'Solicitud no admitida.'})

    def capability_cookie(self,name):
        parsed=cookies.SimpleCookie()
        try:parsed.load(self.headers.get('Cookie',''))
        except cookies.CookieError:return ''
        return parsed[name].value if name in parsed else ''

    def setup(self):
        super().setup();self.connection.settimeout(10)

    def public_request(self):
        origin=self.public_origin()
        return bool(origin and self.headers.get('Host','').lower()==urlsplit(origin).netloc)

    def public_origin(self):return getattr(self.server,'public_origin',PUBLIC_ORIGIN)

    def log_message(self,fmt,*args):
        # No registrar cuerpos, contraseñas, códigos, cookies ni secretos.
        print('%s %s'%(self.command,urlsplit(self.path).path),flush=True)

    def response(self,status,payload,session_id=None,capability=None):
        data=json.dumps(payload,ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(data)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        if session_id:
            secure_cookie='; Secure' if self.public_request() else ''
            self.send_header('Set-Cookie',f'st_session={session_id}; Path=/; HttpOnly; SameSite=Strict; Max-Age=1800{secure_cookie}')
        if capability:
            name,value,path=capability
            self.send_header('Set-Cookie',name+'='+value+'; Path='+path+'; HttpOnly; SameSite=Strict; Max-Age='+('1800' if value else '0')+('; Secure' if self.public_request() else ''))
        self.end_headers()
        self.wfile.write(data)

    def session(self):
        parsed=cookies.SimpleCookie()
        try: parsed.load(self.headers.get('Cookie',''))
        except cookies.CookieError: pass
        sid=parsed['st_session'].value if 'st_session' in parsed else None
        with SESSION_LOCK:
            now=time.time()
            for token in [k for k,v in SESSIONS.items() if now-v['created']>1800]: SESSIONS.pop(token,None)
            if sid not in SESSIONS: return make_session()
            return sid,SESSIONS[sid]

    def allowed_host(self):
        allowed={f'127.0.0.1:{self.server.server_port}',f'localhost:{self.server.server_port}'}
        if self.public_origin():allowed.add(urlsplit(self.public_origin()).netloc)
        return self.headers.get('Host','').lower() in allowed

    def state_payload(self,state):
        user=None
        if state.get('auth'):
            user=secure.current_user(state['auth'])
            if not user:
                state.clear()
                state.update(csrf=secrets.token_urlsafe(32),created=time.time(),stage='login')
        if state.get('challenge'):
            with db.get_connection() as conn: pending=secure.challenge_user(conn,state['challenge'])
            if pending is None:
                state.clear()
                state.update(csrf=secrets.token_urlsafe(32),created=time.time(),stage='login')
        if user and state['stage']=='dashboard' and not features.accepted(user):state['stage']='terms'
        result={'stage':state['stage'],'csrf':state['csrf'],'user':user}
        if user:result.update(areas=db.AREAS,roles=db.ROLE_LABELS)
        if user:
            with db.get_connection() as conn:
                current=features.row_user(conn,user['username'])
                result['permissions']={'terminal':features.global_admin(current) or current['role']=='area_admin' or bool(current['is_guard']),
                    'cctv':bool(features.cctv(conn,current)), 'cctv_admin':bool(features.camera_admin(conn,current)), 'threats':current['role'] in (*db.GLOBAL_ROLES,'area_admin')}
        if state['stage']=='terms':result['terms']={'title':features.TERMS_TITLE,'body':features.TERMS_BODY,'version':db.TERMS_VERSION}
        if state['stage']=='backup':result['recovery_codes']=state.get('recovery_codes',[])
        if state.get('challenge') and pending is not None:
            result['mfa_reset_pending']=bool(pending['mfa_reset_pending'])
        if state['stage']=='enroll':
            secret=state['secret']
            uri=db.build_provisioning_uri(secret,state['username'])
            result['qr']='data:image/png;base64,'+base64.b64encode(db.generate_qr_png(uri)).decode('ascii')
            result['enrollment_key']=secret
        return result

    def do_GET(self):
        if not self.allowed_host(): return self.response(403,{'error':'Origen no autorizado.'})
        if self.redirect_https():return
        path=urlsplit(self.path).path
        if path=='/api/health': return self.response(200,{'ok':True,'application':'SECURITY_TEAM_Studio','version':'1.5.2','mode':'shared' if PUBLIC_ORIGIN else 'local'})
        q={k:v[0] for k,v in parse_qs(urlsplit(self.path).query).items()}
        if path in ('/api/terms','/api/public-pass'):
            sid,state=self.session()
            if path=='/api/terms':return self.response(200,{'title':features.TERMS_TITLE,'body':features.TERMS_BODY,'version':db.TERMS_VERSION,'csrf':state['csrf']},sid)
            try:
                with secure.write_transaction() as conn:
                    if q.get('token'):result=pass_exchange.preview(conn,q['token'])
                    else:result=pass_exchange.read(conn,self.capability_cookie('st_pass'),sid,state.get('auth'),download=q.get('download')=='1')
                return self.response(200,dict(result,csrf=state['csrf']),sid)
            except PermissionError:return self.response(403,{'error':'Inicia sesión con la cuenta titular.'},sid)
            except ValueError:return self.response(400,{'error':'Pase inválido, revocado o expirado.'},sid)
        if path.startswith('/api/'):
            sid,state=self.session()
            payload=self.state_payload(state)
            if path=='/api/session': return self.response(200,payload,sid)
            user=payload['user']
            if not user: return self.response(401,{'error':'Inicia sesión para continuar.'},sid)
            if not features.accepted(user):return self.response(403,{'error':'Acepta los términos para continuar.'},sid)
            if path=='/api/cctv/stream':return self.camera_stream(state,q,sid)
            if path=='/api/browser-camera/stream':return self.browser_camera_stream(state,q,sid)
            if path in features.ROUTES['GET']:
                try:return self.response(200,features.dispatch(state.get('auth'),'GET',path,q,{}),sid)
                except PermissionError:return self.response(403,{'error':'Sin permiso para esta operación.'},sid)
                except ValueError as e:return self.response(400,{'error':str(e)},sid)
            if path=='/api/data':
                snapshot=secure.dashboard_data(state.get('auth'))
                if snapshot is None:return self.response(401,{'error':'Tu sesión caducó.'},sid)
                return self.response(200,snapshot,sid)
            return self.response(404,{'error':'Ruta no encontrada.'},sid)
        webroot=WEB_ROOT
        file=webroot/('index.html' if path in ('/','/index.html','/pass','/scanner','/camera','/activate') else path.lstrip('/'))
        try:
            file=file.resolve()
            if not file.is_relative_to(webroot.resolve()) or not file.is_file():
                return self.response(404,{'error':'Archivo no encontrado.'})
            content=file.read_bytes()
        except OSError: return self.response(404,{'error':'Archivo no encontrado.'})
        self.send_response(200)
        mime=mimetypes.guess_type(str(file))[0] or 'application/octet-stream'
        self.send_header('Content-Type',mime+('; charset=utf-8' if mime.startswith('text/') else ''))
        self.send_header('Content-Length',str(len(content)))
        self.send_header('Cache-Control','no-store')
        self.send_header('Referrer-Policy','no-referrer')
        self.send_header('X-Content-Type-Options','nosniff')
        self.end_headers()
        self.wfile.write(content)

    def camera_stream(self,state,q,sid):
        import camera_hub
        feed=None;headers=False
        if not self.server.video_slots.acquire(blocking=False):
            return self.response(503,{'error':'Hay 16 vistas de vídeo activas. Pausa otra cámara para liberar una vista.'},sid)
        try:
            with db.get_connection() as conn:
                user=features.actor(conn,state.get('auth'))
                if not features.cctv(conn,user):raise PermissionError()
                ch=conn.execute('SELECT * FROM camera_channels WHERE id=?',(int(q.get('id',0)),)).fetchone()
                if not ch:raise ValueError()
                hardening.camera_target(conn,ch['url'])
                feed=camera_hub.get_feed(dict(ch))
            feed.clients+=1
            seq,frame,captured=feed.latest(0,6)
            if not frame:raise ValueError()
            self.send_response(200);self.send_header('Content-Type','multipart/x-mixed-replace; boundary=STFRAME');self.send_header('Cache-Control','no-store, no-cache');self.send_header('X-Content-Type-Options','nosniff');self.end_headers();headers=True
            deadline=time.monotonic()+1800
            previous=-1;checked=0
            while time.monotonic()<deadline and not feed.stop.is_set():
                if time.monotonic()-checked>=1:
                    if not self.camera_owner_alive(sid,state.get('auth')):break
                    with db.get_connection() as conn:
                        viewer=secure.session_user(conn,state.get('auth'))
                        if not viewer or not features.accepted(viewer) or not features.cctv(conn,viewer):break
                        current=conn.execute('SELECT * FROM camera_channels WHERE id=?',(ch['id'],)).fetchone()
                        if not current or current['url']!=ch['url'] or current['profile']!=ch['profile']:break
                        try:hardening.camera_target(conn,ch['url'])
                        except PermissionError:break
                    checked=time.monotonic()
                if frame and seq!=previous and time.time()-captured<8:
                    self.wfile.write(b'--STFRAME\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(frame)).encode()+b'\r\n\r\n'+frame+b'\r\n');self.wfile.flush();previous=seq
                seq,frame,captured=feed.latest(previous,2)
            self.close_connection=True
        except PermissionError:
            if not headers:self.response(403,{'error':'Sin permiso CCTV.'},sid)
        except (OSError,ValueError):
            if not headers:
                try:self.response(502,{'error':'Cámara no disponible. Usa Probar conexión y revisa la IP actual del teléfono.'},sid)
                except OSError:pass
        finally:
            if feed:feed.clients=max(0,feed.clients-1)
            self.server.video_slots.release()

    def camera_owner_alive(self,owner_sid,auth):
        with SESSION_LOCK:
            parent=SESSIONS.get(owner_sid)
            return bool(parent and parent.get('stage')=='dashboard' and parent.get('auth')==auth and time.time()-parent['created']<=1800)

    def browser_camera_stream(self,state,q,sid):
        headers=False;opened=False;body={'id':q.get('id',''),'peer':q.get('peer','')}
        if not self.server.video_slots.acquire(blocking=False):return self.response(503,{'error':'Pausa otra vista de vídeo.'},sid)
        try:
            browser_cameras.stream_open(body,sid,state,self.camera_owner_alive);opened=True
            self.send_response(200)
            self.send_header('Content-Type','multipart/x-mixed-replace; boundary=STFRAME')
            self.send_header('Cache-Control','no-store, no-cache, no-transform')
            self.send_header('X-Accel-Buffering','no');self.send_header('X-Content-Type-Options','nosniff')
            self.end_headers();headers=True;previous=-1;checked=0
            while self.camera_owner_alive(sid,state.get('auth')):
                if time.monotonic()-checked>=1:
                    browser_cameras.dispatch('/api/browser-camera/viewer-poll',body,sid,state,self.camera_owner_alive)
                    checked=time.monotonic()
                seq,frame,captured=browser_cameras.stream_latest(body,previous)
                if seq!=previous and frame and time.time()-captured<3:
                    self.wfile.write(b'--STFRAME\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(frame)).encode()+b'\r\n\r\n'+frame+b'\r\n');self.wfile.flush()
                previous=seq
        except PermissionError:
            if not headers:self.response(403,{'error':'Sin permiso para esta vista CCTV.'},sid)
        except OSError:pass
        finally:
            self.close_connection=True
            if opened:
                try:browser_cameras.dispatch('/api/browser-camera/leave',body,sid,state,self.camera_owner_alive)
                except (PermissionError,ValueError):pass
            self.server.video_slots.release()

    def do_POST(self):
        if self.allowed_host() and self.redirect_https():return
        origin=self.headers.get('Origin','')
        expected=self.public_origin() if self.public_request() else 'http://'+self.headers.get('Host','')
        if not self.allowed_host() or origin!=expected:
            return self.response(403,{'error':'Origen no autorizado.'})
        sid,state=self.session()
        if not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),state['csrf']):
            return self.response(403,{'error':'La sesión cambió. Recarga la página.'},sid)
        try:
            path=urlsplit(self.path).path
            size=int(self.headers.get('Content-Length','0'))
            limit=195000 if path=='/api/browser-camera/upload-frame' else 280000 if path=='/api/browser-camera/upload' else 40000 if path in browser_cameras.PUBLIC|browser_cameras.PRIVATE else 16384
            if not 0<size<=limit: return self.response(400,{'error':'Solicitud inválida.'},sid)
            try:
                if path=='/api/browser-camera/upload-frame':
                    if self.headers.get('Content-Type','').split(';')[0]!='image/jpeg':raise ValueError()
                    body={'_raw_jpeg':self.rfile.read(size),'source_seq':int(self.headers.get('X-Frame-Sequence','0'))}
                else:body=json.loads(self.rfile.read(size).decode('utf-8'),parse_constant=lambda v:(_ for _ in ()).throw(ValueError()))
            except (ValueError,UnicodeError,RecursionError):return self.response(400,{'error':'JSON inválido.'},sid)
            if not isinstance(body,dict): raise ValueError('Solicitud inválida.')
            path=urlsplit(self.path).path
            if path in phone_links.PRIVATE|phone_links.PUBLIC|browser_cameras.PRIVATE|browser_cameras.PUBLIC:
                def owner_alive(owner_sid,auth):
                    with SESSION_LOCK:
                        parent=SESSIONS.get(owner_sid)
                        return bool(parent and parent.get('stage')=='dashboard' and parent.get('auth')==auth and time.time()-parent['created']<=1800)
                service=browser_cameras if path.startswith('/api/browser-camera/') else phone_links
                capability=None
                name,cap_path=('st_camera','/api/browser-camera') if service is browser_cameras else ('st_scan','/api/scanner')
                if path in service.PUBLIC and not path.endswith('/claim'):body['phone_token']=self.capability_cookie(name)
                try:result=service.dispatch(path,body,sid,state,owner_alive)
                except PermissionError as error:return self.response(403,{'error':str(error)},sid)
                if result.get('phone_token'):capability=(name,result.pop('phone_token'),cap_path)
                if path.endswith('/disconnect'):capability=(name,'',cap_path)
                if result.get('ticket'):
                    result['pair_url']=(getattr(self.server,'pass_origin','') or self.public_origin() or 'http://'+self.headers['Host'])+('/camera#ticket=' if service is browser_cameras else '/scanner#ticket=')+quote(result.pop('ticket'))
                    result['pair_qr']=features.qr(result['pair_url'])
                return self.response(200,result,sid,capability)
            if path.startswith('/api/auth/') or path.startswith('/api/public-pass'):
                account=body.get('username') if isinstance(body.get('username'),str) else str(state.get('challenge',{}).get('user_id','session:'+sid))
                with RATE_LOCK:
                    allowed=hardening.rate_check(RATE,[('global',1024),('ip:'+hardening.client_key(self),512),('session:'+sid,60),('account:'+account,60)])
                if not allowed:return self.response(429,{'error':'Espera un minuto antes de volver a intentarlo.'},sid)
            if path=='/api/auth/activate':
                if state.get('auth'):raise ValueError('Cierra tu sesión antes de activar la cuenta de otra persona.')
                with secure.write_transaction() as conn:user=hardening.activation_claim(conn,body.get('ticket'),state)
                state['stage']='password' if state.get('challenge') and user['must_change_password'] else 'enroll' if state.get('challenge') else 'login'
                if state.get('challenge'):state['secret']=db.generate_mfa_secret()
                result=self.state_payload(state);result['activation_username']=user['username']
                return self.response(200,result,sid)
            if path=='/api/public-pass/preview':
                with secure.write_transaction() as conn:result=pass_exchange.preview(conn,body.get('token'))
                return self.response(200,dict(result,csrf=state['csrf']),sid)
            if path=='/api/public-pass/claim':
                with secure.write_transaction() as conn:receipt=pass_exchange.claim(conn,body.get('token'),sid,state.get('auth'))
                return self.response(200,{'ok':True,'csrf':state['csrf']},sid,('st_pass',receipt,'/api/public-pass'))
            if path=='/api/public-pass/accept-terms':
                if body.get('accepted') is not True or body.get('version')!=db.TERMS_VERSION:raise ValueError('Aceptación explícita requerida.')
                with secure.write_transaction() as conn:result=pass_exchange.read(conn,self.capability_cookie('st_pass'),sid,state.get('auth'),True)
                return self.response(200,result,sid)
            if path in ('/api/auth/password','/api/auth/recover','/api/auth/mfa'):
                challenge=state.get('challenge')
                if not challenge or not 0<=time.time()-challenge.get('issued_at',0)<=secure.CHALLENGE_SECONDS:
                    with SESSION_LOCK:
                        SESSIONS.pop(sid,None);sid,state=make_session()
                    return self.response(401,dict(self.state_payload(state),error='Tu sesión de verificación de 5 minutos expiró; inicia sesión nuevamente.',code='CHALLENGE_EXPIRED'),sid)
            if path=='/api/auth/login':
                if state.get('auth'):raise ValueError('Cierra primero tu sesión actual.')
                result=secure.authenticate(body.get('username',''),body.get('password',''))
                if result['status']!='ok': return self.response(401,{'error':'Credenciales inválidas.'},sid)
                user=result['user']
                state.update(challenge=result['challenge'],username=user['username'])
                with db.get_connection() as conn:protected=conn.execute('SELECT ever_enrolled FROM users WHERE id=?',(user['id'],)).fetchone()[0]
                if not protected and not user['mfa_configured'] and not hardening.activation_valid(state,user):
                    import initial_passwords
                    with secure.write_transaction() as conn:individual=initial_passwords.claim(conn,user,state)
                    if not individual:
                        state['stage']='activation';return self.response(200,self.state_payload(state),sid)
                state['stage']='password' if user['must_change_password'] else ('mfa' if user['mfa_configured'] else 'recover' if protected else 'enroll')
                if not user['mfa_configured']: state['secret']=db.generate_mfa_secret()
                return self.response(200,self.state_payload(state),sid)
            if path=='/api/auth/password' and state['stage']=='password':
                with db.get_connection() as conn:pending=secure.challenge_user(conn,state.get('challenge'))
                if pending and not pending['ever_enrolled'] and not hardening.activation_valid(state,pending):raise ValueError('Solicita una contraseña temporal individual a la administración e inicia sesión de nuevo.')
                challenge=secure.change_initial_password(state.get('challenge'),body.get('password',''))
                if not challenge: return self.response(401,{'error':'El acceso caducó. Vuelve a iniciar sesión.'},sid)
                state['challenge']=challenge
                with db.get_connection() as conn:protected=conn.execute('SELECT ever_enrolled FROM users WHERE id=?',(challenge['user_id'],)).fetchone()[0]
                state['stage']='mfa' if challenge['mfa_configured'] else 'recover' if protected else 'enroll'
                return self.response(200,self.state_payload(state),sid)
            if path=='/api/auth/recover' and state['stage'] in ('mfa','recover'):
                challenge=secure.recover_mfa(state.get('challenge'),body.get('code',''))
                if not challenge:return self.response(401,{'error':'No fue posible verificar la recuperación.'},sid)
                state.update(challenge=challenge,secret=db.generate_mfa_secret(),stage='enroll',activation={'id':challenge['user_id'],'sv':challenge['security_version'],'expires':time.time()+300})
                return self.response(200,self.state_payload(state),sid)
            if path=='/api/auth/mfa' and state['stage'] in ('mfa','enroll'):
                with db.get_connection() as conn:pending=secure.challenge_user(conn,state.get('challenge'))
                if pending is not None and not pending['ever_enrolled'] and not hardening.activation_valid(state,pending):raise ValueError('El tiempo de configuración venció. Solicita una nueva contraseña temporal a la administración.')
                if pending is not None and pending['mfa_reset_pending']:
                    challenge=secure.recover_mfa(state.get('challenge'),body.get('code',''),'totp')
                    if not challenge:return self.response(401,{'error':'No fue posible verificar el código.'},sid)
                    state.update(challenge=challenge,secret=db.generate_mfa_secret(),stage='enroll',activation={'id':challenge['user_id'],'sv':challenge['security_version'],'expires':time.time()+300})
                    return self.response(200,self.state_payload(state),sid)
                auth=secure.finish_mfa(state.get('challenge'),body.get('code',''),state.get('secret'))
                if not auth: return self.response(401,{'error':'No fue posible verificar el código. Comprueba tu autenticador.'},sid)
                with SESSION_LOCK:
                    SESSIONS.pop(sid,None)
                    sid,state=make_session()
                    codes=auth.pop('recovery_codes',None)
                    state.update(auth=auth,stage='backup' if codes else 'dashboard')
                    if codes:state['recovery_codes']=codes
                return self.response(200,self.state_payload(state),sid)
            if path=='/api/auth/backup-saved' and state['stage']=='backup':
                if not secure.current_user(state.get('auth')):return self.response(401,{'error':'La sesión caducó.'},sid)
                state.pop('recovery_codes',None);state['stage']='dashboard'
                return self.response(200,self.state_payload(state),sid)
            if path in ('/api/auth/logout','/api/auth/cancel'):
                if state.get('auth'):
                    user=secure.current_user(state['auth'])
                    if user: db.log_event(user['username'],'LOGOUT',target=user['username'])
                with SESSION_LOCK:
                    SESSIONS.pop(sid,None)
                    sid,state=make_session()
                return self.response(200,self.state_payload(state),sid)
            user=secure.current_user(state.get('auth'))
            if not user: return self.response(401,{'error':'Tu sesión caducó. Inicia sesión nuevamente.'},sid)
            if path in features.ROUTES['POST']:
                if path=='/api/auth/accept-terms' and state['stage']!='terms':raise PermissionError('Completa primero los pasos de acceso.')
                if path in ('/api/cctv/channels','/api/cctv/remove'):
                    with browser_cameras.LOCK:
                        with secure.write_transaction() as conn:browser_cameras.collect(conn,self.camera_owner_alive)
                        if path=='/api/cctv/channels':
                            if not isinstance(body.get('channels'),list):raise ValueError('Lista de cámaras inválida.')
                            if len(body['channels'])+len(browser_cameras.CHANNELS)>8:raise ValueError('El límite combinado es ocho cámaras. Elimina una cámara para añadir otra.')
                        result=features.dispatch(state.get('auth'),'POST',path,{},body)
                else:result=features.dispatch(state.get('auth'),'POST',path,{},body)
                if result.get('activation_ticket'):
                    result['activation_url']=(getattr(self.server,'pass_origin','') or PUBLIC_ORIGIN or 'http://'+self.headers['Host'])+'/activate#ticket='+quote(result.pop('activation_ticket'))
                    result['activation_qr']=features.qr(result['activation_url'])
                if 'deliveries' in result:
                    for item in result['deliveries']:
                        item['pass_url']=(getattr(self.server,'pass_origin','') or PUBLIC_ORIGIN or 'http://'+self.headers['Host'])+'/pass#delivery='+quote(item.pop('pass_token'))
                if result.get('pass_token'):
                    result['pass_url']=(getattr(self.server,'pass_origin','') or PUBLIC_ORIGIN or 'http://'+self.headers['Host'])+'/pass#delivery='+quote(result['pass_token'])
                    result['delivery_qr']=features.qr(result['pass_url'])
                if path=='/api/auth/accept-terms':
                    state['stage']='dashboard';result=self.state_payload(state)
                return self.response(200,result,sid)
            if not features.accepted(user):return self.response(403,{'error':'Acepta los términos para continuar.'},sid)
            if path=='/api/users/create':
                temporary=secure.create_user(state['auth'],body.get('username'),body.get('full_name'),body.get('role'),body.get('area'),int(body.get('is_guard',False)))
                return self.response(200,{'ok':True,'temporary_password':temporary},sid)
            if path=='/api/users/update':
                changes=body.get('changes',{})
                if not isinstance(changes,dict): raise ValueError('Datos inválidos.')
                secure.update_user(state['auth'],int(body['id']),**changes)
                return self.response(200,{'ok':True},sid)
            if path=='/api/users/reset-mfa':
                secure.reset_mfa(state['auth'],int(body['id']))
                return self.response(200,{'ok':True},sid)
            if path=='/api/users/reset-password':
                temporary=secure.reset_password(state['auth'],int(body['id']))
                return self.response(200,{'ok':True,'temporary_password':temporary},sid)
            if path=='/api/profile/password':
                if not secure.change_password(state['auth'],body.get('current',''),body.get('password',''),body.get('code','')):
                    return self.response(400,{'error':'No fue posible confirmar el cambio.'},sid)
                with SESSION_LOCK:
                    SESSIONS.pop(sid,None)
                    sid,state=make_session()
                return self.response(200,self.state_payload(state),sid)
            if path=='/api/profile/recovery-codes':
                auth=secure.regenerate_recovery_codes(state['auth'],body.get('password',''),body.get('code',''))
                if not auth:return self.response(400,{'error':'No fue posible confirmar tu identidad.'},sid)
                codes=auth.pop('recovery_codes')
                with SESSION_LOCK:
                    SESSIONS.pop(sid,None);sid,state=make_session()
                    state.update(auth=auth,stage='backup',recovery_codes=codes)
                return self.response(200,self.state_payload(state),sid)
            return self.response(404,{'error':'Operación no encontrada.'},sid)
        except features.Conflict as error:return self.response(409,{'error':str(error)},sid)
        except PermissionError: return self.response(403,{'error':'No tienes permisos para esta operación.'},sid)
        except sqlite3.IntegrityError: return self.response(409,{'error':'La matrícula o el UID ya están asignados.'},sid)
        except ValueError as error:return self.response(400,{'error':str(error)[:140] or 'Datos inválidos.'},sid)
        except (KeyError,TypeError,AttributeError,UnicodeError,RecursionError):return self.response(400,{'error':'Datos inválidos.'},sid)
        except sqlite3.OperationalError: return self.response(503,{'error':'La base está ocupada. Intenta otra vez.'},sid)
        except Exception:
            return self.response(500,{'error':'No fue posible completar la operación.'},sid)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--open',action='store_true')
    parser.add_argument('--public-url',default='')
    parser.add_argument('--trusted-proxy',choices=['','ngrok','cloudflare'],default='')
    args=parser.parse_args()
    if args.public_url:configure_public(args.public_url)
    with store.file_lock(DATA/'.server.lock'):
        initialize()
        if args.public_url:
            with db.get_connection() as conn:ready=conn.execute("SELECT 1 FROM users WHERE role='dpo' AND is_active=1 AND is_locked=0 AND mfa_configured=1 AND must_change_password=0 LIMIT 1").fetchone()
            if not ready:raise RuntimeError('Configura primero el acceso y MFA del DPO desde la aplicación local antes de compartir.')
        httpd=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
        httpd.trusted_proxy=args.trusted_proxy
        process_file=DATA/'server-process.json'
        store.atomic_write(process_file,json.dumps({'pid':os.getpid(),'registered_ms':int(time.time()*1000)}).encode())
        import audit_delivery
        delivery=audit_delivery.start_worker()
        print(f'Identity Console · http://127.0.0.1:{args.port}',flush=True)
        if args.open: threading.Timer(.4,lambda:webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
        try: httpd.serve_forever()
        except KeyboardInterrupt: pass
        finally:
            if delivery:delivery.set()
            import camera_hub;camera_hub.stop_all()
            httpd.server_close()
            process_file.unlink(missing_ok=True)

if __name__=='__main__': main()
