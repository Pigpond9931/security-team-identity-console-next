"""Vinculación con SQLite temporal y revocación real; no usa la base operativa."""
import time,unittest,sqlite3,threading,http.cookiejar,json,urllib.request,urllib.error
import test_backend as base
import phone_links as links
import features as f
db,sec,server=base.db,base.secure,base.server

class PhoneLinks(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):
        base.Backend.setUp(self);links.LINKS.clear()
        self.user=next(u for u in self.users if u['role']=='user' and not u['is_guard'])
        self.admin,_=self.login(self.dpo);self.reader,_=self.login(self.user)
        self.state={'stage':'dashboard','created':time.time(),'auth':self.admin};self.parents={'owner':self.state}
    def alive(self,sid,auth):return bool(sid in self.parents and self.parents[sid]['auth']==auth)
    def req(self,path,body=None,sid='owner',state=None):return links.dispatch('/api/scanner/'+path,body or {},sid,self.state if state is None else state,self.alive)
    def create(self):return self.req('create',{'zone':'GENERAL_ACCESS','direction':'AUTO'})
    def pair(self):
        link=self.create();phone=self.req('claim',{'ticket':link['ticket'],'name':'Teléfono de prueba'},sid='phone',state={})
        self.req('approve',{'id':link['id'],'confirmation':phone['confirmation']});return link,phone
    def badge(self):return f.dispatch(self.reader,'GET','/api/users/qr-badge',{}, {})['badge']['token']
    def test_01_confirmation_required_then_scans_and_deduplicates(self):
        link=self.create();phone=self.req('claim',{'ticket':link['ticket']},sid='phone',state={});token=self.badge()
        with self.assertRaises(PermissionError):self.req('read',{'phone_token':phone['phone_token'],'ref':token},sid='phone',state={})
        with self.assertRaises(ValueError):self.req('approve',{'id':link['id'],'confirmation':'incorrecto'})
        self.req('approve',{'id':link['id'],'confirmation':phone['confirmation']})
        result=self.req('read',{'phone_token':phone['phone_token'],'ref':token,'zone':'SERVER_ROOM','direction':'CHECK_OUT'},sid='phone',state={})
        self.assertEqual(result['result']['verdict'],'VERIFIED');self.assertEqual(result['result']['zone'],'GENERAL_ACCESS');self.assertEqual(result['result']['direction'],'CHECK_IN')
        duplicate=self.req('read',{'phone_token':phone['phone_token'],'ref':token},sid='phone',state={});self.assertTrue(duplicate['duplicate']);self.assertIsNone(duplicate['result'])
        with db.get_connection() as c:self.assertEqual(c.execute('SELECT COUNT(*) FROM access_events').fetchone()[0],1)
    def test_02_ticket_consumed_once_new_pair_invalidates_old(self):
        link,phone=self.pair()
        with self.assertRaises(PermissionError):self.req('claim',{'ticket':link['ticket']})
        self.create()
        with self.assertRaises(PermissionError):self.req('poll',{'phone_token':phone['phone_token']})
    def test_03_logout_revocation_and_account_block_are_effective(self):
        link,phone=self.pair();self.parents.clear()
        with self.assertRaises(PermissionError):self.req('read',{'phone_token':phone['phone_token'],'ref':self.badge()})
        self.parents['owner']=self.state;link,phone=self.pair()
        with db.get_connection() as c:c.execute('UPDATE users SET is_locked=1 WHERE id=?',(self.dpo['id'],))
        with self.assertRaises(PermissionError):self.req('poll',{'phone_token':phone['phone_token']})
    def test_04_owner_scope_role_change_and_expiry(self):
        link,phone=self.pair()
        with self.assertRaises(PermissionError):self.req('revoke',{'id':link['id']},sid='other')
        with db.get_connection() as c:c.execute("UPDATE users SET role='user',area='Identity Management',is_guard=0 WHERE id=?",(self.dpo['id'],))
        with self.assertRaises(PermissionError):self.req('read',{'phone_token':phone['phone_token'],'ref':self.badge()})
        links.LINKS[link['id']]['expires']=0
        with self.assertRaises(PermissionError):self.req('poll',{'phone_token':phone['phone_token']})
    def test_05_regular_user_cannot_create_and_area_cannot_expand(self):
        with self.assertRaises(PermissionError):self.req('create',{'zone':'GENERAL_ACCESS','direction':'AUTO'},state={**self.state,'auth':self.reader})
        leader=next(u for u in self.users if u['role']=='area_admin' and u['area']==db.AREA_AC);auth,_=self.login(leader)
        with self.assertRaises(PermissionError):self.req('create',{'zone':'SERVER_ROOM','direction':'AUTO'},state={**self.state,'auth':auth})
    def test_06_disconnect_audit_and_no_credentials_in_public_status(self):
        link,phone=self.pair();status=self.req('poll',{'phone_token':phone['phone_token']})
        for secret in ('auth','sid','ticket_hash','phone_hash','password_hash','mfa_secret','phone_token'):self.assertNotIn(secret,status)
        self.req('disconnect',{'phone_token':phone['phone_token']})
        with self.assertRaises(PermissionError):self.req('poll',{'phone_token':phone['phone_token']})
        with db.get_connection() as c:self.assertIsNotNone(c.execute("SELECT 1 FROM audit_log WHERE action='SCANNER_LINK_REVOKED'").fetchone())
    def test_07_eight_cameras_and_limit(self):
        channels=[{'name':'Canal '+str(i),'url':'http://192.168.1.'+str(i+10)+':8081/video','profile':'smooth'} for i in range(8)]
        for ch in channels:f.dispatch(self.admin,'POST','/api/cctv/destinations',{}, {'action':'approve','url':ch['url']})
        result=f.dispatch(self.admin,'POST','/api/cctv/channels',{}, {'channels':channels});self.assertEqual(len(result['channels']),8);self.assertEqual(result['max_channels'],8)
        with self.assertRaises(ValueError):f.dispatch(self.admin,'POST','/api/cctv/channels',{}, {'channels':channels+[channels[0]]})
    def test_08_http_csrf_public_phone_has_no_admin_session(self):
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
        url='http://127.0.0.1:'+str(httpd.server_port)
        owner_sid='owner';self.state['csrf']='owner-csrf';server.SESSIONS[owner_sid]=self.state
        jar=http.cookiejar.CookieJar();op=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        def request(path,body=None,csrf='',origin=url):
            headers={'Origin':origin,'Content-Type':'application/json','X-CSRF-Token':csrf}
            try:
                with op.open(urllib.request.Request(url+path,data=json.dumps(body).encode() if body is not None else None,headers=headers)) as r:return r.status,json.load(r)
            except urllib.error.HTTPError as e:return e.code,json.load(e)
        try:
            _,terms=request('/api/terms');link=self.create()
            self.assertEqual(request('/api/scanner/claim',{'ticket':link['ticket']},'bad')[0],403)
            self.assertEqual(request('/api/scanner/claim',{'ticket':link['ticket']},terms['csrf'],'https://evil.test')[0],403)
            status,phone=request('/api/scanner/claim',{'ticket':link['ticket']},terms['csrf']);self.assertEqual(status,200)
            self.assertNotIn('phone_token',phone)
            credential=next(c for c in jar if c.name=='st_scan');self.assertIn('HttpOnly',credential._rest);self.assertEqual(credential.path,'/api/scanner')
            self.req('approve',{'id':link['id'],'confirmation':phone['confirmation']})
            self.assertEqual(request('/api/scanner/read',{'ref':self.badge()},terms['csrf'])[0],200)
            self.assertEqual(request('/api/data')[0],401)
            self.assertEqual(request('/api/scanner/create',{'zone':'GENERAL_ACCESS','direction':'AUTO'},terms['csrf'])[0],403)
        finally:httpd.shutdown();httpd.server_close();server.SESSIONS.clear()

if __name__=='__main__':unittest.main()
