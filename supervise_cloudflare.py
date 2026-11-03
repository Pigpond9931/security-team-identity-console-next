"""Supervisión local del túnel, con exclusión mutua y parada deliberada."""
import json,os,subprocess,sys,time,urllib.request
from pathlib import Path
import windows_store as store

ROOT=Path(__file__).resolve().parent
DATA=ROOT/'data'
STOP=DATA/'cloudflare-supervisor.stop'

def main(open_browser=False):
    with store.file_lock(DATA/'.supervisor.lock'):
        STOP.unlink(missing_ok=True)
        delay=5
        try:
            while not STOP.exists():
                command=[str(ROOT/'.venv/Scripts/python.exe'),'-u',str(ROOT/'share_cloudflare.py')]
                if open_browser:command.append('--open');open_browser=False
                started=time.monotonic()
                child=subprocess.Popen(command,cwd=ROOT,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                failures=0;public_failures=0;last_public=0
                while child.poll() is None:
                    if STOP.exists():break
                    time.sleep(5)
                    if time.monotonic()-started<65:continue
                    try:
                        request=urllib.request.Request('http://127.0.0.1:8765/api/health')
                        with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=5) as response:
                            if not json.load(response).get('ok'):raise ValueError('health')
                        failures=0
                    except (OSError,ValueError):failures+=1
                    if time.monotonic()-last_public>=60:
                        last_public=time.monotonic()
                        try:
                            info=json.loads((DATA/'cloudflare-links.json').read_text())
                            request=urllib.request.Request(info['console_url']+'/api/health')
                            with urllib.request.build_opener(urllib.request.ProxyHandler({})).open(request,timeout=8) as response:
                                if json.load(response).get('application')!='SECURITY_TEAM_Studio':raise ValueError('health')
                            public_failures=0
                        except (OSError,ValueError,KeyError):public_failures+=1
                    if failures>=3 or public_failures>=3:break
                if child.poll() is None:
                    subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'DETENER_CLOUDFLARE.ps1'),'-RestartChild'],cwd=ROOT,timeout=25)
                    try:child.wait(timeout=20)
                    except subprocess.TimeoutExpired:
                        child.terminate();child.wait(timeout=10)
                if STOP.exists():break
                delay=5 if time.monotonic()-started>300 else min(delay*2,300)
                print('Reconectando Cloudflare en '+str(delay)+' segundos. Consulta ENLACE_CLOUDFLARE.md para la nueva URL.',flush=True)
                for _ in range(delay):
                    if STOP.exists():break
                    time.sleep(1)
        except KeyboardInterrupt:
            STOP.touch()
            subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(ROOT/'DETENER_CLOUDFLARE.ps1')],cwd=ROOT,timeout=25)

if __name__=='__main__':main('--open' in sys.argv)
