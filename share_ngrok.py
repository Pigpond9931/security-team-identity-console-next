"""Comparte solo con OAuth de Google y correos explícitos; token bajo DPAPI."""
import argparse
import getpass
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request
import webbrowser
import server
import windows_store as store

SETTINGS=server.DATA/'ngrok.dpapi'

def make_policy(emails):
    if not emails or any(not re.fullmatch(r'[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}',e) for e in emails):
        raise ValueError('Especifica correos de Google válidos; no se permite una lista vacía.')
    public="(req.url.path in ['/pass','/scanner','/camera','/activate','/api/terms','/api/public-pass','/api/public-pass/preview','/api/public-pass/claim','/api/public-pass/accept-terms','/api/scanner/claim','/api/scanner/poll','/api/scanner/read','/api/scanner/disconnect','/api/browser-camera/claim','/api/browser-camera/poll','/api/browser-camera/signal','/api/browser-camera/upload','/api/browser-camera/disconnect','/favicon.svg'] || req.url.path.startsWith('/assets/'))"
    protected='!'+public
    return {'on_http_request':[
        {'expressions':[protected],'actions':[{'type':'oauth','config':{'provider':'google'}}]},
        {'expressions':[protected+' && !(actions.ngrok.oauth.identity.email in '+json.dumps(emails)+')'],
         'actions':[{'type':'deny'}]}]}

def configure():
    store.private_directory(server.DATA)
    url=input('Dominio HTTPS asignado por ngrok (ej. https://tu-dominio.ngrok-free.app): ').strip()
    server.configure_public(url)
    emails=[e.strip().lower() for e in input('Correos de Google autorizados, separados por coma: ').split(',') if e.strip()]
    make_policy(emails)
    token=getpass.getpass('Authtoken de ngrok (no se mostrará): ').strip()
    if not token or any(c.isspace() for c in token):raise ValueError('Authtoken inválido.')
    store.atomic_write(SETTINGS,store.protect(json.dumps({'url':server.PUBLIC_ORIGIN,'emails':emails,'token':token}).encode()))
    print('Configuración guardada de forma privada. Usa COMPARTIR_NGROK.cmd.')

def with_allowed_emails(config,additional):
    owner=config.get('owner_email',config['emails'][0]).lower()
    emails=list(dict.fromkeys([owner,*[email.strip().lower() for email in additional if email.strip()]]))
    make_policy(emails)
    return dict(config,owner_email=owner,emails=emails)

def change_emails():
    if not SETTINGS.exists():raise ValueError('Configura primero ngrok.')
    config=json.loads(store.unprotect(SETTINGS.read_bytes()))
    owner=config.get('owner_email',config['emails'][0])
    print('Tu correo se conserva autorizado:',owner)
    print('Correos actuales:',', '.join(config['emails']))
    print('Escribe todos los correos adicionales que quieres permitir. Deja vacío para permitir solo el tuyo.')
    additional=input('Correos de Google separados por coma: ').split(',')
    updated=with_allowed_emails(config,additional)
    store.atomic_write(SETTINGS,store.protect(json.dumps(updated).encode()))
    print('Lista guardada. Detén el túnel y vuelve a iniciarlo para aplicar el cambio.')

def run():
    if not SETTINGS.exists():raise ValueError('Crea tu cuenta y ejecuta primero CONFIGURAR_NGROK.cmd.')
    config=json.loads(store.unprotect(SETTINGS.read_bytes()))
    policy=make_policy(config['emails']);server.configure_public(config['url'])
    executable=server.ROOT/'tools'/'ngrok.exe'
    if not executable.exists():raise ValueError('Falta tools/ngrok.exe. Consulta COMPARTIR.md.')
    # No conectar el túnel hasta comprobar la protección del DPO.
    with server.db.get_connection() as conn:
        ready=conn.execute("SELECT 1 FROM users WHERE role='dpo' AND is_active=1 AND is_locked=0 AND mfa_configured=1 AND must_change_password=0 LIMIT 1").fetchone()
    if not ready:raise ValueError('Primero entra como DPO en la aplicación local y completa MFA y su configuración inicial.')
    with store.file_lock(server.DATA/'.server.lock'):pass
    policy_path=server.DATA/'ngrok-policy.json';store.atomic_write(policy_path,json.dumps(policy).encode())
    child=subprocess.Popen([sys.executable,str(server.ROOT/'server.py'),'--public-url',config['url'],'--trusted-proxy','ngrok'],cwd=server.ROOT)
    agent=None
    record=server.DATA/'share-processes.json'
    server_record=server.DATA/'server-process.json';owned_record=None
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            if child.poll() is not None:raise RuntimeError('No se pudo iniciar la aplicación para compartir.')
            try:
                with opener.open('http://127.0.0.1:8765/api/health',timeout=1) as response:
                    if json.load(response).get('application')=='SECURITY_TEAM_Studio':break
            except OSError:time.sleep(.2)
        else:raise RuntimeError('La aplicación no confirmó su arranque.')
        owned_record=server_record.read_bytes()
        env=dict(os.environ,NGROK_AUTHTOKEN=config['token'])
        agent=subprocess.Popen([str(executable),'http','127.0.0.1:8765','--url',config['url'],
                                '--traffic-policy-file',str(policy_path),'--inspect=false'],env=env,cwd=server.ROOT)
        store.atomic_write(record,json.dumps({'launcher':os.getpid(),'server':child.pid,'agent':agent.pid,
                                             'registered_ms':int(time.time()*1000)}).encode())
        print('Dirección de tu túnel:',config['url'])
        print('Requiere Google autorizado, contraseña de la aplicación y MFA. Ctrl+C cierra el túnel.')
        code=agent.wait()
        if code:raise RuntimeError('Ngrok no confirmó el túnel. Revisa su mensaje, la cuenta, el dominio y la política OAuth.')
    finally:
        if agent and agent.poll() is None:agent.terminate();agent.wait(timeout=10)
        # El ejecutable de venv en Windows puede ser un padre del servidor real.
        # Detener únicamente el registro que capturó este arranque evita huérfanos.
        if os.name=='nt' and owned_record and server_record.exists() and server_record.read_bytes()==owned_record:
            subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(server.ROOT/'DETENER.ps1')],
                           cwd=server.ROOT,timeout=15,creationflags=subprocess.CREATE_NO_WINDOW,check=False)
        if child.poll() is None:child.terminate();child.wait(timeout=10)
        record.unlink(missing_ok=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();options=parser.add_mutually_exclusive_group();options.add_argument('--configure',action='store_true');options.add_argument('--emails',action='store_true');args=parser.parse_args()
    try:configure() if args.configure else change_emails() if args.emails else run()
    except KeyboardInterrupt:pass
    except (OSError,ValueError,RuntimeError) as error:print('Compartir detenido:',error,file=sys.stderr);sys.exit(1)
