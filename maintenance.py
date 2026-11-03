"""Mantenimiento local del operador Windows. No se expone por HTTP."""
import argparse
from contextlib import closing
import getpass
import secrets
import sqlite3
import sys
from pathlib import Path
import server
import windows_store as store

def backup(destination):
    destination=Path(destination)
    if destination.exists():raise ValueError('El destino ya existe; usa una carpeta nueva.')
    store.private_directory(destination)
    with closing(sqlite3.connect(server.db.DB_PATH)) as source,closing(sqlite3.connect(destination/'identity.sqlite')) as target:source.backup(target)
    for name in ('.mfa-key','.qr-key','audit.dpapi','ngrok.dpapi','cloudflare.dpapi'):
        p=server.DATA/name
        if p.exists():store.atomic_write(destination/name,p.read_bytes())
    print('Respaldo completo protegido. Requiere el mismo usuario y equipo de Windows.')

def recover(username):
    # Esta vía requiere control del equipo y verificación humana fuera del panel.
    if not sys.stdin.isatty():raise ValueError('La recuperación del operador exige una terminal interactiva.')
    if input('Tras verificar la identidad del titular, escribe su matrícula: ').strip()!=username:
        raise ValueError('Confirmación cancelada.')
    temporary=secrets.token_urlsafe(24);hashed=server.secure.hash_password(temporary)
    with server.secure.write_transaction() as conn:
        user=conn.execute('SELECT id FROM users WHERE username=?',(username,)).fetchone()
        if not user:raise ValueError('Cuenta no encontrada.')
        conn.execute('''UPDATE users SET password_hash=?,must_change_password=1,mfa_secret=NULL,
            mfa_configured=0,ever_enrolled=0,mfa_reset_pending=0,last_totp_step=-1,
            failed_attempts=0,is_locked=0,security_version=security_version+1 WHERE id=?''',(hashed,user['id']))
        conn.execute('DELETE FROM recovery_codes WHERE user_id=?',(user['id'],))
        server.db.write_audit(conn,'operador_windows','OFFLINE_RECOVERY_APPROVED','Verificación de identidad local',username)
    import hardening
    with server.secure.write_transaction() as conn:activation=hardening.activation_issue(conn,username,'operador_windows')
    print('Credencial temporal privada (entrégala al titular):',temporary)
    print('Código de activación privado (cinco minutos):',activation)

def activate_account(username):
    if not sys.stdin.isatty():raise ValueError('La activación local exige una terminal interactiva.')
    if input('Verifica al titular y confirma su matrícula: ').strip()!=username:raise ValueError('Cancelado.')
    import hardening
    with server.secure.write_transaction() as conn:ticket=hardening.activation_issue(conn,username,'operador_windows')
    print('Código privado de un uso, cinco minutos:',ticket)


def assign_system_admin(username):
    """Operador local confiable: asigna el rol sin leer ni sustituir factores."""
    with server.secure.write_transaction() as conn:
        user=conn.execute('SELECT * FROM users WHERE username=?',(username,)).fetchone()
        if not user or not user['is_active'] or user['is_locked']:
            raise ValueError('Se requiere una cuenta existente, activa y desbloqueada.')
        if user['role']==server.db.ROLE_SYSTEM_ADMIN:
            print('La cuenta ya es Administrador del sistema.');return
        if user['role']==server.db.ROLE_DPO:
            remaining=conn.execute("SELECT COUNT(*) FROM users WHERE role='dpo' AND is_active=1 AND is_locked=0 AND id<>?",(user['id'],)).fetchone()[0]
            if not remaining:raise ValueError('Debe permanecer otro DPO activo y desbloqueado.')
        conn.execute('''UPDATE users SET role=?,area=NULL,
            security_version=security_version+1,updated_at=? WHERE id=?''',
            (server.db.ROLE_SYSTEM_ADMIN,server.db._now(),user['id']))
        server.db.write_audit(conn,'operador_windows','SYSTEM_ADMIN_ASSIGNED',
            'Asignación local autorizada. Rol anterior: '+user['role']+
            '. Credenciales y autenticador conservados; sesiones revocadas.',username)
    print('Administrador del sistema asignado a',username+'. Vuelve a iniciar sesión.')


def main():
    parser=argparse.ArgumentParser(description='Detén el servidor antes del mantenimiento.')
    commands=parser.add_subparsers(dest='action',required=True)
    commands.add_parser('rotate-key')
    p=commands.add_parser('backup');p.add_argument('destination')
    p=commands.add_parser('activate-account');p.add_argument('username')
    p=commands.add_parser('recover-account');p.add_argument('username')
    p=commands.add_parser('assign-system-admin');p.add_argument('username')
    p=commands.add_parser('audit');p.add_argument('url')
    commands.add_parser('audit-status')
    args=parser.parse_args()
    with store.file_lock(server.DATA/'.server.lock'):
        server.initialize()
        if args.action=='rotate-key':server.secure.rotate_key();print('Clave rotada; autenticadores conservados.')
        elif args.action=='backup':backup(args.destination)
        elif args.action=='activate-account':activate_account(args.username)
        elif args.action=='recover-account':recover(args.username)
        elif args.action=='assign-system-admin':assign_system_admin(args.username)
        else:
            import audit_delivery as audit
            if args.action=='audit':audit.configure(args.url,getpass.getpass('Clave HMAC compartida con el receptor: '));print('Receptor configurado. La entrega empieza al iniciar la aplicación.')
            else:
                with server.db.get_connection() as conn:pending=conn.execute('SELECT COUNT(*) FROM audit_outbox WHERE delivered_at IS NULL').fetchone()[0]
                print('Receptor configurado:',bool(audit.load_config()),'Eventos pendientes:',pending)

if __name__=='__main__':
    try:main()
    except (OSError,ValueError,RuntimeError) as error:print('Mantenimiento detenido:',error,file=sys.stderr);sys.exit(1)
