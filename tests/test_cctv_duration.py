"""Plazos absolutos de CCTV, cookies, QR y retirada de permisos con reloj simulado."""
import http.client,json,threading,time,unittest
from unittest.mock import patch
import test_backend as base
import browser_cameras as bc
import features as f

server,sec,db=base.server,base.secure,base.db

class CCTVLifetime(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):
        base.Backend.setUp(self);bc.CHANNELS.clear()
        auth,_=self.login(self.dpo)
        self.state={'stage':'dashboard','created':time.time(),'auth':auth,'csrf':'owner-csrf'}
        self.handler=object.__new__(server.Handler)
        self.handler.state_payload(self.state)
        server.SESSIONS['owner']=self.state
        self.start=auth['issued_at']
    def request(self,action,body=None,sid='owner',state=None):
        return bc.dispatch('/api/browser-camera/'+action,body or {},sid,self.state if state is None else state,self.handler.camera_owner_alive)
    def pair(self):
        ch=self.request('create',{'name':'Prueba de duración','zone':'GENERAL_ACCESS'})
        phone=self.request('claim',{'ticket':ch['ticket']},'phone',{})
        result=self.request('approve',{'id':ch['id'],'confirmation':phone['confirmation']})
        return ch,phone,result
    def test_camera_survives_half_hour_and_cleanup_but_expires_at_four_hours(self):
        ch,phone,result=self.pair()
        self.assertEqual(result['expires'],self.start+14400)
        for elapsed in (1801,14399):
            with patch('time.time',return_value=self.start+elapsed):
                with server.SESSION_LOCK:server.make_session()
                self.assertIn('owner',server.SESSIONS)
                self.assertEqual(self.request('poll',{'phone_token':phone['phone_token']},'phone',{})['status'],'paired')
                self.assertIsNotNone(sec.current_user(self.state['auth']))
        with patch('time.time',return_value=self.start+14400):
            with self.assertRaises(PermissionError):self.request('poll',{'phone_token':phone['phone_token']},'phone',{})
            self.assertIsNone(sec.current_user(self.state['auth']))
            with server.SESSION_LOCK:server.make_session()
            self.assertNotIn('owner',server.SESSIONS)
    def test_pair_qr_is_single_use_and_still_expires_in_five_minutes(self):
        ch=self.request('create',{'name':'QR temporal','zone':'GENERAL_ACCESS'})
        self.assertLessEqual(ch['expires']-time.time(),300)
        with patch('time.time',return_value=ch['expires']):
            with self.assertRaises(PermissionError):self.request('claim',{'ticket':ch['ticket']},'phone',{})
        ch=self.request('create',{'name':'Un uso','zone':'GENERAL_ACCESS'})
        self.request('claim',{'ticket':ch['ticket']},'phone',{})
        with self.assertRaises(PermissionError):self.request('claim',{'ticket':ch['ticket']},'phone',{})
    def test_ordinary_user_and_scanner_keep_half_hour_limit(self):
        user=next(u for u in self.users if u['role']=='user' and u['area']=='Access Control' and not u['is_guard'])
        auth,_=self.login(user)
        normal={'stage':'dashboard','created':auth['issued_at'],'auth':auth,'csrf':'normal'}
        self.handler.state_payload(normal)
        self.assertNotIn('cctv_session',auth)
        self.assertEqual(server.state_deadline(normal),auth['issued_at']+1800)
        with patch('time.time',return_value=auth['issued_at']+1801):self.assertIsNone(sec.current_user(auth))
        import phone_links
        phone_links.LINKS.clear()
        link=phone_links.dispatch('/api/scanner/create',{'zone':'GENERAL_ACCESS','direction':'AUTO'},'owner',self.state,self.handler.camera_owner_alive)
        self.assertLessEqual(link['expires_at'],self.state['created']+1800)
    def test_logout_and_manual_revoke_cut_camera_before_deadline(self):
        _,phone,_=self.pair();server.SESSIONS.pop('owner')
        with self.assertRaises(PermissionError):self.request('poll',{'phone_token':phone['phone_token']},'phone',{})
        server.SESSIONS['owner']=self.state
        ch,phone,_=self.pair();self.request('revoke',{'id':ch['id']})
        with self.assertRaises(PermissionError):self.request('poll',{'phone_token':phone['phone_token']},'phone',{})
    def test_permission_removal_invalidates_extended_session_and_existing_channel(self):
        _,phone,_=self.pair()
        with db.get_connection() as c:c.execute("UPDATE users SET role='user',area='Access Control',is_guard=0 WHERE id=?",(self.dpo['id'],))
        self.assertIsNone(sec.current_user(self.state['auth']))
        with self.assertRaises(PermissionError):self.request('poll',{'phone_token':phone['phone_token']},'phone',{})
    def test_http_phone_session_and_producer_cookie_survive_half_hour(self):
        ch=self.request('create',{'name':'Teléfono HTTP','zone':'GENERAL_ACCESS'})
        server.SESSIONS['phone']={'stage':'login','created':time.time(),'csrf':'phone-csrf'}
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        self.addCleanup(httpd.server_close);self.addCleanup(httpd.shutdown)
        def post(action,body,cookie):
            c=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=3)
            c.request('POST','/api/browser-camera/'+action,json.dumps(body),{'Origin':'http://127.0.0.1:'+str(httpd.server_port),'X-CSRF-Token':'phone-csrf','Content-Type':'application/json','Cookie':cookie})
            r=c.getresponse();result=(r.status,dict(r.getheaders()),r.getheaders(),json.loads(r.read()));c.close();return result
        status,_,headers,phone=post('claim',{'ticket':ch['ticket']},'st_session=phone')
        self.assertEqual(status,200)
        camera=next(v for k,v in headers if k.lower()=='set-cookie' and v.startswith('st_camera='))
        self.assertIn('Max-Age=14400',camera);self.assertIn('HttpOnly',camera)
        token=camera.split(';')[0]
        self.request('approve',{'id':ch['id'],'confirmation':phone['confirmation']})
        with patch('time.time',return_value=self.start+1801):
            status,_,headers,result=post('poll',{'publishing':True},'st_session=phone; '+token)
            self.assertEqual(status,200);self.assertEqual(result['status'],'paired')
            cookie=next(v for k,v in headers if k.lower()=='set-cookie' and v.startswith('st_session='))
            self.assertGreater(int(cookie.split('Max-Age=')[1].split(';')[0]),12000)

if __name__=='__main__':unittest.main()

