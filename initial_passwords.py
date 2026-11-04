"""Primer ingreso individual o grupal: un uso por cuenta, 24 h y MFA obligatorio."""
import secrets
import time
import db_manager as db

LIFETIME = 24 * 60 * 60


def migrate(c):
    c.execute('''CREATE TABLE IF NOT EXISTS initial_password_grants(
        user_id INTEGER PRIMARY KEY, security_version INTEGER NOT NULL,
        expires REAL NOT NULL, used_at REAL, issued_by TEXT NOT NULL)''')
    if 'shared' not in {r[1] for r in c.execute('PRAGMA table_info(initial_password_grants)')}:
        c.execute('ALTER TABLE initial_password_grants ADD COLUMN shared INTEGER NOT NULL DEFAULT 0')


def register(c, user, issued_by, shared=False):
    """Se llama solo después de guardar un hash temporal individual nuevo."""
    if not user['is_active'] or user['is_locked'] or user['ever_enrolled'] or user['mfa_configured'] or not user['must_change_password']:
        raise ValueError('Solo se habilitan cuentas activas, desbloqueadas y sin inscripción previa.')
    expires = time.time() + LIFETIME
    c.execute('DELETE FROM activation_tickets WHERE user_id=?', (user['id'],))
    c.execute('INSERT OR REPLACE INTO initial_password_grants(user_id,security_version,expires,used_at,issued_by,shared) VALUES(?,?,?,NULL,?,?)',
              (user['id'], user['security_version'], expires, issued_by, int(shared)))
    db.write_audit(c, issued_by, 'INITIAL_PASSWORD_ISSUED', ('Contraseña grupal: un uso por cuenta, 24 horas; valor no registrado.' if shared else 'Contraseña individual: un uso, 24 horas; valor no registrado.'), user['username'])
    return expires


def issue(c, username, issued_by, *, temporary=None, shared=False):
    import security as sec
    user = c.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    if not user or not user['is_active'] or user['is_locked'] or user['ever_enrolled'] or user['mfa_configured']:
        raise ValueError('La cuenta debe estar activa, desbloqueada y sin inscripción previa. Para cuentas configuradas usa restablecer contraseña.')
    temporary = temporary if temporary is not None else secrets.token_urlsafe(18)
    c.execute('UPDATE users SET password_hash=?,must_change_password=1,security_version=security_version+1,updated_at=? WHERE id=?',
              (sec.hash_password(temporary), db._now(), user['id']))
    user = c.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
    expires = register(c, user, issued_by, shared=shared)
    return {'temporary_password': temporary, 'expires_at': expires, 'single_use': True}


def claim(c, authenticated_user, state):
    """Solo tras verificar contraseña. Consumir atómicamente evita dos inscripciones."""
    user = c.execute('SELECT * FROM users WHERE id=?', (authenticated_user['id'],)).fetchone()
    if not user or user['security_version'] != authenticated_user['security_version'] or not user['is_active'] or user['is_locked'] or user['ever_enrolled'] or user['mfa_configured']:
        raise ValueError('El acceso cambió. Inicia sesión de nuevo.')
    grant = c.execute('SELECT * FROM initial_password_grants WHERE user_id=?', (user['id'],)).fetchone()
    if not grant:
        return False
    now = time.time()
    if grant['security_version'] != user['security_version'] or grant['used_at'] is not None or grant['expires'] <= now:
        raise ValueError('Contraseña temporal usada, vencida o revocada. Solicita una nueva a la administración.')
    if grant['shared'] and group_reason(c,user):
        raise ValueError('Esta cuenta requiere una contraseña temporal individual por sus permisos actuales.')
    changed = c.execute('UPDATE initial_password_grants SET used_at=? WHERE user_id=? AND used_at IS NULL', (now, user['id'])).rowcount
    if changed != 1:
        raise ValueError('Contraseña temporal ya utilizada. Solicita una nueva.')
    state['activation'] = {'id': user['id'], 'sv': user['security_version'], 'expires': now + 300}
    db.write_audit(c, user['username'], 'INITIAL_PASSWORD_CLAIMED', 'Primer ingreso autorizado; contraseña privada y MFA pendientes.', user['username'])
    return True


def group_reason(c, user):
    """El modo común nunca permite estrenar una identidad privilegiada."""
    if not user['is_active']:return 'Cuenta inactiva.'
    if user['is_locked']:return 'Cuenta bloqueada: verificar al titular y desbloquear primero.'
    if user['ever_enrolled'] or user['mfa_configured']:return 'La cuenta ya configuró su acceso.'
    privileged = user['role'] != 'user' or bool(user['is_guard']) or c.execute(
        "SELECT 1 FROM user_licenses WHERE matricula=? AND license_id IN ('LIC-CCTV-ADMIN','LIC-DC-VAULT','LIC-SRV-CRIT')",(user['username'],)).fetchone()
    if privileged:return 'Acceso privilegiado: usar contraseña temporal individual.'
    return ''


def issue_group(c, issued_by):
    actor=c.execute('SELECT * FROM users WHERE username=?',(issued_by,)).fetchone()
    if not actor or actor['role'] not in db.GLOBAL_ROLES or not actor['is_active'] or actor['is_locked']:
        raise PermissionError('Solo administración global habilita el ingreso grupal.')
    pending=c.execute('SELECT * FROM users WHERE ever_enrolled=0 AND mfa_configured=0 ORDER BY username').fetchall()
    eligible=[];skipped=[]
    for user in pending:
        reason=group_reason(c,user)
        if reason:skipped.append({'matricula':user['username'],'full_name':user['full_name'],'reason':reason})
        else:eligible.append(user)
    if not eligible:raise ValueError('No hay cuentas pendientes elegibles para la contraseña común.')
    temporary='Aula-'+secrets.token_urlsafe(9)+'!'
    expires=[]
    for user in eligible:
        expires.append(issue(c,user['username'],issued_by,temporary=temporary,shared=True)['expires_at'])
    db.write_audit(c,issued_by,'INITIAL_GROUP_PASSWORD_ISSUED',str(len(eligible))+' cuentas; un uso por cuenta; 24 horas; cambio y MFA obligatorios; valor no registrado.')
    return {'temporary_password':temporary,'expires_at':min(expires),'single_use_per_account':True,
            'issued':[{'matricula':u['username'],'full_name':u['full_name']} for u in eligible],'skipped':skipped}
