"""Entrega opcional, firmada e idempotente a un receptor HTTPS independiente."""
import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import threading
import urllib.error
import urllib.request
from urllib.parse import urlsplit
import db_manager as db
import windows_store as store

def config_path():return Path(os.environ['ST_KEY_PATH']).parent/'audit.dpapi'

def configure(url,token):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password or parsed.fragment or parsed.query:
        raise ValueError('Usa una URL HTTPS sin credenciales, consulta ni fragmento.')
    if len(token)<32:raise ValueError('La clave compartida debe tener al menos 32 caracteres.')
    previous=load_config()
    value={'url':url,'token':token,'instance_id':previous['instance_id'] if previous else secrets.token_hex(16)}
    store.atomic_write(config_path(),store.protect(json.dumps(value).encode()))

def load_config():
    path=config_path()
    return json.loads(store.unprotect(path.read_bytes())) if path.exists() else None

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):raise urllib.error.HTTPError(args[0].full_url,args[2],'Redirección de auditoría rechazada',args[4],None)

def deliver_once():
    config=load_config()
    if not config:return False
    with db.get_connection() as conn:
        row=conn.execute('''SELECT a.* FROM audit_log a JOIN audit_outbox o ON o.audit_id=a.id
            WHERE o.delivered_at IS NULL ORDER BY a.id LIMIT 1''').fetchone()
    if not row:return False
    event=dict(row);event_id=f"{config['instance_id']}:{event['id']}"
    payload=json.dumps({'event_id':event_id,'event':event},ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()
    signature=hmac.new(config['token'].encode(),payload,hashlib.sha256).hexdigest()
    request=urllib.request.Request(config['url'],data=payload,headers={'Content-Type':'application/json',
        'X-ST-Signature':'sha256='+signature,'Idempotency-Key':event_id},method='POST')
    error=None
    try:
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        with opener.open(request,timeout=8) as response:
            if not 200<=response.status<300 or json.loads(response.read(4096)).get('event_id')!=event_id:
                raise ValueError('Confirmación de recepción inválida')
    except (OSError,ValueError,urllib.error.URLError):error='Entrega pendiente: receptor no confirmó el evento'
    with db.get_connection() as conn:
        conn.execute('UPDATE audit_outbox SET attempts=attempts+1,last_error=?,delivered_at=? WHERE audit_id=?',
                     (error,None if error else db._now(),row['id']))
    return error is None

def start_worker():
    if not config_path().exists():return None
    stop=threading.Event()
    def run():
        while not stop.is_set():
            try:more=deliver_once()
            except (OSError,ValueError,RuntimeError):more=False
            stop.wait(.2 if more else 30)
    threading.Thread(target=run,name='audit-https',daemon=True).start()
    return stop
