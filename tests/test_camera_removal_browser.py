"""Chrome and real API with temporary SQLite, fake camera and three scoped sessions."""
import json,os,subprocess,sys,threading,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tests'))
import test_backend as base
import browser_cameras as bc
import features as f
base.Backend.setUpClass();test=base.Backend();test.setUp()
auth,_=test.login(test.dpo)
monitors=[u for u in test.users if u['role']=='user' and u['area']=='Monitoring' and not u['is_guard']]
editing,_=test.login(monitors[0]);viewing,_=test.login(monitors[1])
f.dispatch(auth,'POST','/api/users/assign-license',{},dict(matricula=monitors[0]['username'],license_id='LIC-CCTV-ADMIN'))
with base.db.get_connection() as c:
 for row in c.execute('SELECT id FROM users').fetchall():c.execute('UPDATE users SET full_name=?,username=? WHERE id=?',('Persona de prueba '+str(row['id']),'PRUEBA-'+str(row['id']),row['id']))
 # License follows the fictitious matrícula used in the running UI.
 c.execute("UPDATE user_licenses SET matricula=? WHERE license_id='LIC-CCTV-ADMIN'",('PRUEBA-'+str(monitors[0]['id']),))
for sid,session in [('owner',auth),('cameraadmin',editing),('viewer',viewing)]:
 base.server.SESSIONS[sid]={'stage':'dashboard','auth':session,'created':time.time(),'csrf':sid+'-csrf'}
owner=base.server.SESSIONS['owner']
for url in ('http://192.168.70.20:8081/video','http://192.168.70.21:8081/video'):f.dispatch(auth,'POST','/api/cctv/destinations',{},dict(action='approve',url=url))
f.dispatch(auth,'POST','/api/cctv/channels',{},dict(channels=[dict(name='IP para sustituir',url='http://192.168.70.20:8081/video',profile='smooth')]))
first=None
for n in range(7):
 channel=bc.dispatch('/api/browser-camera/create',{'name':'Móvil emisor' if n==0 else 'Canal sin usar '+str(n),'zone':'GENERAL_ACCESS'},'owner',owner,lambda sid,auth:True)
 if first is None:first=channel
if os.environ.get('ST_TEST_WEB_ROOT'):base.server.WEB_ROOT=Path(os.environ['ST_TEST_WEB_ROOT']).resolve()
httpd=base.server.ThreadingHTTPServer(('127.0.0.1',0),base.server.Handler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
env=dict(os.environ,ST_TEST_URL='http://127.0.0.1:'+str(httpd.server_port)+'/',ST_TEST_CAMERA=json.dumps({'id':first['id'],'ticket':first['ticket']}))
try:result=subprocess.run([os.environ.get('ST_TEST_NODE','node'),str(ROOT/'tests/browser_camera_removal.cjs')],cwd=ROOT,env=env,timeout=170)
finally:httpd.shutdown();httpd.server_close();f.camera_hub.stop_all()
sys.exit(result.returncode)
