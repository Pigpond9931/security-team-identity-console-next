"""Regresiones de auditoría, solo cuentas y SQLite temporales."""
import http.client,json,secrets,threading,time,unittest
from types import SimpleNamespace
from unittest.mock import patch
import test_backend as base
import hardening as h,pass_exchange as px,features as f
db,sec,server=base.db,base.secure,base.server

class Hardening(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):base.Backend.setUp(self)
    def test_activation_single_use_binding_expiry_and_preservation(self):
        before=base.records()
        with sec.write_transaction() as c:
            ticket=h.activation_issue(c,self.user['username'],'test');state={}
            self.assertFalse(h.activation_valid(state,self.user))
            with self.assertRaises(ValueError):h.activation_claim(c,ticket,{'challenge':{'user_id':self.dpo['id']}})
            row=h.activation_claim(c,ticket,state);self.assertTrue(h.activation_valid(state,row))
            with self.assertRaises(ValueError):h.activation_claim(c,ticket,{})
            self.assertFalse(h.activation_valid(state,{**dict(row),'security_version':row['security_version']+1}))
            state['activation']['expires']=0;self.assertFalse(h.activation_valid(state,row))
            h.migrate(c);h.migrate(c)
        self.assertEqual(base.records(),before)
    def test_approved_camera_scope_and_revocation(self):
        admin,_=self.login(self.dpo);user,_=self.login(self.user)
        f.dispatch(admin,'POST','/api/users/assign-license',{}, {'matricula':self.user['username'],'license_id':'LIC-CCTV-ADMIN'})
        target='http://192.168.8.20:8081/video'
        f.dispatch(user,'POST','/api/cctv/destinations',{}, {'action':'request','url':target})
        with self.assertRaises(PermissionError):f.dispatch(user,'POST','/api/cctv/destinations',{}, {'action':'approve','url':target})
        with db.get_connection() as c:
            with self.assertRaises(PermissionError):h.camera_target(c,target)
        f.dispatch(admin,'POST','/api/cctv/destinations',{}, {'action':'approve','url':target})
        with db.get_connection() as c:
            self.assertEqual(h.camera_target(c,target),target)
            for other in (target+'?other=1',target.replace('/video','/admin')):
                with self.assertRaises(PermissionError):h.camera_target(c,other)
        f.dispatch(admin,'POST','/api/cctv/destinations',{}, {'action':'revoke','url':target})
        with db.get_connection() as c:
            with self.assertRaises(PermissionError):h.camera_target(c,target)
    def test_user_pass_requires_holder_and_receipt_is_session_bound(self):
        admin,_=self.login(self.dpo);user,_=self.login(self.user)
        issued=f.dispatch(user,'POST','/api/users/mobile-pass',{}, {})
        token=issued['pass_token'];sid=secrets.token_urlsafe(32)
        with sec.write_transaction() as c:
            preview=px.preview(c,token);self.assertTrue(preview['requires_login']);self.assertNotIn('badge',preview)
            for auth in (None,admin):
                with self.assertRaises(PermissionError):px.claim(c,token,sid,auth)
            receipt=px.claim(c,token,sid,user)
            with self.assertRaises(ValueError):px.claim(c,token,sid,user)
            self.assertTrue(px.read(c,receipt,sid,user)['badge']['token'])
            with self.assertRaises(ValueError):px.read(c,receipt,secrets.token_urlsafe(32),user)
            with self.assertRaises(PermissionError):px.read(c,receipt,sid,admin)
            c.execute('UPDATE pass_receipts SET expires=0')
            with self.assertRaises(ValueError):px.read(c,receipt,sid,user)
    def test_visitor_requires_host_confirmation_before_terms_or_identity(self):
        admin,_=self.login(self.dpo)
        issued=f.dispatch(admin,'POST','/api/visitors/create',{}, {'full_name':'Visitante ficticio','organization':'Pruebas','visit_reason':'Regresión','allowed_zone':'GENERAL_ACCESS','duration':'4h'})
        sid=secrets.token_urlsafe(32)
        with sec.write_transaction() as c:
            receipt=px.claim(c,issued['pass_token'],sid,None)
            pending=px.read(c,receipt,sid,None,True);self.assertTrue(pending['pending_approval']);self.assertNotIn('badge',pending)
            row=c.execute('SELECT * FROM pass_receipts').fetchone()
            with self.assertRaises(ValueError):px.approve(c,f.actor(c,admin),row['id'],'invalid')
            receipt_id=row['id']
        f.dispatch(admin,'POST','/api/visitors/approve-device',{}, {'id':receipt_id,'confirmation':pending['confirmation']})
        with sec.write_transaction() as c:
            data=px.read(c,receipt,sid,None);self.assertFalse(data['terms']['accepted']);self.assertFalse(data['badge']['token'])
            data=px.read(c,receipt,sid,None,True);self.assertTrue(data['terms']['accepted']);self.assertTrue(data['badge']['token'])
    def test_rate_budgets_isolate_accounts_and_have_memory_bound(self):
        buckets={}
        self.assertTrue(h.rate_check(buckets,[('a',1),('global',3)]))
        self.assertFalse(h.rate_check(buckets,[('a',1),('global',3)]))
        self.assertTrue(h.rate_check(buckets,[('b',1),('global',3)]))
        self.assertTrue(h.rate_check(buckets,[('c',1),('global',3)]))
        self.assertFalse(h.rate_check(buckets,[('d',1),('global',3)]))
        buckets={str(i):[time.monotonic()] for i in range(4097)};self.assertFalse(h.rate_check(buckets,[('new',1)]))
    def test_per_second_budget_for_video_frames_is_separate(self):
        buckets={}
        self.assertTrue(h.rate_check(buckets,[('frame:token',2)],window=1))
        self.assertTrue(h.rate_check(buckets,[('frame:token',2)],window=1))
        self.assertFalse(h.rate_check(buckets,[('frame:token',2)],window=1))
        buckets['old']=[time.monotonic()-2]
        self.assertTrue(h.rate_check(buckets,[('fresh',1)],window=1))
        self.assertNotIn('old',buckets)
    def test_idle_sessions_are_recycled_before_authenticated_ones(self):
        server.SESSIONS.clear();now=time.time()
        for index in range(server.IDLE_SESSION_CAP):
            server.SESSIONS['idle-'+str(index)]={'stage':'login','created':now+index/1000,'csrf':'fixture'}
        server.SESSIONS['access']={'stage':'dashboard','created':now,'csrf':'fixture','auth':{'user_id':1,'issued_at':now}}
        protected={
            'mfa':{'challenge':{'user_id':1}},
            'activation':{'activation':{'expires':now+300}},
            'camera':{'cctv_until':now+14400},
            'capability':{'capability_until':now+900},
        }
        for key,extra in protected.items():
            server.SESSIONS[key]={'stage':'login','created':now-100,'csrf':'fixture',**extra}
        sid,_=server.make_session()
        self.assertIn('access',server.SESSIONS);self.assertIn(sid,server.SESSIONS)
        for key in protected:self.assertIn(key,server.SESSIONS)
        self.assertLess(len(server.SESSIONS),server.IDLE_SESSION_CAP+2)

    def capability_request(self,path,body):
        handler=SimpleNamespace(client_address=('127.0.0.1',10),public_request=lambda:False)
        return server.Handler.public_capability_allowed(handler,path,body)

    def test_video_traffic_cannot_reset_auth_or_claim_budgets(self):
        with patch.object(h.time,'monotonic',return_value=100):
            self.assertTrue(h.rate_check(server.RATE,[('account:fixture',1)]))
            for _ in range(server.PUBLIC_CLAIM_TOKEN_LIMIT):
                self.assertTrue(self.capability_request('/api/scanner/claim',{'ticket':'fixture-ticket'}))
        with patch.object(h.time,'monotonic',return_value=102):
            self.assertTrue(self.capability_request('/api/browser-camera/upload-frame',{'phone_token':'camera'}))
            self.assertFalse(h.rate_check(server.RATE,[('account:fixture',1)]))
            self.assertFalse(self.capability_request('/api/scanner/claim',{'ticket':'fixture-ticket'}))

    def test_eight_camera_publishers_share_one_ip_without_spending_minute_budget(self):
        with patch.object(h.time,'monotonic',return_value=100):
            for camera in range(8):
                for _ in range(25):
                    self.assertTrue(self.capability_request('/api/browser-camera/upload-frame',{'phone_token':str(camera)}))
            self.assertEqual(server.RATE,{})
            for _ in range(server.FRAME_TOKEN_LIMIT-25):
                self.assertTrue(self.capability_request('/api/browser-camera/upload',{'phone_token':'0'}))
            self.assertFalse(self.capability_request('/api/browser-camera/upload',{'phone_token':'0'}))

    def test_private_camera_queries_do_not_spend_public_budget(self):
        for path in server.browser_cameras.PRIVATE|server.phone_links.PRIVATE:
            for _ in range(610):self.assertTrue(self.capability_request(path,{}))
        self.assertEqual(server.RATE,{})
        self.assertEqual(server.FRAME_RATE,{})

    def test_classroom_polling_budget_can_share_one_ip(self):
        with patch.object(h.time,'monotonic',return_value=100):
            for scanner in range(35):
                for _ in range(40):
                    self.assertTrue(self.capability_request('/api/scanner/poll',{'phone_token':'scanner-'+str(scanner)}))
            for camera in range(8):
                for _ in range(150):
                    self.assertTrue(self.capability_request('/api/browser-camera/poll',{'phone_token':'camera-'+str(camera)}))
    def test_new_session_flood_is_rate_limited(self):
        server.SESSIONS.clear();server.RATE.clear()
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        host='127.0.0.1:'+str(httpd.server_port)
        def request():
            connection=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=8)
            connection.request('GET','/api/session',headers={'Host':host})
            response=connection.getresponse();response.read();connection.close();return response.status
        try:
            for _ in range(server.NEW_SESSION_IP_LIMIT):self.assertEqual(request(),200)
            self.assertEqual(request(),429)
        finally:
            httpd.shutdown();httpd.server_close();server.SESSIONS.clear();server.RATE.clear()
    def test_public_claim_endpoints_limit_attempts_before_validation(self):
        server.SESSIONS.clear();server.RATE.clear()
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        host='127.0.0.1:'+str(httpd.server_port)
        server.SESSIONS['rate']={'stage':'login','created':time.time(),'csrf':'rate-csrf'}
        def claim(path,ticket):
            connection=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=8)
            connection.request('POST',path,json.dumps({'ticket':ticket}),{
                'Host':host,'Origin':'http://'+host,'Cookie':'st_session=rate',
                'X-CSRF-Token':'rate-csrf','Content-Type':'application/json'})
            response=connection.getresponse();response.read();connection.close();return response.status
        try:
            for path in ('/api/scanner/claim','/api/browser-camera/claim'):
                server.RATE.clear()
                statuses=[claim(path,('A'*28)+str(index).zfill(4)) for index in range(server.PUBLIC_CLAIM_IP_LIMIT)]
                self.assertTrue(all(status!=429 for status in statuses),path)
                self.assertEqual(claim(path,('A'*28)+'final'),429,path)
        finally:
            httpd.shutdown();httpd.server_close();server.SESSIONS.clear();server.RATE.clear()
    def test_proxy_headers_trusted_only_for_configured_local_connector(self):
        request=SimpleNamespace(public_request=lambda:True,server=SimpleNamespace(trusted_proxy='cloudflare'),client_address=('127.0.0.1',10),headers={'CF-Connecting-IP':'203.0.113.20'})
        self.assertEqual(h.client_key(request),'203.0.113.20')
        request.public_request=lambda:False;self.assertEqual(h.client_key(request),'127.0.0.1')
        request.public_request=lambda:True;request.client_address=('192.168.1.3',10);self.assertEqual(h.client_key(request),'192.168.1.3')
        request.client_address=('127.0.0.1',10);request.headers={'CF-Connecting-IP':'spoofed'};self.assertEqual(h.client_key(request),'127.0.0.1')
    def test_session_capacity_preserves_existing_sessions(self):
        server.SESSIONS.update({str(i):{'created':time.time(),'auth':{'user_id':i,'issued_at':time.time()}} for i in range(4096)})
        before=dict(server.SESSIONS)
        with self.assertRaises(server.SessionCapacity):server.make_session()
        self.assertEqual(server.SESSIONS,before)
    def test_http_validation_headers_activation_and_https_redirect(self):
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        cookie='';csrf='';host='127.0.0.1:'+str(httpd.server_port)
        def req(path,body=None,headers=None,raw=None):
            nonlocal cookie,csrf
            conn=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=8)
            hh={'Host':host,'Origin':'http://'+host,'Cookie':cookie,'X-CSRF-Token':csrf,'Content-Type':'application/json',**(headers or {})}
            data=raw if raw is not None else json.dumps(body) if body is not None else None
            conn.request('POST' if data is not None else 'GET',path,data,hh);r=conn.getresponse();content=r.read();out=dict(r.getheaders())
            if out.get('Set-Cookie'):cookie=out['Set-Cookie'].split(';')[0]
            try:value=json.loads(content)
            except ValueError:value={}
            csrf=value.get('csrf',csrf);conn.close();return r.status,value,out
        try:
            status,state,headers=req('/api/session');self.assertEqual(status,200)
            for field in ('roles','areas','demo','enrollment_key'):self.assertNotIn(field,state)
            self.assertNotIn('unsafe-inline',headers['Content-Security-Policy']);self.assertIn("object-src 'none'",headers['Content-Security-Policy'])
            self.assertIn('microphone=()',headers['Permissions-Policy'])
            for username,password in (([],''),('',None),({},[]),(1,1),('x','x'*73)):
                self.assertEqual(req('/api/auth/login',{'username':username,'password':password})[0],400)
            status,error,_=req('/api/auth/login',raw='{"password":');self.assertEqual(status,400);self.assertEqual(error,{'error':'JSON inválido.'})
            status,state,_=req('/api/auth/login',{'username':self.user['username'],'password':db.TEMP_PASSWORD});self.assertEqual(status,200);self.assertEqual(state['stage'],'activation');self.assertNotIn('enrollment_key',state)
            self.assertNotEqual(req('/api/auth/password',{'password':'PrivadaDePrueba123!'})[0],200)
            with sec.write_transaction() as c:ticket=h.activation_issue(c,self.user['username'],'test')
            self.assertEqual(req('/api/auth/activate',{'ticket':ticket})[1]['stage'],'password')
            status,state,_=req('/api/auth/password',{'password':'PrivadaDePrueba123!'});self.assertEqual(status,200);self.assertEqual(state['stage'],'enroll');self.assertIn('enrollment_key',state)
            httpd.public_origin='https://example.test';httpd.trusted_proxy='cloudflare'
            for path in ('/','/assets/app.js','/api/session','/missing'):
                status,_,headers=req(path,headers={'Host':'example.test','X-Forwarded-Proto':'https'})
                self.assertIn('max-age=31536000',headers['Strict-Transport-Security'])
                status,_,headers=req(path,headers={'Host':'example.test','X-Forwarded-Proto':'http'})
                self.assertEqual(status,308);self.assertEqual(headers['Location'],'https://example.test'+path)
        finally:httpd.shutdown();httpd.server_close()

if __name__=='__main__':unittest.main()
