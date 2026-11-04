"""Create a Git-aware source manifest or verify an extracted release without Git."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
MANIFEST='manifest-source.json'
TEXT={'.py','.ps1','.cmd','.jsx','.css','.md','.js','.cjs','.mjs','.json','.yml','.yaml','.toml','.txt','.html'}


def source_bytes(path):
    data=path.read_bytes()
    if path.suffix in TEXT or path.name in ('.gitattributes','.gitignore'):
        return data.replace(b'\r\n',b'\n')
    return data


def safe_file(name):
    relative=PurePosixPath(name)
    if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
        raise ValueError('Ruta de manifiesto no permitida.')
    path=ROOT.joinpath(*relative.parts)
    if not path.resolve().is_relative_to(ROOT.resolve()):
        raise ValueError('Ruta fuera de la copia.')
    for part in (path,*path.parents):
        if part==ROOT.parent:break
        if part.is_symlink() or (hasattr(part,'is_junction') and part.is_junction()):
            raise ValueError('Archivo enlazado; verificación detenida.')
    return path


def write(git):
    result=subprocess.run([git,'ls-files','--cached','--others','--exclude-standard','-z'],
        cwd=ROOT,capture_output=True,check=True)
    names=sorted(set(result.stdout.decode('utf-8').rstrip('\0').split('\0'))-{MANIFEST})
    records=[]
    for name in names:
        data=source_bytes(safe_file(name))
        records.append({'path':name,'bytes_normalized':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    report={'format':2,'version':'1.6.0-next.1','prepared':'2026-11-04',
        'scope':'Source files only; excludes this manifest, Git internals, dependencies and private runtime.',
        'normalization':'CRLF to LF for known text extensions; binary files unchanged.',
        'files':records}
    (ROOT/MANIFEST).write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'Manifiesto generado: {len(records)} archivos, sin incluirse a sí mismo.')


def check():
    report=json.loads((ROOT/MANIFEST).read_text(encoding='utf-8'))
    if report.get('format')!=2:raise ValueError('Formato de manifiesto no reconocido.')
    records=report['files'];names=[r['path'] for r in records]
    if len(names)!=len(set(names)) or MANIFEST in names:raise ValueError('Entradas duplicadas o autorreferentes.')
    failed=[]
    for record in records:
        try:
            data=source_bytes(safe_file(record['path']))
            if len(data)!=record['bytes_normalized'] or hashlib.sha256(data).hexdigest()!=record['sha256']:
                failed.append(record['path'])
        except (OSError,ValueError):failed.append(record['path'])
    print(json.dumps({'ok':not failed,'files_verified':len(records),'different_or_missing':failed},ensure_ascii=False))
    return 1 if failed else 0


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true',help='Requiere Git y una copia con solo los cambios que se distribuirán.')
    parser.add_argument('--git',default='git')
    args=parser.parse_args()
    try:
        if args.write:write(args.git)
        else:raise SystemExit(check())
    except (OSError,ValueError,KeyError,subprocess.CalledProcessError) as error:
        print('No fue posible verificar las fuentes:',str(error),file=sys.stderr)
        raise SystemExit(1)
