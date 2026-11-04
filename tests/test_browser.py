"""Inicia API real temporal y comprueba React con Chrome. No toca data/."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading

ROOT=Path(__file__).resolve().parents[1]
SCRATCH=Path(tempfile.gettempdir())/'SecurityTeamNextTests'
SCRATCH.mkdir(parents=True,exist_ok=True)
with tempfile.TemporaryDirectory(dir=SCRATCH) as temporary:
    os.environ['ST_DATA_DIR']=temporary
    os.environ['ST_TEST_MODE']='1'
    sys.path.insert(0,str(ROOT))
    import server
    server.initialize()
    if os.environ.get('ST_TEST_WEB_ROOT'):server.WEB_ROOT=Path(os.environ['ST_TEST_WEB_ROOT']).resolve()
    with server.db.get_connection() as conn:
        for row in conn.execute('SELECT id FROM users').fetchall():
            conn.execute('UPDATE users SET username=?,full_name=? WHERE id=?',
                         (f"PRUEBA-{row['id']}",f"Persona de prueba {row['id']}",row['id']))
        if '--system-admin' in sys.argv:
            conn.execute("UPDATE users SET role='system_admin',area=NULL WHERE username='PRUEBA-2'")
    import hardening
    with server.secure.write_transaction() as conn:
        activation=hardening.activation_issue(conn,'PRUEBA-2' if '--system-admin' in sys.argv else 'PRUEBA-1','operador_prueba')
    httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True)
    thread.start()
    env=dict(os.environ,ST_TEST_ACTIVATION=activation,ST_TEST_URL=f'http://127.0.0.1:{httpd.server_port}/',ST_TEST_PYTHON=sys.executable,
             ST_TEST_ACCOUNT='PRUEBA-2' if '--system-admin' in sys.argv else 'PRUEBA-1')
    try:
        result=subprocess.run([os.environ.get('ST_TEST_NODE','node'),str(ROOT/'tests'/'browser.cjs')],env=env,timeout=240)
    finally:
        httpd.shutdown();httpd.server_close();thread.join()
sys.exit(result.returncode)
