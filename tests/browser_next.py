"""Exercise the real isolated Windows backend through Chrome; no production data."""
from pathlib import Path
import json, os, subprocess, sys, tempfile, threading

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
with tempfile.TemporaryDirectory(prefix='SecurityTeamNextBrowser-') as temporary:
    os.environ['ST_DATA_DIR']=temporary
    os.environ['ST_TEST_MODE']='1'
    import server, initial_passwords
    server.initialize()
    with server.db.get_connection() as c:
        for row in c.execute('SELECT id FROM users').fetchall():
            c.execute('UPDATE users SET username=?,full_name=? WHERE id=?',
                      (str(9900000+row['id']),'Persona ficticia '+str(row['id']),row['id']))
        account=c.execute("SELECT username FROM users WHERE role='dpo'").fetchone()[0]
        grant=initial_passwords.issue(c,account,'operador_prueba',temporary='IngresoFicticioNext123!')
    assert Path(server.db.DB_PATH).resolve().is_relative_to(Path(temporary).resolve())
    assert not (ROOT/'data').exists()
    httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    env=dict(os.environ,ST_TEST_URL=f'http://127.0.0.1:{httpd.server_port}/',
        ST_TEST_ACCOUNT=account,ST_TEST_PYTHON=sys.executable)
    try:
        result=subprocess.run([os.environ.get('ST_TEST_NODE','node'),str(ROOT/'tests/browser_next.cjs')],
            env=env,cwd=ROOT,timeout=180)
    except subprocess.TimeoutExpired:
        output=Path(os.environ.get('ST_QA_OUTPUT',str(ROOT.parent/'qa-browser')))
        output.mkdir(parents=True,exist_ok=True)
        (output/'validation.json').write_text(json.dumps({'ok':False,'status':'timeout','limit_seconds':180}))
        raise
    finally:
        httpd.shutdown();httpd.server_close();thread.join()
    raise SystemExit(result.returncode)
