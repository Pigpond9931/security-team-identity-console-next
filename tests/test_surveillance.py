"""Continuous video, ordering, revocation and HTTP limits using fictitious identities."""
import http.client,io,json,threading,time,unittest
from urllib.parse import urlencode
from PIL import Image
import test_backend as base
import browser_cameras as bc
import features as f

server=base.server;db=base.db
class Surveillance(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):
        base.Backend.setUp(self);bc.CHANNELS.clear()
        auth,_=self.login(self.dpo)
        self.state={'stage':'dashboard','created':time.time(),'auth':auth,'csrf':'csrf-test'}
        server.SESSIONS.update(owner=self.state,viewer=self.state,phone={'stage':'login','created':time.time(),'csrf':'phone-csrf'})
        self.alive=lambda sid,auth:sid in server.SESSIONS and server.SESSIONS[sid].get('auth')==auth
        buf=io.BytesIO();Image.new('RGB',(64,48),'green').save(buf,'JPEG');self.raw=buf.getvalue()
    def req(self,p,b=None,sid='owner',state=None):
        return bc.dispatch('/api/browser-camera/'+p,b or {},sid,self.state if state is None else state,self.alive)
    def pair(self):
        ch=self.req('create',{'name':'Laboratorio ficticio','zone':'GENERAL_ACCESS'})
        phone=self.req('claim',{'ticket':ch['ticket']},sid='phone',state={})
        self.req('approve',{'id':ch['id'],'confirmation':phone['confirmation']})
        peer=self.req('view',{'id':ch['id']},sid='viewer')
        return ch,phone,{'id':ch['id'],'peer':peer['peer']}
    def upload(self,phone,seq,raw=None):
        return self.req('upload-frame',{'phone_token':phone['phone_token'],'_raw_jpeg':self.raw if raw is None else raw,'source_seq':seq},sid='phone',state={})
    def test_latest_frame_discards_out_of_order_and_has_no_queue(self):
        ch,p,key=self.pair();bc.stream_open(key,'viewer',self.state,self.alive)
        self.assertTrue(self.upload(p,200)['accepted']);self.assertFalse(self.upload(p,199)['accepted'])
        self.assertTrue(self.upload(p,201)['accepted'])
        seq,raw,captured=bc.stream_latest(key,0,0)
        self.assertEqual(seq,2);self.assertEqual(raw,self.raw);self.assertLess(time.time()-captured,1)
        self.assertTrue(self.req('poll',{'phone_token':p['phone_token']},state={})['fallback'])
        self.assertNotIn('frame_raw',self.req('list')['channels'][0])
    def test_stream_peer_is_bound_to_authenticated_session(self):
        _,_,key=self.pair()
        with self.assertRaises(PermissionError):bc.stream_open(key,'owner',self.state,self.alive)
        bc.stream_open(key,'viewer',self.state,self.alive)
        self.req('leave',key,sid='viewer')
        with self.assertRaises(PermissionError):bc.stream_latest(key,0,0)
    def test_viewer_permission_revocation_stops_existing_view(self):
        _,_,key=self.pair();reader=next(u for u in self.users if u['role']=='user' and u['area']=='Access Control' and not u['is_guard']);auth,_=self.login(reader)
        f.dispatch(self.state['auth'],'POST','/api/users/assign-license',{},dict(matricula=reader['username'],license_id='LIC-CCTV-MON'))
        state={**self.state,'auth':auth};server.SESSIONS['reader']=state
        v=self.req('view',{'id':key['id']},'reader',state);read=dict(id=key['id'],peer=v['peer'])
        bc.stream_open(read,'reader',state,self.alive)
        f.dispatch(self.state['auth'],'POST','/api/users/revoke-license',{},dict(matricula=reader['username'],license_id='LIC-CCTV-MON'))
        with self.assertRaises(PermissionError):bc.stream_open(read,'reader',state,self.alive)
    def test_binary_payload_bounded_and_not_an_arbitrary_file(self):
        _,p,_=self.pair()
        for raw in (b'bad-jpeg',b'x'*195001):
            with self.assertRaises(ValueError):self.upload(p,100,raw)
        with self.assertRaises(ValueError):self.upload(p,0)
        with self.assertRaises(PermissionError):self.upload({'phone_token':'not-a-valid-producer-capability'},100)
    def test_waiting_for_frame_does_not_block_signaling(self):
        _,p,key=self.pair();bc.stream_open(key,'viewer',self.state,self.alive)
        waiting=threading.Event();result=[]
        def wait():waiting.set();result.append(bc.stream_latest(key,0,2))
        t=threading.Thread(target=wait);t.start();waiting.wait(1)
        start=time.monotonic();self.req('viewer-poll',key,sid='viewer');self.upload(p,1);t.join(2)
        self.assertFalse(t.is_alive());self.assertLess(time.monotonic()-start,1);self.assertEqual(result[0][1],self.raw)
    def httpd(self):
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        self.addCleanup(httpd.server_close);self.addCleanup(httpd.shutdown)
        return httpd.server_port
    def test_http_stream_continuous_binary_and_revokes_on_logout(self):
        _,p,key=self.pair();port=self.httpd();viewer=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
        viewer.request('GET','/api/browser-camera/stream?'+urlencode(key),headers={'Cookie':'st_session=viewer'})
        response=viewer.getresponse();self.assertEqual(response.status,200)
        self.assertIn('multipart/x-mixed-replace',response.getheader('Content-Type'))
        self.assertIn('no-transform',response.getheader('Cache-Control'))
        for source in (1,2,3):
            producer=http.client.HTTPConnection('127.0.0.1',port,timeout=3)
            producer.request('POST','/api/browser-camera/upload-frame',body=self.raw,headers={'Origin':'http://127.0.0.1:'+str(port),'Content-Type':'image/jpeg','X-CSRF-Token':'phone-csrf','X-Frame-Sequence':str(source),'Cookie':'st_session=phone; st_camera='+p['phone_token']})
            uploaded=producer.getresponse();self.assertEqual(uploaded.status,200);self.assertTrue(json.loads(uploaded.read())['accepted']);producer.close()
            self.assertEqual(response.readline(),b'--STFRAME\r\n')
            self.assertEqual(response.readline(),b'Content-Type: image/jpeg\r\n')
            length=int(response.readline().split(b':')[1]);self.assertEqual(response.readline(),b'\r\n')
            self.assertEqual(response.read(length),self.raw);self.assertEqual(response.read(2),b'\r\n')
        server.SESSIONS.pop('viewer');self.assertEqual(response.read(),b'');viewer.close()
    def test_http_requires_login_origin_csrf_and_producer_cookie(self):
        _,p,key=self.pair();port=self.httpd()
        def request(method,path,body=None,headers=None):
            c=http.client.HTTPConnection('127.0.0.1',port,timeout=3);c.request(method,path,body=body,headers=headers or {});r=c.getresponse();status=r.status;r.read();c.close();return status
        self.assertEqual(request('GET','/api/browser-camera/stream?'+urlencode(key)),401)
        h={'Origin':'http://127.0.0.1:'+str(port),'Content-Type':'image/jpeg','X-CSRF-Token':'phone-csrf','X-Frame-Sequence':'1','Cookie':'st_session=phone; st_camera='+p['phone_token']}
        for header in ('Origin','X-CSRF-Token','Cookie'):
            bad=dict(h);bad.pop(header);self.assertEqual(request('POST','/api/browser-camera/upload-frame',self.raw,bad),403)
        self.assertEqual(request('POST','/api/browser-camera/upload-frame',b'x'*195001,h),400)
        h['Content-Type']='application/json';self.assertEqual(request('POST','/api/browser-camera/upload-frame',b'{}',h),400)

if __name__=='__main__':unittest.main()
