"""Quick Tunnels: consola con PIN por correo y portal limitado de pases firmados."""
import argparse,json,os,re,subprocess,sys,threading,time,webbrowser
from pathlib import Path
from urllib.parse import urlsplit
import server
import windows_store as store
from runtime_paths import prepare_private_store

SETTINGS=server.DATA/'cloudflare.dpapi'
CONSOLE_PORT=int(os.environ.get('ST_CONSOLE_PORT','8876'))
PASS_PORT=int(os.environ.get('ST_PASS_PORT','8877'))
if not 1024<=CONSOLE_PORT<=65535 or not 1024<=PASS_PORT<=65535 or CONSOLE_PORT==PASS_PORT:
    raise ValueError('Define dos puertos distintos entre 1024 y 65535 para Next.')
PUBLIC_GET={'/pass','/scanner','/camera','/activate','/api/terms','/api/public-pass','/favicon.svg'}

class PassOnlyHandler(server.Handler):
    def do_GET(self):
        path=urlsplit(self.path).path
        if path not in PUBLIC_GET and not path.startswith('/assets/'):
            return self.response(404,{'error':'Este portal solo entrega pases firmados.'})
        return super().do_GET()
    def do_POST(self):
        if urlsplit(self.path).path not in {'/api/public-pass/preview','/api/public-pass/accept-terms','/api/public-pass/claim',*server.phone_links.PUBLIC,*server.browser_cameras.PUBLIC}:
            return self.response(404,{'error':'Este portal no ofrece acceso a la consola.'})
        return super().do_POST()

def emails_valid(emails):
    result=list(dict.fromkeys(str(e).strip().lower() for e in emails))
    if not result or any(not re.fullmatch(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',e) for e in result):
        raise ValueError('Se requiere una lista de correos completos; no se admiten comodines.')
    return result

def config():
    if SETTINGS.exists():result=json.loads(store.unprotect(SETTINGS.read_bytes()))
    else:
        source=server.DATA/'ngrok.dpapi'
        if not source.exists():raise ValueError('Falta la lista autorizada. Ejecuta AUTORIZAR_CLOUDFLARE.cmd.')
        old=json.loads(store.unprotect(source.read_bytes()))
        result={'owner_email':old.get('owner_email',old['emails'][0]),'emails':emails_valid(old['emails'])}
        store.atomic_write(SETTINGS,store.protect(json.dumps(result).encode()))
    result['emails']=emails_valid(result['emails']);return result

def change_emails():
    prepare_private_store(server.DATA)
    if SETTINGS.exists() or (server.DATA/'ngrok.dpapi').exists():current=config()
    else:
        owner=input('Tu correo completo: ').strip().lower();current={'owner_email':owner,'emails':[owner]}
    print('Correos actuales:',', '.join(current['emails']))
    print('Pega todos los correos adicionales que deban conservar acceso, separados por coma.')
    additional=input('Correos adicionales: ').split(',')
    result={**current,'emails':emails_valid([current['owner_email'],*[x.strip() for x in additional if x.strip()]])}
    store.atomic_write(SETTINGS,store.protect(json.dumps(result).encode()))
    print('Lista guardada. Reinicia Cloudflare para aplicar el cambio; el enlace también cambiará.')

def command(port,log,emails=None):
    args=[str(server.ROOT/'tools'/'cloudflared.exe'),'tunnel','--no-autoupdate','--metrics','127.0.0.1:0',
          '--url','http://127.0.0.1:'+str(port),'--logfile',str(log),'--output','json']
    if emails:args+=['--allowed-mail',','.join(emails_valid(emails))]
    return args

def find_url(path):
    if not path.exists():return None
    found=re.findall(r'https://[a-z0-9-]+\.trycloudflare\.com',path.read_text(encoding='utf-8',errors='replace'))
    return found[-1] if found else None

def run(open_browser=False):
    prepare_private_store(server.DATA)
    settings=config();pin=settings.get('email_pin',True) is not False;agents=[];servers=[];delivery=None
    record=server.DATA/'cloudflare-processes.json';process_file=server.DATA/'server-process.json'
    with store.file_lock(server.DATA/'.server.lock'):
        stop_file=server.DATA/'cloudflare-child.stop';stop_file.unlink(missing_ok=True)
        server.initialize()
        with server.db.get_connection() as c:
            ready=server.secure.publication_ready(c)
        if not ready:raise ValueError('Completa primero acceso, MFA y políticas de un administrador global en modo local.')
        # Reservar los puertos antes de publicar evita servir otra aplicación.
        console=server.ThreadingHTTPServer(('127.0.0.1',CONSOLE_PORT),server.Handler);servers.append(console)
        portal=None
        if pin:portal=server.ThreadingHTTPServer(('127.0.0.1',PASS_PORT),PassOnlyHandler);servers.append(portal)
        started=[]
        try:
            urls=[]
            specifications=[('console',CONSOLE_PORT,settings['emails'] if pin else None)]+([('passes',PASS_PORT,None)] if pin else [])
            for name,port,emails in specifications:
                log=server.DATA/('cloudflare-'+name+'.log');log.unlink(missing_ok=True)
                agent=subprocess.Popen(command(port,log,emails),cwd=server.ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                agents.append(agent)
                store.atomic_write(record,json.dumps({'launcher':os.getpid(),'agents':[a.pid for a in agents],'registered_ms':int(time.time()*1000)}).encode())
                deadline=time.monotonic()+45;url=None
                while time.monotonic()<deadline:
                    if stop_file.exists():return
                    if agent.poll() is not None:raise RuntimeError('Cloudflare no pudo iniciar '+name+'. Revisa el registro del almacén privado externo.')
                    url=find_url(log)
                    if url:break
                    time.sleep(.2)
                if not url:raise RuntimeError('Cloudflare no entregó una dirección en 45 segundos. Comprueba Internet y vuelve a iniciar.')
                urls.append(url)
            server.configure_public(urls[0]);console.trusted_proxy='cloudflare';console.public_origin=urls[0];console.pass_origin=urls[1] if pin else urls[0]
            if portal:portal.public_origin=urls[1];portal.trusted_proxy='cloudflare'
            for httpd in servers:
                threading.Thread(target=httpd.serve_forever,daemon=True).start();started.append(httpd)
            store.atomic_write(process_file,json.dumps({'pid':os.getpid(),'registered_ms':int(time.time()*1000),'provider':'cloudflare'}).encode())
            info={'console_url':urls[0],'pass_origin':console.pass_origin,'allowed_emails':len(settings['emails']) if pin else None,
                  'email_pin':pin,'authentication':'email_pin_and_app_mfa' if pin else 'app_password_totp','started_at':time.time(),'temporary':True}
            store.atomic_write(server.DATA/'cloudflare-links.json',json.dumps(info).encode())
            (server.DATA/'ENLACE_CLOUDFLARE.md').write_text('# SECURITY TEAM · Cloudflare activo\n\n'
                +'**Consola:** '+urls[0]+'\n\n'+('Correo autorizado + PIN recibido por email; después matrícula, contraseña y MFA de SECURITY TEAM.' if pin else 'Acceso con matrícula, contraseña y autenticador de SECURITY TEAM. Sin PIN de correo ni lista de correos en el túnel, por elección del propietario.')+'\n\n'
                +'Las entregas móviles caducan en cinco minutos y se canjean una vez. Los usuarios deben autenticar su propia cuenta; los invitados necesitan confirmación del anfitrión. Las APIs administrativas requieren autenticación y permisos.\n\n'
                +'El enlace cambia al reiniciar. Abre `COMPARTIR_CLOUDFLARE.cmd` para iniciar con recuperación automática y `ABRIR_CLOUDFLARE.cmd` para ver el enlace actual. '
                +'En Personas y permisos, usa «Renovar entregas móviles» para preparar enlaces privados nuevos en conjunto.\n',encoding='utf-8')
            import audit_delivery
            delivery=audit_delivery.start_worker()
            print('Consola protegida: '+urls[0],flush=True)
            print('Acceso: '+('PIN de correo + ' if pin else '')+'matrícula, contraseña y autenticador de la app.',flush=True)
            if open_browser:webbrowser.open(urls[0])
            while all(a.poll() is None for a in agents) and not stop_file.exists():time.sleep(.5)
            if stop_file.exists():return
            raise RuntimeError('Se detuvo un túnel; se cierra esta sesión compartida. Vuelve a iniciar para obtener el enlace nuevo.')
        finally:
            for agent in agents:
                if agent.poll() is None:agent.terminate();agent.wait(timeout=10)
            if delivery:delivery.set()
            for httpd in started:httpd.shutdown()
            for httpd in servers:httpd.server_close()
            server.features.camera_hub.stop_all()
            record.unlink(missing_ok=True);process_file.unlink(missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--emails',action='store_true');parser.add_argument('--open',action='store_true');args=parser.parse_args()
    try:change_emails() if args.emails else run(args.open)
    except KeyboardInterrupt:pass
    except (OSError,ValueError,RuntimeError) as error:print('Compartir detenido:',error,file=sys.stderr);sys.exit(1)
