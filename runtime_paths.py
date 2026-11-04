"""Shared, fail-closed private storage paths. Importing never creates data."""
import argparse
import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


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
