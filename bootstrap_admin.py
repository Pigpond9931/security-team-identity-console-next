"""Crea el primer administrador solo en una base nueva; no toca otras instalaciones."""
import os
import secrets
import sys
from pathlib import Path

def main():
    if os.name != 'nt':
        raise SystemExit('Esta instalación utiliza DPAPI y requiere Windows.')
    import server
    import initial_passwords
    import windows_store
    if Path(server.db.DB_PATH).exists():
        raise SystemExit('Ya existe una base. No se modifica. Utiliza la administración existente o un ST_DATA_DIR nuevo.')
    username=input('Matrícula del primer administrador: ').strip()
    name=input('Nombre del primer administrador: ').strip()
    if not username.isdigit() or not 4 <= len(username) <= 20 or not 2 <= len(name) <= 120:
        raise SystemExit('Matrícula o nombre inválidos. No se creó la base.')
    with windows_store.file_lock(server.DATA/'.server.lock'):
        if Path(server.db.DB_PATH).exists():
            raise SystemExit('La base cambió durante la preparación; no se modifica.')
        server.initialize()
        with server.secure.write_transaction() as c:
            if c.execute('SELECT COUNT(*) FROM users').fetchone()[0]:
                raise SystemExit('Hay usuarios existentes; no se modifican.')
            c.execute('INSERT INTO users(username,full_name,role,area,is_guard,password_hash,created_at) VALUES(?,?,?,?,?,?,?)',
                      (username,name,'system_admin',None,0,server.secure.hash_password(secrets.token_urlsafe(32)),server.db._now()))
            issued=initial_passwords.issue(c,username,'bootstrap_local')
        print('Administrador creado:',username)
        print('Contraseña temporal individual (24 horas, un uso):',issued['temporary_password'])
        print('Guárdala en privado. Ejecuta INICIAR.cmd y completa contraseña privada, MFA, recuperación y términos.')
        print('No ejecutes bootstrap de nuevo sobre esta base. Las cuentas siguientes se crean desde la consola.')

if __name__=='__main__':main()
