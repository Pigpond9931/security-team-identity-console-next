"""Controles de transporte, límites y autorizaciones efímeras, sin secretos en logs."""
import hashlib,ipaddress,json,secrets,time
import db_manager as db

CSP="default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data: blob:; media-src 'self' blob:; font-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"

def digest(value):
    if not isinstance(value,str) or not 20<=len(value)<=2048:raise ValueError('Enlace inválido o vencido.')
    return hashlib.sha256(value.encode()).hexdigest()

def migrate(c):
    import initial_passwords
    initial_passwords.migrate(c)
    c.execute('CREATE TABLE IF NOT EXISTS security_meta(key TEXT PRIMARY KEY,value TEXT NOT NULL)')
    c.execute('''CREATE TABLE IF NOT EXISTS camera_destinations(url TEXT PRIMARY KEY,status TEXT NOT NULL,
        requested_by TEXT,approved_by TEXT,updated_at TEXT NOT NULL)''')
    c.execute('''CREATE TABLE IF NOT EXISTS activation_tickets(hash TEXT PRIMARY KEY,user_id INTEGER,
        security_version INTEGER,expires REAL,used_at REAL,issued_by TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pass_receipts(hash TEXT PRIMARY KEY,id TEXT UNIQUE,sid_hash TEXT,
        subject_type TEXT,subject_id TEXT,security_version INTEGER,expires REAL,status TEXT,
        confirmation TEXT,delivery_hash TEXT)''')
    columns={r[1] for r in c.execute('PRAGMA table_info(mobile_passes)')}
    if 'used_at' not in columns:c.execute('ALTER TABLE mobile_passes ADD COLUMN used_at REAL')
    if not c.execute("SELECT 1 FROM security_meta WHERE key='hardening_140'").fetchone():
        import features as f
        for ch in c.execute('SELECT url FROM camera_channels').fetchall():
            f.camera_url(ch['url'])
            c.execute("INSERT OR IGNORE INTO camera_destinations VALUES(?,'approved','migracion','operador_windows',?)",(ch['url'],db._now()))
        # Retira enlaces de entrega antiguos; conserva gafetes y factores ya emitidos.
        retired=c.execute('SELECT COUNT(*) FROM mobile_passes').fetchone()[0]
        c.execute('DELETE FROM mobile_passes')
        db.write_audit(c,'operador_windows','DELIVERY_LINKS_REVOKED_ON_UPGRADE',str(retired)+' enlaces antiguos; gafetes y cuentas conservados')
        c.execute("INSERT INTO security_meta VALUES('hardening_140',?)",(db._now(),))

def camera_target(c,url):
    import features as f
    url=f.camera_url(url)
    if not c.execute("SELECT 1 FROM camera_destinations WHERE url=? AND status='approved'",(url,)).fetchone():
        raise PermissionError('Destino de cámara pendiente de aprobación global. Solicítalo en Destinos de cámaras IP.')
    return url

def activation_issue(c,username,issued_by):
    user=c.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
    if not user or not user['is_active'] or user['is_locked'] or user['ever_enrolled'] or user['mfa_configured']:
        raise ValueError('La activación se limita a cuentas habilitadas que aún no han registrado su autenticador.')
    token=secrets.token_urlsafe(32)
    c.execute('DELETE FROM activation_tickets WHERE user_id=? OR expires<?',(user['id'],time.time()))
    c.execute('INSERT INTO activation_tickets VALUES(?,?,?,?,NULL,?)',(digest(token),user['id'],user['security_version'],time.time()+300,issued_by))
    db.write_audit(c,issued_by,'ACTIVATION_ISSUED','Activación privada de cinco minutos',username)
    return token

def activation_claim(c,token,state):
    row=c.execute('SELECT * FROM activation_tickets WHERE hash=? AND used_at IS NULL AND expires>?',(digest(token),time.time())).fetchone()
    if not row:raise ValueError('Activación usada o vencida. Solicita otra a la administración.')
    user=c.execute('SELECT * FROM users WHERE id=?',(row['user_id'],)).fetchone()
    if not user or not user['is_active'] or user['is_locked'] or user['ever_enrolled'] or user['security_version']!=row['security_version']:
        raise ValueError('La activación ya no es válida.')
    challenge=state.get('challenge')
    if challenge and challenge['user_id']!=user['id']:raise ValueError('La activación corresponde a otra matrícula.')
    c.execute('UPDATE activation_tickets SET used_at=? WHERE hash=?',(time.time(),row['hash']))
    state['activation']={'id':user['id'],'sv':user['security_version'],'expires':time.time()+300}
    return user

def activation_valid(state,user):
    grant=state.get('activation',{})
    return bool(grant.get('id')==user['id'] and grant.get('sv')==user['security_version'] and grant.get('expires',0)>time.time())

def client_key(handler):
    # Solo el conector local configurado explícitamente puede aportar IP de Cloudflare.
    if handler.public_request() and getattr(handler.server,'trusted_proxy','')=='cloudflare' and ipaddress.ip_address(handler.client_address[0]).is_loopback:
        try:return str(ipaddress.ip_address(handler.headers.get('CF-Connecting-IP','')))
        except ValueError:pass
    return handler.client_address[0]

def rate_check(buckets,checks):
    now=time.monotonic()
    for key in list(buckets):
        if not buckets[key] or buckets[key][-1]<now-60:buckets.pop(key,None)
    if len(buckets)>4096:return False
    current=[]
    for key,limit in checks:
        values=[t for t in buckets.get(key,[]) if t>now-60]
        if len(values)>=limit:return False
        current.append((key,values))
    for key,values in current:buckets[key]=values+[now]
    return True
