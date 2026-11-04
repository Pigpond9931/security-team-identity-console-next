"""Prepara publicación con login propio de la app; nunca copia tokens ni correos reales."""
from pathlib import Path
import json
import windows_store as store

def main():
    from runtime_paths import data_dir
    data=data_dir()
    store.private_directory(data)
    dest=data/'cloudflare.dpapi'
    if dest.exists():
        raise SystemExit('Ya existe configuración privada. No se reemplaza.')
    settings={'owner_email':'owner@example.com','emails':['owner@example.com'],'email_pin':False}
    store.atomic_write(dest,store.protect(json.dumps(settings).encode()))
    print('Configuración guardada. Acceso con matrícula, contraseña y MFA; sin PIN de correo.')
    print('Completa primero el administrador local antes de ejecutar COMPARTIR_CLOUDFLARE.cmd.')

if __name__=='__main__':main()
