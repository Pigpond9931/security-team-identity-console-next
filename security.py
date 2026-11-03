"""Núcleo de identidad de la consola local.

Las sesiones y retos son estado exclusivo del servidor, nunca datos de
autorización enviados por el navegador. El servidor ejecuta las migraciones
explícitamente y cifra los secretos TOTP con una clave local separada.
"""
import binascii
import os
from pathlib import Path
from cryptography.fernet import Fernet, MultiFernet, InvalidToken
import hashlib
import json
import windows_store as store
import re
import secrets
import time
from contextlib import contextmanager

import bcrypt
import pyotp
import db_manager as db

PUBLIC_COLUMNS = ('id', 'username', 'full_name', 'role', 'area', 'is_guard',
                  'mfa_configured', 'rfid_uid', 'rfid_aliases', 'failed_attempts', 'is_locked',
                  'is_active', 'created_at', 'updated_at', 'last_login',
                  'security_version', 'must_change_password', 'terms_accepted', 'terms_accepted_at', 'terms_version', 'allowed_zones')
SESSION_SECONDS = 1800
CHALLENGE_SECONDS = 300
MAX_FAILURES = 3

def cipher():
    key_path=Path(os.environ.get('ST_KEY_PATH',str(Path(__file__).parent/'data'/'.mfa-key')))
    key_path.parent.mkdir(parents=True,exist_ok=True)
    with store.file_lock(key_path.parent/'.key.lock',wait=True):
        if not key_path.exists():
            with db.get_connection() as conn:
                if conn.execute("SELECT 1 FROM users WHERE mfa_secret LIKE 'fernet:%' LIMIT 1").fetchone():
                    raise RuntimeError('Falta la clave de la base. Restaura el respaldo completo; no se generó una clave sustituta.')
            keys=[Fernet.generate_key().decode('ascii')]
            store.atomic_write(key_path,store.protect(json.dumps({'v':1,'keys':keys}).encode()))
        data=key_path.read_bytes()
        if data.startswith(store.PREFIX):
            decoded=store.unprotect(data)
            ring=json.loads(decoded)
            keys=ring['keys']
        else:
            # Migración de la clave antigua: conserva la clave y los factores.
            Fernet(data)
            keys=[data.decode('ascii')]
            store.atomic_write(key_path,store.protect(json.dumps({'v':1,'keys':keys}).encode()))
        return MultiFernet([Fernet(key.encode('ascii')) for key in keys])

def rotate_key():
    """Usar solo bajo .server.lock, con el servidor detenido. Recuperable tras fallo."""
    key_path=Path(os.environ['ST_KEY_PATH'])
    cipher()
    with store.file_lock(key_path.parent/'.key.lock',wait=True):
        ring=json.loads(store.unprotect(key_path.read_bytes()))
        keys=[Fernet.generate_key().decode('ascii'),*ring['keys']]
        store.atomic_write(key_path,store.protect(json.dumps({'v':1,'keys':keys}).encode()))
        multi=MultiFernet([Fernet(k.encode('ascii')) for k in keys])
        with write_transaction() as conn:
            for row in conn.execute('SELECT id,mfa_secret FROM users WHERE mfa_secret IS NOT NULL'):
                value=row['mfa_secret']
                plain=multi.decrypt(value[7:].encode('ascii')) if value.startswith('fernet:') else value.encode('ascii')
                conn.execute('UPDATE users SET mfa_secret=? WHERE id=?',('fernet:'+multi.encrypt(plain).decode('ascii'),row['id']))
            db.write_audit(conn,'operador_windows','MFA_KEY_ROTATED','Rotación local de custodia')
        # Si hay una caída antes de este paso, ambas claves permiten continuar.
        store.atomic_write(key_path,store.protect(json.dumps({'v':1,'keys':keys[:1]}).encode()))

def encrypt_secret(secret):
    return 'fernet:'+cipher().encrypt(secret.encode('ascii')).decode('ascii')

def decrypt_secret(secret):
    if not secret: return None
    if not secret.startswith('fernet:'): return secret
    try: return cipher().decrypt(secret[7:].encode('ascii')).decode('ascii')
    except (InvalidToken,ValueError,UnicodeError): return None

def encrypt_existing_secrets():
    encryptor=cipher()
    with write_transaction() as conn:
        for row in conn.execute('SELECT id,mfa_secret FROM users WHERE mfa_secret IS NOT NULL').fetchall():
            if not row['mfa_secret'].startswith('fernet:'):
                conn.execute('UPDATE users SET mfa_secret=? WHERE id=?',('fernet:'+encryptor.encrypt(row['mfa_secret'].encode('ascii')).decode('ascii'),row['id']))
            else:
                encryptor.decrypt(row['mfa_secret'][7:].encode('ascii'))

def public_user(row):
    return {key: row[key] for key in PUBLIC_COLUMNS}

@contextmanager
def write_transaction():
    with db.get_connection() as conn:
        conn.execute('BEGIN IMMEDIATE')
        yield conn

def migrate():
    """Migración idempotente; versionar formalmente antes del despliegue."""
    with write_transaction() as conn:
        columns = {r['name'] for r in conn.execute('PRAGMA table_info(users)')}
        for name, declaration in (
            ('security_version', 'INTEGER NOT NULL DEFAULT 0'),
            ('last_totp_step', 'INTEGER NOT NULL DEFAULT -1'),
            ('must_change_password', 'INTEGER NOT NULL DEFAULT 1'),
            ('ever_enrolled', 'INTEGER NOT NULL DEFAULT 0'),
            ('mfa_reset_pending', 'INTEGER NOT NULL DEFAULT 0'),
        ):
            if name not in columns:
                # Los identificadores proceden de esta lista cerrada.
                conn.execute(f'ALTER TABLE users ADD COLUMN {name} {declaration}')
        conn.execute('UPDATE users SET ever_enrolled=1 WHERE mfa_configured=1 OR is_active=0')
        conn.execute('''CREATE TABLE IF NOT EXISTS recovery_codes(
            user_id INTEGER NOT NULL REFERENCES users(id),code_hash TEXT NOT NULL,
            PRIMARY KEY(user_id,code_hash))''')
        conn.execute('''CREATE TABLE IF NOT EXISTS audit_outbox(
            audit_id INTEGER PRIMARY KEY REFERENCES audit_log(id),delivered_at TEXT,
            attempts INTEGER NOT NULL DEFAULT 0,last_error TEXT)''')
        conn.execute('''CREATE TRIGGER IF NOT EXISTS trg_audit_outbox AFTER INSERT ON audit_log
            BEGIN INSERT INTO audit_outbox(audit_id) VALUES(NEW.id); END''')
        conn.execute('INSERT OR IGNORE INTO audit_outbox(audit_id) SELECT id FROM audit_log')
        conn.execute('''CREATE TRIGGER IF NOT EXISTS trg_audit_no_replace
                        BEFORE INSERT ON audit_log
                        WHEN EXISTS(SELECT 1 FROM audit_log WHERE id=NEW.id)
                        BEGIN SELECT RAISE(ABORT,'Reemplazo de auditoria prohibido'); END''')

def hash_password(password):
    if not isinstance(password,str):raise ValueError('Contraseña inválida.')
    raw = password.encode('utf-8')
    if len(password or '') < 10 or len(raw) > 72:
        raise ValueError('Usa al menos 10 caracteres y como máximo 72 bytes UTF-8.')
    return bcrypt.hashpw(raw, bcrypt.gensalt()).decode('ascii')

def verify_password(password, stored):
    if not isinstance(password,str):return False
    raw = password.encode('utf-8')
    if len(raw) > 72 or not stored:
        return False
    try:
        return bcrypt.checkpw(raw, stored.encode('ascii'))
    except (ValueError, TypeError, UnicodeError):
        return False

# Mantener un costo semejante para usuarios inexistentes o con clave incorrecta.
DUMMY_HASH = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode('ascii')

def fail(conn, user, action):
    conn.execute('''UPDATE users SET failed_attempts=failed_attempts+1,
                    is_locked=CASE WHEN failed_attempts+1 >= ? THEN 1 ELSE is_locked END,
                    security_version=security_version+
                        CASE WHEN failed_attempts+1 >= ? AND is_locked=0 THEN 1 ELSE 0 END
                    WHERE id=?''', (MAX_FAILURES, MAX_FAILURES, user['id']))
    db.write_audit(conn, user['username'], action, 'Verificación fallida', user['username'])

def authenticate(username, password):
    """Paso 1. No cuenta como acceso; no retorna secreto/hash a la UI."""
    if not isinstance(username,str) or not isinstance(password,str) or len(username)>80 or len(password.encode('utf-8'))>72:raise ValueError('Matrícula o contraseña inválida.')
    username = username.strip()
    with db.get_connection() as conn:
        before = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    valid = verify_password(password, before['password_hash'] if before else DUMMY_HASH)
    with write_transaction() as conn:
        user = conn.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        if (not user or not before or not user['is_active'] or user['is_locked']
                or user['password_hash'] != before['password_hash']
                or user['security_version'] != before['security_version']):
            db.write_audit(conn, username, 'AUTH_DENIED', 'Credenciales inválidas')
            return {'status': 'invalid'}
        if not valid:
            fail(conn, user, 'PASSWORD_FAIL')
            return {'status': 'invalid'}
        db.write_audit(conn, username, 'PASSWORD_VERIFIED', 'Pendiente de segundo factor')
        return {'status': 'ok', 'user': public_user(user), 'challenge': {
            'user_id': user['id'], 'security_version': user['security_version'],
            'issued_at': time.time(), 'mfa_configured': bool(user['mfa_configured'])}}

def challenge_user(conn, challenge):
    if not challenge or not 0 <= time.time()-challenge.get('issued_at', 0) <= CHALLENGE_SECONDS:
        return None
    user = conn.execute('SELECT * FROM users WHERE id=?', (challenge['user_id'],)).fetchone()
    if (not user or not user['is_active'] or user['is_locked']
            or user['security_version'] != challenge['security_version']
            or bool(user['mfa_configured']) != challenge['mfa_configured']):
        return None
    return user

def change_initial_password(challenge, new_password):
    """Prepara el cambio en memoria; solo finish_mfa lo persiste tras OTP."""
    hashed = hash_password(new_password)
    with write_transaction() as conn:
        user = challenge_user(conn, challenge)
        if not user or not user['must_change_password']:
            return None
        if verify_password(new_password,user['password_hash']):
            raise ValueError('Elige una contraseña diferente de la temporal.')
        return dict(challenge, new_password_hash=hashed)

def accepted_step(secret, code, now=None):
    """Devuelve el paso real que coincidió, incluida la ventana ±1."""
    if not isinstance(code,str) or not re.fullmatch(r'[0-9]{6}',code):
        return None
    try:
        otp = pyotp.TOTP(secret)
        step = int(time.time() if now is None else now) // otp.interval
        for candidate in (step, step-1, step+1):
            if secrets.compare_digest(otp.at(candidate*otp.interval), code):
                return candidate
    except (ValueError, TypeError, binascii.Error):
        pass
    return None

def finish_mfa(challenge, code, enrollment_secret=None):
    """Validación, consumo del código, enrolamiento y auditoría atómicos."""
    with write_transaction() as conn:
        user = challenge_user(conn, challenge)
        if not user:
            return None
        changing_password = bool(user['must_change_password'])
        if changing_password and not challenge.get('new_password_hash'):
            return None
        enrolling = not user['mfa_configured']
        if user['mfa_reset_pending'] or (enrolling and user['ever_enrolled']):
            return None  # Recuperación con prueba independiente obligatoria.
        # El secreto de alta es efímero, generado y conservado en el servidor.
        if enrolling and not enrollment_secret:
            return None
        secret = enrollment_secret if enrolling else decrypt_secret(user['mfa_secret'])
        step = accepted_step(secret, code)
        if step is None or step <= user['last_totp_step']:
            fail(conn, user, 'MFA_FAIL')
            return None
        conn.execute('''UPDATE users SET mfa_secret=?,mfa_configured=1,last_totp_step=?,
                        failed_attempts=0,last_login=?,updated_at=?,
                        password_hash=?,must_change_password=0,
                        ever_enrolled=1,security_version=security_version+? WHERE id=?''',
                     (encrypt_secret(secret), step, db._now(), db._now(),
                      challenge['new_password_hash'] if changing_password else user['password_hash'],
                      int(enrolling or changing_password), user['id']))
        if changing_password:
            db.write_audit(conn, user['username'], 'PASSWORD_CHANGED', 'Cambio obligatorio')
        if enrolling:
            db.write_audit(conn, user['username'], 'MFA_ENROLLED', target=user['username'])
        db.write_audit(conn, user['username'], 'AUTH_SUCCESS', 'MFA completo', user['username'])
        fresh = conn.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
        auth={'user_id': user['id'], 'security_version': fresh['security_version'], 'issued_at': time.time()}
        if enrolling or not conn.execute('SELECT 1 FROM recovery_codes WHERE user_id=?',(user['id'],)).fetchone():
            auth['recovery_codes']=issue_recovery_codes(conn,user['id'])
        return auth

def code_digest(code):
    normalized=re.sub(r'[\s-]','',str(code or '')).upper()
    return hashlib.sha256(normalized.encode('utf-8')).hexdigest()

def issue_recovery_codes(conn,user_id):
    codes=['-'.join([secrets.token_hex(4).upper() for _ in range(4)]) for _ in range(8)]
    conn.execute('DELETE FROM recovery_codes WHERE user_id=?',(user_id,))
    conn.executemany('INSERT INTO recovery_codes(user_id,code_hash) VALUES(?,?)',[(user_id,code_digest(c)) for c in codes])
    db.write_audit(conn,None,'RECOVERY_CODES_ISSUED',target=str(user_id))
    return codes

def recover_mfa(challenge,code,method='recovery'):
    """El administrador no puede generar ni consultar la prueba del titular."""
    if method not in ('totp','recovery'):raise ValueError('Método de recuperación inválido.')
    with write_transaction() as conn:
        user=challenge_user(conn,challenge)
        if not user or not user['ever_enrolled']:return None
        if method=='totp' and user['mfa_configured']:
            step=accepted_step(decrypt_secret(user['mfa_secret']),code)
            valid=step is not None and step>user['last_totp_step']
        else:
            digest=code_digest(code)
            valid=conn.execute('SELECT 1 FROM recovery_codes WHERE user_id=? AND code_hash=?',(user['id'],digest)).fetchone() is not None
        if not valid:fail(conn,user,'RECOVERY_FAIL');return None
        if method!='totp':conn.execute('DELETE FROM recovery_codes WHERE user_id=? AND code_hash=?',(user['id'],digest))
        conn.execute('''UPDATE users SET mfa_secret=NULL,mfa_configured=0,mfa_reset_pending=0,
            ever_enrolled=0,last_totp_step=-1,security_version=security_version+1 WHERE id=?''',(user['id'],))
        db.write_audit(conn,user['username'],'RECOVERY_VERIFIED','Prueba privada del titular',user['username'])
        return dict(challenge,security_version=user['security_version']+1,mfa_configured=False)

def regenerate_recovery_codes(session,password,code):
    with write_transaction() as conn:
        user=session_user(conn,session)
        if not user:raise PermissionError('La sesión caducó.')
        step=accepted_step(decrypt_secret(user['mfa_secret']),code)
        if not verify_password(password,user['password_hash']) or step is None or step<=user['last_totp_step']:
            fail(conn,user,'RECOVERY_CODES_FAIL');return None
        conn.execute('UPDATE users SET last_totp_step=?,security_version=security_version+1 WHERE id=?',(step,user['id']))
        return {'user_id':user['id'],'security_version':user['security_version']+1,'issued_at':time.time(),
                'recovery_codes':issue_recovery_codes(conn,user['id'])}

def session_user(conn, session):
    if not session or not 0 <= time.time()-session.get('issued_at', 0) <= SESSION_SECONDS:
        return None
    user = conn.execute('SELECT * FROM users WHERE id=?', (session['user_id'],)).fetchone()
    if (not user or not user['is_active'] or user['is_locked'] or not user['mfa_configured']
            or user['must_change_password'] or user['security_version'] != session['security_version']):
        return None
    return user

def current_user(session):
    with db.get_connection() as conn:
        user = session_user(conn, session)
        return public_user(user) if user else None

def require_manager(conn, session, target_id):
    actor = session_user(conn, session)
    target = conn.execute('SELECT * FROM users WHERE id=?', (target_id,)).fetchone()
    if not actor or not target or actor['id'] == target_id:
        raise PermissionError('Operación no autorizada.')
    if actor['role'] == db.ROLE_SYSTEM_ADMIN:
        return actor, target
    if actor['role'] == db.ROLE_DPO and target['role'] != db.ROLE_SYSTEM_ADMIN:
        return actor, target
    if (actor['role'] == db.ROLE_AREA_ADMIN and actor['area'] is not None
            and actor['area'] == target['area'] and target['role'] == db.ROLE_USER):
        return actor, target
    raise PermissionError('Operación no autorizada.')

def update_user(session, target_id, **changes):
    """Perfil, rol, área, RFID, bloqueo y baja con alcance vigente."""
    allowed = {'username','full_name','role','area','is_guard','is_active','rfid_uid','is_locked'}
    if not changes or not set(changes) <= allowed:
        raise ValueError('Campos no permitidos.')
    with write_transaction() as conn:
        actor, target = require_manager(conn, session, target_id)
        if actor['role'] not in db.GLOBAL_ROLES and set(changes) & {'role','area','is_guard'}:
            raise PermissionError('Solo la administración global cambia permisos o área.')
        if changes.get('role') == db.ROLE_SYSTEM_ADMIN and actor['role'] != db.ROLE_SYSTEM_ADMIN:
            raise PermissionError('Solo un administrador del sistema asigna ese rol.')
        if 'role' in changes and changes['role'] not in db.ROLE_LABELS:
            raise ValueError('Rol inválido.')
        if 'area' in changes and changes['area'] is not None and changes['area'] not in db.AREAS:
            raise ValueError('Área inválida.')
        for key in ('is_guard','is_active','is_locked'):
            if key in changes and changes[key] not in (0,1):
                raise ValueError('Estado inválido.')
        role=changes.get('role',target['role']);area=changes.get('area',target['area'])
        if role not in db.GLOBAL_ROLES and area not in db.AREAS:raise ValueError('El usuario debe tener área.')
        if role in db.GLOBAL_ROLES:changes['area']=None
        if target['role'] in db.GLOBAL_ROLES and (role!=target['role'] or changes.get('is_active')==0 or changes.get('is_locked')==1):
            count=conn.execute('SELECT COUNT(*) FROM users WHERE role=? AND is_active=1 AND is_locked=0 AND id<>?',(target['role'],target_id)).fetchone()[0]
            if not count:raise PermissionError('Debe permanecer una cuenta activa y desbloqueada del rol '+db.ROLE_LABELS[target['role']]+'.')
        for key in ('username','full_name'):
            if key in changes:
                changes[key] = str(changes[key]).strip()
                if not changes[key]: raise ValueError('Datos obligatorios vacíos.')
        if 'rfid_uid' in changes:
            changes['rfid_uid'] = (changes['rfid_uid'] or '').strip() or None
            if changes['rfid_uid']:
                import features
                normalized=features.normalize_rfid(changes['rfid_uid'])
                import rfid_cards
                if rfid_cards.owners(conn, normalized, exclude_id=target_id):
                    raise ValueError('UID ya vinculado a otra identidad.')
        if set(changes)&{'role','area'}:
            changes['allowed_zones']=json.dumps(db.default_zones(role,area,changes.get('is_guard',target['is_guard'])))
        if changes.get('is_active') == 0:
            changes.update(mfa_secret=None,mfa_configured=0,rfid_uid=None,last_totp_step=-1,mfa_reset_pending=int(bool(target['ever_enrolled'])))
        if changes.get('is_locked') == 0:
            changes['failed_attempts'] = 0
        # Los nombres vienen exclusivamente de las listas anteriores.
        fields = ','.join(f'{name}=?' for name in changes)
        conn.execute(f'UPDATE users SET {fields},security_version=security_version+1,updated_at=? WHERE id=?',
                     (*changes.values(), db._now(), target_id))
        db.write_audit(conn, actor['username'], 'USER_UPDATED',
                       'Campos: '+','.join(changes), target['username'])

def reset_mfa(session, target_id):
    with write_transaction() as conn:
        actor, target = require_manager(conn, session, target_id)
        if not target['ever_enrolled']:raise ValueError('Esta persona aún no ha configurado MFA.')
        conn.execute('''UPDATE users SET mfa_reset_pending=1,
                        security_version=security_version+1,updated_at=? WHERE id=?''',
                     (db._now(), target_id))
        db.write_audit(conn, actor['username'], 'MFA_RESET', target=target['username'])

def reset_password(session, target_id):
    temporary = secrets.token_urlsafe(24)
    hashed = hash_password(temporary)
    with write_transaction() as conn:
        actor, target = require_manager(conn, session, target_id)
        conn.execute('''UPDATE users SET password_hash=?,must_change_password=1,
                        security_version=security_version+1,updated_at=? WHERE id=?''',
                     (hashed,db._now(),target_id))
        if not target['ever_enrolled'] and not target['mfa_configured'] and target['is_active'] and not target['is_locked']:
            import initial_passwords
            fresh=conn.execute('SELECT * FROM users WHERE id=?',(target_id,)).fetchone()
            initial_passwords.register(conn,fresh,actor['username'])
        db.write_audit(conn, actor['username'], 'PASSWORD_RESET', target=target['username'])
    return temporary  # Entrega privada única; nunca registrar en auditoría.

def create_user(session, username, full_name, role, area, is_guard=0):
    if role not in db.ROLE_LABELS or area not in [None]+db.AREAS or is_guard not in (0,1):
        raise ValueError('Rol, área o estado inválidos.')
    username, full_name = str(username or '').strip(), str(full_name or '').strip()
    if not username or not full_name:
        raise ValueError('Matrícula y nombre son obligatorios.')
    if role not in db.GLOBAL_ROLES and area is None:
        raise ValueError('El usuario debe tener área.')
    if role in db.GLOBAL_ROLES:area=None
    temporary = secrets.token_urlsafe(24)
    hashed = hash_password(temporary)
    with write_transaction() as conn:
        actor = session_user(conn, session)
        if not actor or actor['role'] not in db.GLOBAL_ROLES:
            raise PermissionError('Solo la administración global crea usuarios.')
        if role == db.ROLE_SYSTEM_ADMIN and actor['role'] != db.ROLE_SYSTEM_ADMIN:
            raise PermissionError('Solo un administrador del sistema asigna ese rol.')
        conn.execute('''INSERT INTO users(username,full_name,role,area,is_guard,password_hash,
                        mfa_configured,is_active,created_at,must_change_password)
                        VALUES(?,?,?,?,?,?,0,1,?,1)''',
                     (username,full_name,role,area,is_guard,hashed,db._now()))
        conn.execute('UPDATE users SET allowed_zones=? WHERE username=?',(json.dumps(db.default_zones(role,area,is_guard)),username))
        import initial_passwords
        initial_passwords.register(conn,conn.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone(),actor['username'])
        db.write_audit(conn,actor['username'],'USER_CREATED',target=username)
    return temporary

def list_users(session):
    with db.get_connection() as conn:
        actor = session_user(conn, session)
        if not actor or actor['role'] not in (*db.GLOBAL_ROLES, db.ROLE_AREA_ADMIN):
            raise PermissionError('Operación no autorizada.')
        columns = ','.join(PUBLIC_COLUMNS)
        if actor['role'] in db.GLOBAL_ROLES:
            rows = conn.execute(f'SELECT {columns} FROM users ORDER BY id').fetchall()
        else:
            rows = conn.execute(f'SELECT {columns} FROM users WHERE area=? AND role=? ORDER BY id',
                                (actor['area'],db.ROLE_USER)).fetchall()
        return [dict(row) for row in rows]

def accesses_today():
    # Usa la misma zona horaria del servidor que el resto de la aplicación.
    with db.get_connection() as conn:
        return conn.execute('''SELECT COUNT(*) FROM audit_log
                               WHERE action='AUTH_SUCCESS' AND timestamp LIKE ?''',
                            (db._today_prefix()+'%',)).fetchone()[0]

def dashboard_data(session):
    """Autorización y lecturas comparten la misma instantánea SQLite."""
    with db.get_connection() as conn:
        conn.execute('BEGIN')
        user=session_user(conn,session)
        if not user:return None
        columns=','.join(PUBLIC_COLUMNS)
        admin=user['role'] in (*db.GLOBAL_ROLES,db.ROLE_AREA_ADMIN)
        if user['role'] in db.GLOBAL_ROLES:
            users=[dict(r) for r in conn.execute(f'SELECT {columns} FROM users ORDER BY id')]
            logs=conn.execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 250').fetchall()
        elif user['role']==db.ROLE_AREA_ADMIN:
            users=[dict(r) for r in conn.execute(f'SELECT {columns} FROM users WHERE area=? AND role=? ORDER BY id',(user['area'],db.ROLE_USER))]
            logs=conn.execute('''SELECT a.* FROM audit_log a WHERE
                a.actor IN(SELECT username FROM users WHERE area=?) OR
                a.target IN(SELECT username FROM users WHERE area=?) ORDER BY a.id DESC LIMIT 250''',(user['area'],user['area'])).fetchall()
        else:
            users=[public_user(user)]
            logs=conn.execute('''SELECT id,timestamp,actor,action,target,'Evento de monitoreo' AS details FROM audit_log
                WHERE action IN('AUTH_SUCCESS','MFA_FAIL','PASSWORD_FAIL','ACCOUNT_LOCKED','ACCOUNT_LOCKED_MANUAL')
                ORDER BY id DESC LIMIT 250''').fetchall() if user['is_guard'] else []
        params=[db._today_prefix()+'%'];scope=''
        if user['role']==db.ROLE_AREA_ADMIN:
            scope=' AND (actor IN(SELECT username FROM users WHERE area=?) OR target IN(SELECT username FROM users WHERE area=?))'
            params.extend([user['area'],user['area']])
        elif not admin and not user['is_guard']:scope=' AND actor=?';params.append(user['username'])
        accesses=conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='AUTH_SUCCESS' AND timestamp LIKE ?"+scope,params).fetchone()[0]
        return {'users':users,'audit':[dict(r) for r in logs],'accesses_today':accesses,'updated_at':db._now()}

def change_password(session,current,new,code):
    hashed=hash_password(new)
    with write_transaction() as conn:
        user=session_user(conn,session)
        if not user: raise PermissionError('La sesión caducó.')
        step=accepted_step(decrypt_secret(user['mfa_secret']),code)
        if not verify_password(current,user['password_hash']) or step is None or step<=user['last_totp_step']:
            fail(conn,user,'PASSWORD_CHANGE_FAIL')
            return False
        conn.execute('UPDATE users SET password_hash=?,last_totp_step=?,security_version=security_version+1,updated_at=? WHERE id=?',
                     (hashed,step,db._now(),user['id']))
        db.write_audit(conn,user['username'],'PASSWORD_CHANGED','Cambio propio con MFA',user['username'])
        return True
