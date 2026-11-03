"""Removal, shared slots, live revocation and HTTP authorization with temporary data."""
import http.client,json,threading,time,unittest
from unittest.mock import patch
import test_backend as base
import browser_cameras as bc
import camera_hub as hub
import features as f
db,sec,server=base.db,base.secure,base.server

class CameraRemoval(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):
        base.Backend.setUp(self);bc.CHANNELS.clear();hub.stop_all()
        auth,_=self.login(self.dpo);self.state={'stage':'dashboard','auth':auth,'created':time.time(),'csrf':'owner-csrf'}
        server.SESSIONS.update(owner=self.state,other=self.state)
        self.alive=lambda sid,auth:sid in server.SESSIONS and server.SESSIONS[sid].get('auth')==auth
        self.addCleanup(hub.stop_all)
    def feature(self,path,body=None,auth=None):return f.dispatch(auth or self.state['auth'],'GET' if body is None else 'POST',path,{},body or {})
    def cam(self,p,b=None,sid='owner',state=None):return bc.dispatch('/api/browser-camera/'+p,b or {},sid,self.state if state is None else state,self.alive)
    def ip(self,count=1):
        urls=['http://192.168.70.'+str(i+10)+':8081/video' for i in range(count)]
        for url in urls:self.feature('/api/cctv/destinations',{'action':'approve','url':url})
        self.feature('/api/cctv/channels',{'channels':[{'name':'IP '+str(i+1),'url':url,'profile':'smooth'} for i,url in enumerate(urls)]})
        return self.feature('/api/cctv/channels')['channels']
    def remove(self,ch,auth=None):return self.feature('/api/cctv/remove',{'id':ch['id'],'expected':{k:ch[k] for k in ('name','url','profile','updated_at')}},auth)
    def test_remove_one_ip_preserves_other_channels_and_approval(self):
        first,second=self.ip(2)
        with patch.object(hub,'reconcile',wraps=hub.reconcile) as reconcile:self.remove(first);reconcile.assert_called_once_with([second])
        self.assertEqual(self.feature('/api/cctv/channels')['channels'],[second])
        self.assertEqual(self.feature('/api/cctv/destinations')['destinations'][0]['status'],'approved')
        with db.get_connection() as c:self.assertEqual(c.execute("SELECT COUNT(*) FROM audit_log WHERE action='CCTV_IP_REMOVED'").fetchone()[0],1)
    def test_stale_ip_selection_cannot_delete_a_replaced_channel(self):
        ch=self.ip()[0]
        with db.get_connection() as c:c.execute('UPDATE camera_channels SET name=? WHERE id=?',('Otro dispositivo',ch['id']))
        with self.assertRaises(f.Conflict):self.remove(ch)
        self.assertEqual(self.feature('/api/cctv/channels')['channels'][0]['name'],'Otro dispositivo')
        with self.assertRaises(ValueError):self.feature('/api/cctv/remove',{'id':True,'expected':{}})
    def test_deleting_ip_stops_capture_and_frees_slot_for_browser(self):
        ch=self.ip()[0]
        class Feed:
            stop=threading.Event();condition=threading.Condition()
        feed=Feed();hub._feeds[ch['id']]=((ch['url'],ch['profile']),feed)
        for n in range(7):self.cam('create',{'name':str(n),'zone':'GENERAL_ACCESS'})
        self.assertEqual(self.cam('list')['available_slots'],0)
        with self.assertRaises(ValueError):self.cam('create',{'name':'Nueva','zone':'GENERAL_ACCESS'})
        self.remove(ch);self.assertTrue(feed.stop.is_set());self.assertEqual(self.cam('list')['available_slots'],1)
        self.cam('create',{'name':'Nueva','zone':'GENERAL_ACCESS'});self.assertEqual(self.cam('list')['total_channels'],8)
    def test_other_camera_administrator_can_remove_but_cannot_pair(self):
        monitor=next(u for u in self.users if u['role']=='user' and u['area']=='Monitoring' and not u['is_guard'])
        auth,_=self.login(monitor);self.feature('/api/users/assign-license',{'matricula':monitor['username'],'license_id':'LIC-CCTV-ADMIN'})
        other={**self.state,'auth':auth};server.SESSIONS['camera-admin']=other
        ch=self.cam('create',{'name':'Móvil de otra sesión','zone':'GENERAL_ACCESS'});phone=self.cam('claim',{'ticket':ch['ticket']},state={})
        listed=self.cam('list',sid='camera-admin',state=other)['channels'][0];self.assertTrue(listed['can_manage']);self.assertFalse(listed['can_pair'])
        with self.assertRaises(PermissionError):self.cam('approve',{'id':ch['id'],'confirmation':phone['confirmation']},sid='camera-admin',state=other)
        self.cam('revoke',{'id':ch['id']},sid='camera-admin',state=other)
        with self.assertRaises(PermissionError):self.cam('poll',{'phone_token':phone['phone_token']},state={})
    def test_read_only_monitor_cannot_remove_ip_or_browser(self):
        ch=self.ip()[0];web=self.cam('create',{'name':'Móvil','zone':'GENERAL_ACCESS'})
        monitor=next(u for u in self.users if u['role']=='user' and u['area']=='Monitoring' and not u['is_guard']);auth,_=self.login(monitor);state={**self.state,'auth':auth};server.SESSIONS['monitor']=state
        with self.assertRaises(PermissionError):self.remove(ch,auth)
        with self.assertRaises(PermissionError):self.cam('revoke',{'id':web['id']},sid='monitor',state=state)
        self.assertFalse(self.cam('list',sid='monitor',state=state)['channels'][0]['can_manage'])
    def test_browser_removal_wakes_waiter_and_releases_capacity(self):
        web=self.cam('create',{'name':'Móvil','zone':'GENERAL_ACCESS'});phone=self.cam('claim',{'ticket':web['ticket']},state={});self.cam('approve',{'id':web['id'],'confirmation':phone['confirmation']})
        peer=self.cam('view',{'id':web['id']});key={'id':web['id'],'peer':peer['peer']};bc.stream_open(key,'owner',self.state,self.alive)
        started=threading.Event();closed=[]
        def wait():
            started.set()
            try:bc.stream_latest(key,0,5)
            except PermissionError:closed.append(True)
        thread=threading.Thread(target=wait);thread.start();started.wait(1)
        self.cam('revoke',{'id':web['id']},sid='other');thread.join(1)
        self.assertFalse(thread.is_alive());self.assertEqual(closed,[True]);self.assertEqual(self.cam('list')['available_slots'],8)
    def test_late_viewer_signal_is_not_a_revoked_phone_capability(self):
        web=self.cam('create',{'name':'Móvil','zone':'GENERAL_ACCESS'});phone=self.cam('claim',{'ticket':web['ticket']},state={});self.cam('approve',{'id':web['id'],'confirmation':phone['confirmation']})
        peer=self.cam('view',{'id':web['id']});self.cam('leave',{'id':web['id'],'peer':peer['peer']})
        with self.assertRaises(f.Conflict):self.cam('signal',{'phone_token':phone['phone_token'],'peer':peer['peer'],'message':{'type':'candidate','candidate':{}}},state={})
        self.assertEqual(self.cam('poll',{'phone_token':phone['phone_token'],'publishing':True},state={})['status'],'paired')
    def start_http(self):
        httpd=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler);threading.Thread(target=httpd.serve_forever,daemon=True).start()
        self.addCleanup(httpd.server_close);self.addCleanup(httpd.shutdown);return httpd.server_port
    def post(self,port,path,body,headers=None):
        c=http.client.HTTPConnection('127.0.0.1',port,timeout=5);c.request('POST',path,json.dumps(body),headers=headers or {'Origin':'http://127.0.0.1:'+str(port),'Content-Type':'application/json','X-CSRF-Token':'owner-csrf','Cookie':'st_session=owner'})
        response=c.getresponse();result=(response.status,json.loads(response.read()));c.close();return result
    def test_expired_browser_tickets_do_not_block_saving_new_ip(self):
        ch=self.ip()[0];self.remove(ch)
        for n in range(8):self.cam('create',{'name':str(n),'zone':'GENERAL_ACCESS'})
        for entry in bc.CHANNELS.values():entry['expires']=0
        port=self.start_http();status,result=self.post(port,'/api/cctv/channels',{'channels':[ch]})
        self.assertEqual(status,200,result);self.assertEqual(len(result['channels']),1);self.assertFalse(bc.CHANNELS)
    def test_http_remove_enforces_csrf_origin_and_stale_confirmation(self):
        ch=self.ip()[0];port=self.start_http();body={'id':ch['id'],'expected':{k:ch[k] for k in ('name','url','profile','updated_at')}}
        headers={'Origin':'http://127.0.0.1:'+str(port),'Content-Type':'application/json','X-CSRF-Token':'owner-csrf','Cookie':'st_session=owner'}
        for field in ('Origin','X-CSRF-Token','Cookie'):
            altered=dict(headers);altered.pop(field);self.assertIn(self.post(port,'/api/cctv/remove',body,altered)[0],(401,403))
        wrong={**body,'expected':{**body['expected'],'name':'Cambió'}};self.assertEqual(self.post(port,'/api/cctv/remove',wrong)[0],409)
        self.assertEqual(self.post(port,'/api/cctv/remove',body)[0],200);self.assertFalse(self.feature('/api/cctv/channels')['channels'])

if __name__=='__main__':unittest.main()
