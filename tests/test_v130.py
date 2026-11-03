"""Integración real v1.3 sobre SQLite temporal; nunca usa la base operativa."""
import concurrent.futures
import hashlib
import http.cookiejar
import io
import json
import sqlite3
import threading
import time
import unittest
import urllib.request
import urllib.error
from unittest.mock import patch
import test_backend as base
import features as f
from PIL import Image

db,sec,server=base.db,base.secure,base.server

class Features(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    def setUp(self):
        base.Backend.setUp(self)
        self.user=next(u for u in self.users if u['role']=='user' and u['area']==db.AREA_AC and not u['is_guard'])
    login=base.Backend.login
    def setup_pair(self):
        admin,_=self.login(self.dpo);user,_=self.login(self.user)
        return admin,user
    def req(self,s,path,body=None,q=None):return f.dispatch(s,'GET' if body is None else 'POST',path,q or {},body or {})
    def badge(self,s):return self.req(s,'/api/users/qr-badge')['badge']['token']
    def scan(self,s,ref,zone='GENERAL_ACCESS',method='QR_BADGE',direction='AUTO'):
        return self.req(s,'/api/access/verify',{'ref':ref,'zone':zone,'method':method,'direction':direction})['result']
    def test_01_migration_idempotent_preserves_every_existing_field(self):
        before=base.records();db.migrate_extensions();db.migrate_extensions()
        self.assertEqual(base.records(),before)
        with db.get_connection() as c:
            self.assertEqual(c.execute('SELECT COUNT(*) FROM licenses_catalog').fetchone()[0],5)
            self.assertEqual(c.execute('SELECT COUNT(*) FROM camera_channels').fetchone()[0],0)
    def test_02_terms_required_and_explicit_version(self):
        admin,user=self.setup_pair()
        with db.get_connection() as c:c.execute('UPDATE users SET terms_accepted=0 WHERE id=?',(self.user['id'],))
        with self.assertRaises(PermissionError):self.req(user,'/api/licenses')
        for b in ({},{'accepted':False,'version':'v1.0'},{'accepted':True,'version':'v0'}):
            with self.assertRaises(ValueError):self.req(user,'/api/auth/accept-terms',b)
        self.req(user,'/api/auth/accept-terms',{'accepted':True,'version':'v1.0'})
        self.assertEqual(len(self.req(user,'/api/licenses')['licenses']),5)
    def test_03_qr_signature_purpose_expiration_and_security_version(self):
        admin,user=self.setup_pair();token=self.badge(user)
        self.assertEqual(f.verify(token,'BADGE')['sv'],base.record(self.user['id'])['security_version'])
        for bad in (token+'x',token[:-6]+'abcdef','ST3.bad.bad'):
            self.assertEqual(self.scan(admin,bad)['verdict'],'DENIED')
        with db.get_connection() as c:c.execute('UPDATE users SET security_version=security_version+1 WHERE id=?',(self.user['id'],))
        self.assertEqual(self.scan(admin,token)['verdict'],'DENIED')
        with self.assertRaises(ValueError):f.verify(f.sign({'purpose':'BADGE','tipo':'USER','ref':'x','sv':0,'exp':time.time()-1}),'BADGE')
    def test_04_idor_badges_and_png(self):
        admin,user=self.setup_pair()
        for path in ('/api/users/qr-badge','/api/users/qr-badge.png'):
            with self.assertRaises(PermissionError):self.req(user,path,q={'matricula':self.dpo['username']})
        out=self.req(user,'/api/users/qr-badge.png')
        import base64
        im=Image.open(io.BytesIO(base64.b64decode(out['png_base64'])))
        self.assertEqual(im.size,(720,1180))
        self.assertTrue(out['qr_png_base64'])
    def test_05_mobile_delivery_separate_bearer_and_terms(self):
        admin,user=self.setup_pair()
        with db.get_connection() as c:c.execute('UPDATE users SET terms_accepted=0 WHERE id=?',(self.user['id'],))
        token=self.req(admin,'/api/users/mobile-pass',{'matricula':self.user['username']})['pass_token']
        with sec.write_transaction() as c:
            before=f.pass_payload(c,f.verify(token,'PASS'));self.assertIsNone(before['qr_png_base64'])
            self.assertFalse(before['terms']['accepted'])
            after=f.pass_payload(c,f.verify(token,'PASS'),True);self.assertTrue(after['terms']['accepted'])
            with self.assertRaises(ValueError):f.verify(after['badge']['token'],'PASS')
        self.assertEqual(self.scan(admin,token)['verdict'],'DENIED')
        self.assertEqual(self.scan(admin,after['badge']['token'])['verdict'],'VERIFIED')
    def test_06_block_revoke_mobile_and_physical(self):
        admin,user=self.setup_pair();token=self.badge(user)
        mobile=self.req(user,'/api/users/mobile-pass',{'matricula':self.user['username']})['pass_token']
        sec.update_user(admin,self.user['id'],is_locked=1)
        self.assertEqual(self.scan(admin,token)['verdict'],'DENIED')
        with db.get_connection() as c:
            with self.assertRaises(ValueError):f.pass_payload(c,f.verify(mobile,'PASS'))
    def test_07_rfid_hid_hex_normalization_and_duplicate_prevention(self):
        admin,user=self.setup_pair();sec.update_user(admin,self.user['id'],rfid_uid='04:AA')
        self.assertEqual(self.scan(admin,'1194',method='RFID_125KHZ')['verdict'],'VERIFIED')
        self.assertEqual(self.scan(admin,'001194',method='RFID_125KHZ')['direction'],'CHECK_OUT')
        other=next(u for u in self.users if u['role']=='user' and u['id']!=self.user['id'])
        with self.assertRaises(ValueError):sec.update_user(admin,other['id'],rfid_uid='1194')
        self.assertEqual(self.scan(admin,'99999999',method='RFID_125KHZ')['verdict'],'DENIED')
    def test_08_zones_and_critical_license(self):
        admin,user=self.setup_pair();token=self.badge(user)
        self.req(admin,'/api/users/zones',{'matricula':self.user['username'],'zones':['GENERAL_ACCESS','SERVER_ROOM']})
        denied=self.scan(admin,token,'SERVER_ROOM');self.assertEqual(denied['verdict'],'DENIED')
        self.req(admin,'/api/users/assign-license',{'matricula':self.user['username'],'license_id':'LIC-SRV-CRIT'})
        self.assertEqual(self.scan(admin,token,'SERVER_ROOM')['verdict'],'VERIFIED')
        self.assertEqual(self.scan(admin,token,'DATA_CENTER_VAULT')['verdict'],'DENIED')
    def test_09_presence_per_zone_and_assisted_checkout(self):
        admin,user=self.setup_pair();token=self.badge(user);first=self.scan(admin,token)
        self.assertEqual(first['direction'],'CHECK_IN')
        self.assertEqual(len(self.req(admin,'/api/access/presence')['presence']),1)
        checkout=self.req(admin,'/api/access/checkout',{'event_id':first['id']})['result']
        self.assertEqual(checkout['direction'],'CHECK_OUT')
        self.assertEqual(len(self.req(admin,'/api/access/presence')['presence']),0)
        with self.assertRaises(ValueError):self.req(admin,'/api/access/checkout',{'event_id':first['id']})
    def test_10_visitors_acceptance_expiry_revoke_and_scope(self):
        admin,user=self.setup_pair();v=self.req(admin,'/api/visitors/create',{'full_name':'Invitado de prueba','allowed_zone':'GENERAL_ACCESS','duration':'2h'})
        self.assertIsNone(v['qr_png_base64'])
        with sec.write_transaction() as c:active=f.pass_payload(c,f.verify(v['pass_token'],'PASS'),True)
        self.assertEqual(self.scan(admin,active['badge']['token'])['verdict'],'VERIFIED')
        self.assertEqual(self.scan(admin,active['badge']['token'],'SERVER_ROOM')['verdict'],'DENIED')
        self.req(admin,'/api/visitors/revoke',{'visitor_id':v['visitor']['visitor_id']})
        self.assertEqual(self.scan(admin,active['badge']['token'])['verdict'],'DENIED')
        with db.get_connection() as c:
            with self.assertRaises(ValueError):f.pass_payload(c,f.verify(v['pass_token'],'PASS'))
        with self.assertRaises(PermissionError):self.req(user,'/api/visitors')
        expired=f.sign({'purpose':'BADGE','tipo':'VISITOR','ref':v['visitor']['visitor_id'],'exp':0,'sv':0})
        self.assertEqual(self.scan(admin,expired)['verdict'],'DENIED')
    def test_11_seat_limit_concurrent_and_release_on_offboard(self):
        admin,user=self.setup_pair();others=[u for u in self.users if u['role']=='user' and u['id']!=self.user['id']][:2]
        with db.get_connection() as c:c.execute("UPDATE licenses_catalog SET seats=1 WHERE license_id='LIC-SRV-CRIT'")
        def assign(u):
            try:self.req(admin,'/api/users/assign-license',{'matricula':u['username'],'license_id':'LIC-SRV-CRIT'});return True
            except f.Conflict:return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:out=list(pool.map(assign,others))
        self.assertEqual(sum(out),1)
        with db.get_connection() as c:held=c.execute("SELECT matricula FROM user_licenses WHERE license_id='LIC-SRV-CRIT'").fetchone()[0]
        target=next(u for u in others if u['username']==held);sec.update_user(admin,target['id'],is_active=0)
        with db.get_connection() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM user_licenses').fetchone()[0],0)
        with self.assertRaises(ValueError):self.req(admin,'/api/users/assign-license',{'matricula':held,'license_id':'LIC-SRV-CRIT'})
    def test_12_scope_dpo_cannot_manage_system_admin(self):
        admin,user=self.setup_pair()
        with db.get_connection() as c:c.execute("UPDATE users SET role='system_admin',area=NULL WHERE id=?",(self.user['id'],))
        for path,body in [('/api/users/assign-license',{'license_id':'LIC-IAM-STD'}),('/api/users/zones',{'zones':['GENERAL_ACCESS']}),('/api/users/mobile-pass',{})]:
            with self.assertRaises(PermissionError):self.req(admin,path,dict(body,matricula=self.user['username']))
        for path in ('/api/users/qr-badge','/api/users/qr-badge.png'):
            with self.assertRaises(PermissionError):self.req(admin,path,q={'matricula':self.user['username']})
    def test_13_area_admin_no_scope_expansion(self):
        leader=next(u for u in self.users if u['role']=='area_admin' and u['area']==db.AREA_AC);s,_=self.login(leader)
        with self.assertRaises(PermissionError):self.req(s,'/api/users/zones',{'matricula':self.user['username'],'zones':['SERVER_ROOM']})
        outside=next(u for u in self.users if u['role']=='user' and u['area']==db.AREA_MON)
        with self.assertRaises(PermissionError):self.req(s,'/api/users/assign-license',{'matricula':outside['username'],'license_id':'LIC-IAM-STD'})
        with self.assertRaises(PermissionError):self.req(s,'/api/access/verify',{'zone':'SERVER_ROOM','method':'RFID_125KHZ','ref':'1'})
    def test_14_access_events_append_only_and_outbox(self):
        admin,user=self.setup_pair();event=self.scan(admin,self.badge(user))
        for sql in ('UPDATE access_events SET reason=\'alterado\'','DELETE FROM access_events','INSERT OR REPLACE INTO access_events SELECT * FROM access_events'):
            with self.assertRaises(sqlite3.IntegrityError):
                with db.get_connection() as c:c.execute(sql)
        with db.get_connection() as c:
            self.assertIsNotNone(c.execute("SELECT o.audit_id FROM audit_outbox o JOIN audit_log a ON a.id=o.audit_id WHERE a.action='ACCESS_VERIFIED'").fetchone())
    def test_15_threats_five_rules_and_no_public_secrets(self):
        admin,user=self.setup_pair();self.scan(admin,'invalid')
        self.req(admin,'/api/users/assign-license',{'matricula':self.user['username'],'license_id':'LIC-DC-VAULT'})
        sec.update_user(admin,self.user['id'],rfid_uid='123456',is_locked=1)
        result=self.req(admin,'/api/threats')['findings'];self.assertEqual({x['code'] for x in result},{'TH-01','TH-02','TH-03','TH-04','TH-05'})
        for x in result:
            self.assertTrue(all(k in x for k in ('severity','evidence','recommendation','false_positive_note')))
        self.assertNotIn('password_hash',json.dumps(result));self.assertNotIn('fernet:',json.dumps(result))
    def test_16_cctv_license_permission_and_ssrf_boundaries(self):
        admin,user=self.setup_pair()
        with self.assertRaises(PermissionError):self.req(user,'/api/cctv/channels')
        self.req(admin,'/api/users/assign-license',{'matricula':self.user['username'],'license_id':'LIC-CCTV-MON'})
        self.assertEqual(self.req(user,'/api/cctv/channels')['channels'],[])
        with self.assertRaises(PermissionError):self.req(user,'/api/cctv/channels',{'channels':[]})
        for url in ('http://127.0.0.1:8765/api/data','http://169.254.169.254/','https://example.com/','http://192.168.1.2:22/','http://name.local/video','http://u:p@192.168.1.2/video'):
            with self.assertRaises(ValueError):self.req(admin,'/api/cctv/channels',{'channels':[{'name':'x','url':url}]})
        self.req(admin,'/api/cctv/destinations',{'action':'approve','url':'http://192.168.1.20:8080/video'})
        out=self.req(admin,'/api/cctv/channels',{'channels':[{'name':'Cámara','url':'http://192.168.1.20:8080/video'}]})
        self.assertEqual(len(out['channels']),1)
    def test_18_batch_deliveries_only_ready_and_rbac(self):
        admin,user=self.setup_pair()
        with self.assertRaises(PermissionError):self.req(user,'/api/mobile-passes/renew',{})
        with db.get_connection() as c:c.execute("UPDATE users SET role='system_admin',area=NULL WHERE id=?",(self.user['id'],))
        visitor=self.req(admin,'/api/visitors/create',{'full_name':'Invitado prueba','allowed_zone':'GENERAL_ACCESS','duration':'2h'})
        before=base.records();out=self.req(admin,'/api/mobile-passes/renew',{})
        self.assertEqual(base.records(),before)
        ids={x['id'] for x in out['deliveries']}
        self.assertIn(self.dpo['username'],ids);self.assertIn(visitor['visitor']['visitor_id'],ids)
        self.assertNotIn(self.user['username'],ids)
        self.assertTrue(out['skipped'])
        for item in out['deliveries']:self.assertEqual(f.verify(item['pass_token'],'PASS')['ref'],item['id'])
    def test_19_public_portal_cannot_reach_console(self):
        import share_cloudflare as cloud
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),cloud.PassOnlyHandler)
        httpd.public_origin='https://passes.example.test'
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        url='http://127.0.0.1:'+str(httpd.server_port)
        def get(path):
            try:
                with urllib.request.urlopen(urllib.request.Request(url+path,headers={'Host':'passes.example.test'})) as r:return r.status,r.headers
            except urllib.error.HTTPError as e:return e.code,e.headers
        try:
            self.assertEqual(get('/pass')[0],200)
            status,headers=get('/api/terms');self.assertEqual(status,200);self.assertIn('Secure',headers.get('Set-Cookie',''))
            for path in ('/','/api/data','/api/session','/api/cctv/stream','/assets/../server.py','/api/health'):self.assertEqual(get(path)[0],404)
            self.assertEqual(get('/api/public-pass?token=bad')[0],400)
            request=urllib.request.Request(url+'/api/auth/login',data=b'{}',headers={'Host':'passes.example.test'})
            with self.assertRaises(urllib.error.HTTPError) as e:urllib.request.urlopen(request)
            self.assertEqual(e.exception.code,404)
        finally:httpd.shutdown();httpd.server_close()
    def test_20_cloudflare_command_keeps_email_protection(self):
        import share_cloudflare as cloud
        command=cloud.command(8765,'PRIVATE-CONSOLE.log',['owner@example.com','guest@example.com'])
        self.assertIn('--allowed-mail',command);self.assertIn('owner@example.com,guest@example.com',command)
        self.assertNotIn('--allowed-mail',cloud.command(8766,'PRIVATE-PASSES.log'))
        for emails in ([],['@gmail.com'],['*@gmail.com']):
            with self.assertRaises(ValueError):cloud.emails_valid(emails)
    def test_17_http_expired_challenge_and_public_pass_csrf(self):
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
        url=f'http://127.0.0.1:{httpd.server_port}';jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        def request(path,body=None,csrf=None,origin=url):
            headers={'Origin':origin}
            if body is not None:headers.update({'Content-Type':'application/json','X-CSRF-Token':csrf or ''})
            try:
                with opener.open(urllib.request.Request(url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)) as r:return r.status,json.load(r)
            except urllib.error.HTTPError as e:return e.code,json.load(e)
        try:
            _,s=request('/api/session');_,s=request('/api/auth/login',{'username':self.user['username'],'password':db.TEMP_PASSWORD},s['csrf'])
            for state in server.SESSIONS.values():
                if state.get('challenge'):state['challenge']['issued_at']-=301
            status,v=request('/api/auth/mfa',{'code':'123456'},s['csrf']);self.assertEqual(status,401);self.assertEqual(v['code'],'CHALLENGE_EXPIRED');self.assertEqual(v['stage'],'login')
            _,terms=request('/api/terms')
            self.assertEqual(request('/api/public-pass/accept-terms',{'token':'bad','accepted':True,'version':'v1.0'},'bad')[0],403)
            self.assertEqual(request('/api/public-pass/accept-terms',{'token':'bad','accepted':True,'version':'v1.0'},terms['csrf'],'https://evil.invalid')[0],403)
            self.assertEqual(request('/api/public-pass?token=bad')[0],400)
            self.assertEqual(request('/api/access/latest')[0],401)
        finally:httpd.shutdown();httpd.server_close();thread.join()

if __name__=='__main__':
    try:unittest.main(verbosity=2)
    finally:base.TEMP.cleanup()
