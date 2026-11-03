"""Primer ingreso con contraseña individual: un uso, 24 h y sesión ligada a la cuenta."""
import secrets
import time
import db_manager as db

LIFETIME = 24 * 60 * 60


def migrate(c):
    c.execute('''CREATE TABLE IF NOT EXISTS initial_password_grants(
        user_id INTEGER PRIMARY KEY, security_version INTEGER NOT NULL,
        expires REAL NOT NULL, used_at REAL, issued_by TEXT NOT NULL)''')


def register(c, user, issued_by):
    """Se llama solo después de guardar un hash temporal individual nuevo."""
    if not user['is_active'] or user['is_locked'] or user['ever_enrolled'] or user['mfa_configured'] or not user['must_change_password']:
        raise ValueError('Solo se habilitan cuentas activas, desbloqueadas y sin inscripción previa.')
    expires = time.time() + LIFETIME
    c.execute('DELETE FROM activation_tickets WHERE user_id=?', (user['id'],))
    c.execute('INSERT OR REPLACE INTO initial_password_grants VALUES(?,?,?,NULL,?)',
              (user['id'], user['security_version'], expires, issued_by))
    db.write_audit(c, issued_by, 'INITIAL_PASSWORD_ISSUED', 'Contraseña individual: un uso, 24 horas; valor no registrado.', user['username'])
    return expires


def issue(c, username, issued_by):
    import security as sec
    user = c.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
    if not user or not user['is_active'] or user['is_locked'] or user['ever_enrolled'] or user['mfa_configured']:
        raise ValueError('La cuenta debe estar activa, desbloqueada y sin inscripción previa. Para cuentas configuradas usa restablecer contraseña.')
    temporary = secrets.token_urlsafe(18)
    c.execute('UPDATE users SET password_hash=?,must_change_password=1,security_version=security_version+1,updated_at=? WHERE id=?',
              (sec.hash_password(temporary), db._now(), user['id']))
    user = c.execute('SELECT * FROM users WHERE id=?', (user['id'],)).fetchone()
    expires = register(c, user, issued_by)
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
    changed = c.execute('UPDATE initial_password_grants SET used_at=? WHERE user_id=? AND used_at IS NULL', (now, user['id'])).rowcount
    if changed != 1:
        raise ValueError('Contraseña temporal ya utilizada. Solicita una nueva.')
    state['activation'] = {'id': user['id'], 'sv': user['security_version'], 'expires': now + 300}
    db.write_audit(c, user['username'], 'INITIAL_PASSWORD_CLAIMED', 'Primer ingreso autorizado; contraseña privada y MFA pendientes.', user['username'])
    return True
