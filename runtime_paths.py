"""Shared, fail-closed private storage paths. Importing never creates data."""
import argparse
import json
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
STORE_MARKER = '.identity-console-store.json'
STORE_ID = 'SecurityTeam.IdentityConsoleNext'


def _contains(parent, child):
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def external_path(value, *, repo_root=REPO_ROOT):
    """Validate before mkdir/DACL/SQLite. Resolve existing symlinks and junctions."""
    raw = Path(value).expanduser()
    if not raw.is_absolute():
        raise ValueError('El almacén privado requiere una ruta absoluta externa al repositorio.')
    repo = Path(repo_root).resolve()
    destination = raw.resolve()
    if _contains(repo, destination) or _contains(destination, repo) or destination == Path(destination.anchor):
        raise ValueError('El almacén debe ser una carpeta dedicada fuera del repositorio, sin contenerlo.')
    if destination.exists() and not destination.is_dir():
        raise ValueError('El almacén privado debe ser una carpeta.')
    # A reparse point could be changed after validation. Refuse any linked ancestor;
    # the private store also rejects links among its descendants before setting ACLs.
    for part in (raw, *raw.parents):
        if part.is_symlink() or (hasattr(part, 'is_junction') and part.is_junction()):
            raise ValueError('No se permiten enlaces ni junctions en la ruta del almacén privado.')
    return destination


def data_dir(*, environ=None, repo_root=REPO_ROOT):
    env = os.environ if environ is None else environ
    repo = Path(repo_root).resolve()
    legacy = repo / 'data'
    if legacy.is_symlink() or (hasattr(legacy, 'is_junction') and legacy.is_junction()):
        raise RuntimeError('Existe un data/ enlazado. Revisa la migración antes de iniciar Next.')
    if legacy.exists() and (not legacy.is_dir() or any(legacy.iterdir())):
        raise RuntimeError('Existe data/ antiguo con contenido. Inicio detenido: respalda y migra con verificación; no se abrirá una base nueva.')
    if 'ST_DATA_DIR' in env:
        value = env['ST_DATA_DIR']
        if not value or not str(value).strip():
            raise ValueError('ST_DATA_DIR está vacío; define una ruta absoluta externa.')
    else:
        local = env.get('LOCALAPPDATA')
        if not local:
            raise RuntimeError('No existe LOCALAPPDATA. Define ST_DATA_DIR con una carpeta privada externa.')
        value = Path(local) / 'SecurityTeam' / 'IdentityConsoleNext'
    return external_path(value, repo_root=repo)


def assert_dedicated_store(directory):
    """Refuse a populated foreign folder before changing ACLs or opening SQLite.

    The marker identifies an intentionally prepared store, not an authentication
    credential. Older unmarked stores require an explicit migration decision.
    """
    path = external_path(directory)
    if not path.exists():
        return False
    marker = path / STORE_MARKER
    if marker.exists() or marker.is_symlink():
        if marker.is_symlink() or (hasattr(marker, 'is_junction') and marker.is_junction()) or not marker.is_file():
            raise RuntimeError('Marcador del almacén privado inválido. No se modificó la carpeta.')
        try:
            if marker.stat().st_size > 4096:
                raise ValueError('Marker size')
            value = json.loads(marker.read_text(encoding='utf-8'))
            if not isinstance(value, dict) or value != {'application': STORE_ID, 'format': 1} or type(value.get('format')) is not int:
                raise ValueError('Marker format')
        except (OSError, ValueError, UnicodeError):
            raise RuntimeError('Marcador del almacén privado inválido. No se modificó la carpeta.') from None
        return True
    # Bootstrap takes the server lock before its first initialization. A lone
    # regular lock file is the only pre-existing entry accepted without a marker.
    for entry in path.iterdir():
        linked = entry.is_symlink() or (hasattr(entry, 'is_junction') and entry.is_junction())
        if entry.name != '.server.lock' or linked or not entry.is_file():
            raise RuntimeError('La carpeta elegida contiene archivos ajenos o un almacén antiguo sin marcador. Selecciona una carpeta nueva; respalda y revisa la migración antes de adoptar datos existentes.')
    return False


def prepare_private_store(directory):
    """Validate ownership intent before applying private ACLs or creating files."""
    path = external_path(directory)
    recognized = assert_dedicated_store(path)
    import windows_store as store
    store.private_directory(path)
    if not recognized:
        content = json.dumps({'application': STORE_ID, 'format': 1}, sort_keys=True) + '\n'
        store.atomic_write(path / STORE_MARKER, content.encode('utf-8'))
    return path


def private_file(name):
    if Path(name).name != name or name in ('.', '..'):
        raise ValueError('Nombre de archivo privado inválido.')
    return data_dir() / name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Resolver el almacén sin crearlo ni migrar datos.')
    parser.add_argument('--print', action='store_true')
    parser.parse_args()
    try:
        print(data_dir())
    except (ValueError, RuntimeError, OSError) as error:
        parser.exit(1, str(error) + '\n')
