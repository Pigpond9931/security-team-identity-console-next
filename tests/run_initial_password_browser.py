"""Validación visual aislada: nunca utiliza la base ni la sesión del propietario."""
import json, os, subprocess, sys, threading, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tests'))
import test_backend as base
base.Backend.setUpClass()
test = base.Backend(); test.setUp()
auth, _ = test.login(test.dpo)
with base.db.get_connection() as c:
    c.execute('UPDATE users SET full_name=? WHERE id=?', ('PERSONA NUEVO INGRESO', test.user['id']))
base.server.SESSIONS['owner'] = {'stage':'dashboard', 'auth':auth, 'created':time.time(), 'csrf':'owner-csrf'}
httpd = base.server.ThreadingHTTPServer(('127.0.0.1',0), base.server.Handler)
threading.Thread(target=httpd.serve_forever,daemon=True).start()
try:
    env = dict(os.environ, ST_TEST_URL='http://127.0.0.1:'+str(httpd.server_port)+'/', ST_TEST_USERNAME=test.user['username'])
    result = subprocess.run([os.environ['ST_TEST_NODE'], str(ROOT/'tests/browser_initial_password.cjs')], cwd=ROOT, env=env, timeout=120)
finally:
    httpd.shutdown(); httpd.server_close()
sys.exit(result.returncode)
