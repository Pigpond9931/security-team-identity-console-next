"""Pruebas con cuentas y SQLite temporales; no toca la instalación del usuario."""
import concurrent.futures
from contextlib import closing
import http.cookiejar
import importlib
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCRATCH=Path(tempfile.gettempdir())/'SecurityTeamNextTests'
SCRATCH.mkdir(parents=True,exist_ok=True)
TEMP=tempfile.TemporaryDirectory(dir=SCRATCH)
os.environ['ST_DATA_DIR']=TEMP.name
os.environ['ST_TEST_MODE']='1'
sys.path.insert(0,str(ROOT))
import server
import pyotp
db,secure=server.db,server.secure

def record(user_id):
    with db.get_connection() as conn:return dict(conn.execute('SELECT * FROM users WHERE id=?',(user_id,)).fetchone())
def records():
    with db.get_connection() as conn:return [dict(r) for r in conn.execute('SELECT * FROM users')]

class Backend(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        server.initialize()
        secure.cipher()
        cls.base=Path(TEMP.name)/'base.sqlite'
        shutil.copyfile(db.DB_PATH,cls.base)
    def setUp(self):
        shutil.copyfile(self.base,db.DB_PATH)
        server.SESSIONS.clear();server.RATE.clear();server.FRAME_RATE.clear()
        self.users=records()
        self.dpo=next(u for u in self.users if u['role']=='dpo')
        self.user=next(u for u in self.users if u['role']=='user' and u['area']==db.AREA_AC)
    def login(self,user):
        challenge=secure.authenticate(user['username'],db.TEMP_PASSWORD)['challenge']
        challenge=secure.change_initial_password(challenge,'PrivadaDePrueba123!')
        secret=db.generate_mfa_secret()
        session=secure.finish_mfa(challenge,pyotp.TOTP(secret).now(),secret)
        self.assertIsNotNone(session)
        import features
        with db.get_connection() as conn:features.accept(conn,features.row_user(conn,user['username']),'TEST_LOGIN')
        return session,secret
    def test_01_initialize_no_recrea_usuario_renombrado(self):
        with db.get_connection() as conn:conn.execute('UPDATE users SET username=? WHERE id=?',('matricula-nueva',self.dpo['id']))
        server.initialize()
        self.assertEqual(len(records()),33)
        self.assertEqual(db.seed_users(),0)
        self.assertFalse(any(u['username']==self.dpo['username'] for u in records()))
    def test_02_seed_completo_sin_mfa(self):
        self.assertEqual(len(self.users),33)
        self.assertEqual(sum(u['is_guard'] for u in self.users),3)
        self.assertTrue(all(not u['mfa_secret'] for u in self.users))
    def test_03_password_no_equivale_a_acceso(self):
        secure.authenticate(self.user['username'],db.TEMP_PASSWORD)
        self.assertEqual(secure.accesses_today(),0)
        self.assertIsNone(record(self.user['id'])['last_login'])
    def test_04_tres_fallos_concurrentes_bloquean(self):
        original=secure.verify_password;barrier=threading.Barrier(3)
        def race(*args):
            result=original(*args);barrier.wait(timeout=20);return result
        secure.verify_password=race
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                list(pool.map(lambda _:secure.authenticate(self.user['username'],'incorrecta'),range(3)))
        finally: secure.verify_password=original
        user=record(self.user['id'])
        self.assertEqual((user['failed_attempts'],user['is_locked']),(3,1))
    def test_05_mfa_bloqueo_replay_y_cifrado(self):
        _,secret=self.login(self.user)
        row=record(self.user['id'])
        self.assertTrue(row['mfa_secret'].startswith('fernet:'))
        self.assertNotIn(secret,row['mfa_secret'])
        challenge=secure.authenticate(self.user['username'],'PrivadaDePrueba123!')['challenge']
        self.assertIsNone(secure.finish_mfa(challenge,pyotp.TOTP(secret).now()))
        for _ in range(2): self.assertIsNone(secure.finish_mfa(challenge,'------'))
        self.assertTrue(record(self.user['id'])['is_locked'])
    def test_06_reset_revoca_sesion_y_reto(self):
        admin,_=self.login(self.dpo)
        session,secret=self.login(self.user)
        challenge=secure.authenticate(self.user['username'],'PrivadaDePrueba123!')['challenge']
        secure.reset_mfa(admin,self.user['id'])
        self.assertIsNone(secure.current_user(session))
        self.assertIsNone(secure.finish_mfa(challenge,pyotp.TOTP(secret).now()))
    def test_07_doble_enrolamiento_rechazado(self):
        c=secure.authenticate(self.user['username'],db.TEMP_PASSWORD)['challenge']
        c=secure.change_initial_password(c,'PrivadaDePrueba123!')
        s1,s2=db.generate_mfa_secret(),db.generate_mfa_secret()
        self.assertIsNotNone(secure.finish_mfa(c,pyotp.TOTP(s1).now(),s1))
        self.assertIsNone(secure.finish_mfa(c,pyotp.TOTP(s2).now(),s2))
    def test_08_rbac_area_y_promocion(self):
        leader=next(u for u in self.users if u['role']=='area_admin' and u['area']==db.AREA_AC)
        session,_=self.login(leader)
        other=next(u for u in self.users if u['role']=='user' and u['area']==db.AREA_MON)
        with self.assertRaises(PermissionError): secure.update_user(session,other['id'],full_name='Otra persona')
        with self.assertRaises(PermissionError): secure.update_user(session,self.user['id'],role='dpo')
        with self.assertRaises(PermissionError): secure.update_user(session,self.user['id'],is_guard=1)
        secure.update_user(session,self.user['id'],full_name='Nombre de prueba')
        self.assertEqual(record(self.user['id'])['full_name'],'Nombre de prueba')
    def test_09_baja_revoca_mfa_rfid_y_sesion(self):
        admin,_=self.login(self.dpo);session,_=self.login(self.user)
        secure.update_user(admin,self.user['id'],rfid_uid='04:AA')
        secure.update_user(admin,self.user['id'],is_active=0)
        row=record(self.user['id'])
        self.assertIsNone(row['mfa_secret']);self.assertIsNone(row['rfid_uid'])
        self.assertIsNone(secure.current_user(session))
    def test_10_secreto_no_sale_en_listado(self):
        admin,_=self.login(self.dpo);self.login(self.user)
        for row in secure.list_users(admin):
            self.assertNotIn('mfa_secret',row);self.assertNotIn('password_hash',row)
    def test_11_auditoria_no_admite_replace(self):
        with self.assertRaises(sqlite3.IntegrityError):
            with db.get_connection() as conn:
                row=conn.execute('SELECT * FROM audit_log LIMIT 1').fetchone()
                conn.execute('INSERT OR REPLACE INTO audit_log(id,timestamp,action) VALUES(?,?,?)',(row['id'],row['timestamp'],'ALTERADO'))
    def test_12_no_trunca_password_ni_inyecta_sql(self):
        with self.assertRaises(ValueError): secure.hash_password('A'*73)
        self.assertEqual(secure.authenticate("' OR 1=1 --",db.TEMP_PASSWORD)['status'],'invalid')
    def test_13_http_cookie_csrf_origin_y_datos(self):
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
        origin=f'http://127.0.0.1:{httpd.server_port}'
        jar=http.cookiejar.CookieJar()
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
        def request(path,body=None,csrf=None,source=origin):
            headers={'Origin':source}
            if csrf: headers['X-CSRF-Token']=csrf
            if body is not None: headers['Content-Type']='application/json'
            req=urllib.request.Request(origin+'/api/'+path,data=None if body is None else json.dumps(body).encode(),headers=headers)
            try:
                with opener.open(req,timeout=8) as response:return response.status,json.load(response)
            except urllib.error.HTTPError as error:return error.code,json.load(error)
        try:
            status,s=request('session');self.assertEqual(status,200)
            self.assertTrue(all('HttpOnly' in c._rest and c._rest.get('SameSite')=='Strict' for c in jar))
            self.assertEqual(request('data')[0],401)
            self.assertEqual(request('auth/login',{},'wrong')[0],403)
            self.assertEqual(request('auth/login',{},s['csrf'],'https://evil.invalid')[0],403)
            import hardening
            with secure.write_transaction() as conn:activation=hardening.activation_issue(conn,self.dpo['username'],'operador_prueba')
            status,s=request('auth/activate',{'ticket':activation},s['csrf']);self.assertEqual(status,200)
            status,s=request('auth/login',{'username':self.dpo['username'],'password':db.TEMP_PASSWORD},s['csrf']);self.assertEqual(status,200);self.assertEqual(s['stage'],'password')
            status,s=request('auth/password',{'password':'PrivadaDePrueba123!'},s['csrf']);self.assertEqual(s['stage'],'enroll')
            code=pyotp.TOTP(s['enrollment_key']).now()
            status,s=request('auth/mfa',{'code':code},s['csrf']);self.assertEqual(s['stage'],'backup')
            self.assertEqual(len(s['recovery_codes']),8)
            status,s=request('auth/backup-saved',{},s['csrf']);self.assertEqual(s['stage'],'terms')
            self.assertEqual(request('data')[0],403)
            status,s=request('auth/accept-terms',{'accepted':True,'version':db.TERMS_VERSION},s['csrf']);self.assertEqual(s['stage'],'dashboard')
            self.assertNotIn('recovery_codes',s)
            status,data=request('data');self.assertEqual(status,200);self.assertEqual(len(data['users']),33)
            self.assertEqual(data['accesses_today'],1)
            self.assertTrue(all('mfa_secret' not in u and 'password_hash' not in u for u in data['users']))
            self.assertNotIn('enrollment_key',s)
        finally:httpd.shutdown();httpd.server_close();thread.join()

    def test_14_doble_reset_admin_no_suplanta_titular(self):
        admin,_=self.login(self.dpo);session,secret=self.login(self.user)
        old_codes=session['recovery_codes']
        secure.reset_mfa(admin,self.user['id'])
        temporary=secure.reset_password(admin,self.user['id'])
        self.assertIsNone(secure.current_user(session))
        challenge=secure.authenticate(self.user['username'],temporary)['challenge']
        challenge=secure.change_initial_password(challenge,'ClaveSoloDePrueba123!')
        attacker_secret=db.generate_mfa_secret()
        self.assertIsNone(secure.finish_mfa(challenge,pyotp.TOTP(attacker_secret).now(),attacker_secret))
        recovered=secure.recover_mfa(challenge,old_codes[0])
        self.assertIsNotNone(recovered)
        self.assertIsNone(secure.recover_mfa(challenge,old_codes[0]))
        self.assertFalse(record(self.user['id'])['mfa_configured'])
        new_secret=db.generate_mfa_secret()
        new=secure.finish_mfa(recovered,pyotp.TOTP(new_secret).now(),new_secret)
        self.assertIsNotNone(secure.current_user(new))
        with db.get_connection() as conn:
            hashes=[r[0] for r in conn.execute('SELECT code_hash FROM recovery_codes WHERE user_id=?',(self.user['id'],))]
        self.assertNotIn(secure.code_digest(old_codes[1]),hashes)

    def test_15_baja_reactivacion_conserva_prueba_titular(self):
        admin,_=self.login(self.dpo);session,_=self.login(self.user)
        secure.update_user(admin,self.user['id'],is_active=0)
        secure.update_user(admin,self.user['id'],is_active=1)
        challenge=secure.authenticate(self.user['username'],'PrivadaDePrueba123!')['challenge']
        secret=db.generate_mfa_secret()
        self.assertIsNone(secure.finish_mfa(challenge,pyotp.TOTP(secret).now(),secret))
        self.assertIsNotNone(secure.recover_mfa(challenge,session['recovery_codes'][0]))

    def test_16_recuperacion_concurrente_solo_una(self):
        session,_=self.login(self.user)
        challenge=secure.authenticate(self.user['username'],'PrivadaDePrueba123!')['challenge']
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            values=list(pool.map(lambda _:secure.recover_mfa(challenge,session['recovery_codes'][0]),range(2)))
        self.assertEqual(sum(v is not None for v in values),1)

    def test_17_codigos_invalidos_bloquean_y_hash_solo(self):
        session,secret=self.login(self.user)
        with db.get_connection() as conn:
            stored=[r[0] for r in conn.execute('SELECT code_hash FROM recovery_codes')]
        self.assertTrue(all(len(h)==64 for h in stored))
        self.assertTrue(all(c not in stored for c in session['recovery_codes']))
        challenge=secure.authenticate(self.user['username'],'PrivadaDePrueba123!')['challenge']
        for _ in range(3):self.assertIsNone(secure.recover_mfa(challenge,'invalido'))
        self.assertTrue(record(self.user['id'])['is_locked'])

    def test_18_dpapi_y_rotacion_preservan_autenticador(self):
        _,secret=self.login(self.user)
        path=Path(os.environ['ST_KEY_PATH']);before=path.read_bytes()
        self.assertTrue(before.startswith(secure.store.PREFIX))
        self.assertNotEqual(len(before),44)
        secure.rotate_key()
        self.assertNotEqual(before,path.read_bytes())
        self.assertEqual(secure.decrypt_secret(record(self.user['id'])['mfa_secret']),secret)
        self.assertTrue(secure.store.unprotect(path.read_bytes()).startswith(b'{'))

    def test_19_clave_ausente_no_se_regenera(self):
        self.login(self.user)
        path=Path(os.environ['ST_KEY_PATH']);saved=path.read_bytes();path.unlink()
        try:
            with self.assertRaises(RuntimeError):secure.cipher()
            self.assertFalse(path.exists())
        finally:secure.store.atomic_write(path,saved)

    def test_20_bloqueo_mantenimiento_y_rutas_legacy_retiradas(self):
        with secure.store.file_lock(Path(TEMP.name)/'maintenance-test.lock'):
            with self.assertRaises(RuntimeError):
                with secure.store.file_lock(Path(TEMP.name)/'maintenance-test.lock'):pass
        for name in ('reset_database','authenticate','create_user','update_user','reset_mfa','reset_password_to_temp','change_username','confirm_mfa_enrollment','list_users','get_user_by_id'):
            self.assertFalse(hasattr(db,name),name)

    def test_21_regeneracion_codigos_exige_dos_factores_y_revoca(self):
        session,secret=self.login(self.user)
        self.assertIsNone(secure.regenerate_recovery_codes(session,'incorrecta',pyotp.TOTP(secret).now()))
        future=pyotp.TOTP(secret).at(time.time()+30)
        auth=secure.regenerate_recovery_codes(session,'PrivadaDePrueba123!',future)
        self.assertIsNotNone(auth)
        self.assertIsNone(secure.current_user(session))
        self.assertNotEqual(session['recovery_codes'],auth['recovery_codes'])

    def test_22_auditoria_update_delete_y_outbox_atomicos(self):
        for sql in ('UPDATE audit_log SET action=\'alterado\'','DELETE FROM audit_log','INSERT OR REPLACE INTO audit_log SELECT * FROM audit_log LIMIT 1'):
            with self.assertRaises(sqlite3.IntegrityError):
                with db.get_connection() as conn:conn.execute(sql)
        with db.get_connection() as conn:
            total=conn.execute('SELECT COUNT(*) FROM audit_log').fetchone()[0]
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM audit_outbox').fetchone()[0],total)
        with self.assertRaises(RuntimeError):
            with secure.write_transaction() as conn:
                db.write_audit(conn,'prueba','ROLLBACK_TEST');raise RuntimeError()
        with db.get_connection() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM audit_log').fetchone()[0],total)

    def test_23_entrega_firmada_reintenta_y_exige_ack(self):
        import audit_delivery as audit
        audit.configure('https://auditoria.example.invalid/events','x'*40)
        class Reply:
            status=200
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,*args):return b'{}'
        with patch.object(audit.urllib.request,'build_opener') as factory:
            factory.return_value.open.return_value=Reply()
            self.assertFalse(audit.deliver_once())
            request=factory.return_value.open.call_args.args[0]
            self.assertTrue(request.get_header('X-st-signature').startswith('sha256='))
            payload=json.loads(request.data)
            self.assertNotIn('recovery_codes',payload['event'])
            Reply.read=lambda *_:json.dumps({'event_id':payload['event_id']}).encode()
            self.assertTrue(audit.deliver_once())
        with self.assertRaises(ValueError):audit.configure('http://inseguro.invalid','x'*40)

    def test_24_contrasena_inicial_conservada(self):
        self.assertEqual(db.TEMP_PASSWORD,'SoloPruebasLocal2026!')
        self.assertEqual(secure.authenticate(self.user['username'],db.TEMP_PASSWORD)['status'],'ok')

    def test_25_origen_publico_exacto_cookie_secure_y_csrf(self):
        server.configure_public('https://prueba.ngrok-free.app')
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
        url=f'http://127.0.0.1:{httpd.server_port}/api/'
        try:
            req=urllib.request.Request(url+'session',headers={'Host':'prueba.ngrok-free.app'})
            with opener.open(req) as response:
                cookie=response.headers['Set-Cookie'];s=json.load(response)
            self.assertIn('; Secure',cookie)
            req=urllib.request.Request(url+'auth/login',data=b'{}',headers={'Host':'prueba.ngrok-free.app','Origin':'https://otro.ngrok-free.app','Cookie':cookie.split(';')[0],'X-CSRF-Token':s['csrf']})
            with self.assertRaises(urllib.error.HTTPError) as error:opener.open(req)
            self.assertEqual(error.exception.code,403)
            req=urllib.request.Request(url+'session',headers={'Host':'otro.ngrok-free.app'})
            with self.assertRaises(urllib.error.HTTPError) as error:opener.open(req)
            self.assertEqual(error.exception.code,403)
        finally:server.PUBLIC_ORIGIN='';httpd.shutdown();httpd.server_close();thread.join()
        with self.assertRaises(ValueError):server.configure_public('http://inseguro.ngrok-free.app')

    def test_26_dacl_privada_sin_herencia(self):
        result=secure.store.directory_acl(TEMP.name)
        self.assertTrue(result['protected'])
        identities={s.replace('SY','S-1-5-18') for s in re.findall(r';;;([^;)]+)\)',result['sddl'])}
        # En Windows, SDDL puede abreviar al administrador local como LA.
        if secure.store.user_sid().endswith('-500'):
            identities={secure.store.user_sid() if sid=='LA' else sid for sid in identities}
        self.assertEqual(identities,{'S-1-5-18',secure.store.user_sid()})

    def test_27_respaldo_incluye_base_y_clave_protegida(self):
        import maintenance
        self.login(self.user)
        destination=Path(TEMP.name)/'respaldo'
        maintenance.backup(destination)
        self.assertTrue((destination/'identity.sqlite').exists())
        self.assertTrue((destination/'.mfa-key').read_bytes().startswith(secure.store.PREFIX))
        with closing(sqlite3.connect(destination/'identity.sqlite')) as conn:
            self.assertEqual(conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],33)

    def test_28_seed_concurrente_no_duplica(self):
        original=db.DB_PATH;db.DB_PATH=str(Path(TEMP.name)/'concurrent.sqlite')
        try:
            db.init_db()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:counts=list(pool.map(lambda _:db.seed_users(),range(2)))
            self.assertEqual(sorted(counts),[0,33])
            with db.get_connection() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM users').fetchone()[0],33)
        finally:db.DB_PATH=original

    def test_29_ngrok_no_admite_lista_vacia(self):
        import share_ngrok
        with self.assertRaises(ValueError):share_ngrok.make_policy([])
        with self.assertRaises(ValueError):share_ngrok.make_policy(['usuario\" in []'])
        policy=share_ngrok.make_policy(['persona@example.com'])
        self.assertEqual(policy['on_http_request'][0]['actions'][0]['config']['provider'],'google')
        self.assertIn('persona@example.com',policy['on_http_request'][1]['expressions'][0])
        self.assertEqual(policy['on_http_request'][1]['actions'][0]['type'],'deny')

    def test_30_lectura_respeta_revocacion_y_area(self):
        leader=next(u for u in self.users if u['role']=='area_admin' and u['area']==db.AREA_AC)
        session,_=self.login(leader)
        data=secure.dashboard_data(session)
        self.assertTrue(all(u['area']==db.AREA_AC and u['role']=='user' for u in data['users']))
        with db.get_connection() as conn:conn.execute('UPDATE users SET security_version=security_version+1 WHERE id=?',(leader['id'],))
        self.assertIsNone(secure.dashboard_data(session))

    def system_admin(self):
        with db.get_connection() as conn:
            conn.execute('UPDATE users SET role=?,area=NULL WHERE id=?',(db.ROLE_SYSTEM_ADMIN,self.user['id']))
        return self.login(record(self.user['id']))[0]

    def test_31_admin_sistema_global_y_separado_del_dpo(self):
        admin=self.system_admin()
        data=secure.dashboard_data(admin)
        self.assertEqual(len(data['users']),33)
        self.assertEqual(len(secure.list_users(admin)),33)
        self.assertEqual(record(self.user['id'])['role'],'system_admin')
        self.assertEqual(record(self.dpo['id'])['role'],'dpo')
        temporary=secure.create_user(admin,'ADMIN-PRUEBA','Administrador ficticio',db.ROLE_SYSTEM_ADMIN,db.AREA_AC)
        created=next(u for u in records() if u['username']=='ADMIN-PRUEBA')
        self.assertIsNone(created['area'])
        self.assertTrue(secure.verify_password(temporary,created['password_hash']))
        other=next(u for u in self.users if u['role']=='user' and u['area']==db.AREA_MON)
        secure.update_user(admin,other['id'],is_guard=1)
        self.assertEqual(record(other['id'])['is_guard'],1)
        secure.update_user(admin,self.dpo['id'],full_name='DPO de prueba')
        self.assertEqual(record(self.dpo['id'])['full_name'],'DPO de prueba')
        with self.assertRaises(PermissionError):secure.update_user(admin,self.user['id'],role='user',area=db.AREA_AC)

    def test_32_dpo_no_controla_admin_sistema_ni_asigna_su_rol(self):
        self.system_admin();dpo,_=self.login(self.dpo)
        before=record(self.user['id'])
        for operation in (
            lambda:secure.update_user(dpo,self.user['id'],is_active=0),
            lambda:secure.reset_password(dpo,self.user['id']),
            lambda:secure.reset_mfa(dpo,self.user['id']),
            lambda:secure.create_user(dpo,'ESCALAR','Intento',db.ROLE_SYSTEM_ADMIN,None),
            lambda:secure.update_user(dpo,self.users[-1]['id'],role=db.ROLE_SYSTEM_ADMIN),
        ):
            with self.assertRaises(PermissionError):operation()
        self.assertEqual(record(self.user['id']),before)
        self.assertFalse(any(u['username']=='ESCALAR' for u in records()))
        secure.create_user(dpo,'NORMAL','Usuario ficticio',db.ROLE_USER,db.AREA_MON)

    def test_33_preserva_ultimo_admin_sistema_y_ultimo_dpo(self):
        admin=self.system_admin()
        other=next(u for u in self.users if u['role']=='user' and u['area']==db.AREA_MON)
        with db.get_connection() as conn:
            conn.execute('UPDATE users SET role=?,area=NULL WHERE id=?',(db.ROLE_SYSTEM_ADMIN,other['id']))
        second,_=self.login(record(other['id']))
        dpo,_=self.login(self.dpo)
        with self.assertRaises(PermissionError):secure.update_user(dpo,other['id'],is_locked=1)
        for changes in ({'is_active':0},{'is_locked':1},{'role':db.ROLE_USER,'area':db.AREA_AC}):
            with self.assertRaises(PermissionError):secure.update_user(admin,self.dpo['id'],**changes)
        def deactivate(pair):
            session,target=pair
            try:secure.update_user(session,target,is_active=0);return True
            except PermissionError:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            changed=list(pool.map(deactivate,[(admin,other['id']),(second,self.user['id'])]))
        self.assertEqual(sum(changed),1)
        self.assertEqual(sum(u['role']==db.ROLE_SYSTEM_ADMIN and u['is_active'] and not u['is_locked'] for u in records()),1)
        self.assertEqual(sum(secure.current_user(s) is not None for s in (admin,second)),1)

    def test_34_area_y_usuario_no_escalan_a_admin_sistema(self):
        leader=next(u for u in self.users if u['role']=='area_admin' and u['area']==db.AREA_AC)
        session,_=self.login(leader)
        with self.assertRaises(PermissionError):secure.update_user(session,self.user['id'],role=db.ROLE_SYSTEM_ADMIN)
        with self.assertRaises(PermissionError):secure.create_user(session,'ESCALAR','Intento',db.ROLE_SYSTEM_ADMIN,None)
        user,_=self.login(self.user)
        with self.assertRaises(PermissionError):secure.create_user(user,'ESCALAR','Intento',db.ROLE_SYSTEM_ADMIN,None)

    def test_35_asignacion_local_preserva_credenciales_y_dpo(self):
        import maintenance
        old_session,_=self.login(self.user)
        before=record(self.user['id'])
        maintenance.assign_system_admin(self.user['username'])
        after=record(self.user['id'])
        self.assertEqual(after['role'],db.ROLE_SYSTEM_ADMIN)
        self.assertIsNone(after['area'])
        allowed={'role','area','security_version','updated_at'}
        self.assertTrue(all(before[k]==after[k] for k in before if k not in allowed))
        self.assertIsNone(secure.current_user(old_session))
        self.assertEqual(record(self.dpo['id'])['role'],db.ROLE_DPO)
        maintenance.assign_system_admin(self.user['username'])
        self.assertEqual(record(self.user['id']),after)
        with self.assertRaises(ValueError):maintenance.assign_system_admin(self.dpo['username'])
        server.initialize()
        self.assertEqual(record(self.user['id'])['role'],db.ROLE_SYSTEM_ADMIN)

    def test_36_authorization_precedes_password_hashing(self):
        reader,_=self.login(self.user)
        with patch.object(secure,'hash_password',side_effect=AssertionError('hash antes de autorizar')):
            with self.assertRaises(PermissionError):secure.create_user(reader,'SIN-PERMISO','Intento',db.ROLE_USER,db.AREA_AC)
            with self.assertRaises(PermissionError):secure.reset_password(reader,self.dpo['id'])
            with self.assertRaises(PermissionError):secure.change_password({},'ClaveActual123!','ClaveNueva123!','000000')

if __name__=='__main__':
    try: unittest.main(verbosity=2)
    finally: TEMP.cleanup()
