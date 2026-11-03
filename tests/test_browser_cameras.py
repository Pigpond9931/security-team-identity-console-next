import time,unittest,base64,io
from PIL import Image
import test_backend as base
import browser_cameras as bc
import phone_links
db,sec=base.db,base.secure
class BrowserCameras(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):
        base.Backend.setUp(self);bc.CHANNELS.clear();self.auth,_=self.login(self.dpo)
        self.state={'stage':'dashboard','created':time.time(),'auth':self.auth};self.parents={'owner':self.state,'viewer':self.state}
    def alive(self,sid,auth):return sid in self.parents and self.parents[sid]['auth']==auth
    def req(self,p,b=None,sid='owner',state=None):return bc.dispatch('/api/browser-camera/'+p,b or {},sid,self.state if state is None else state,self.alive)
    def pair(self):
        ch=self.req('create',{'name':'Puerta A','zone':'GENERAL_ACCESS'});phone=self.req('claim',{'ticket':ch['ticket']},sid='phone',state={})
        self.req('approve',{'id':ch['id'],'confirmation':phone['confirmation']});return ch,phone
    def test_confirmation_and_ticket_are_scoped_single_use(self):
        ch=self.req('create',{'name':'A','zone':'GENERAL_ACCESS'});p=self.req('claim',{'ticket':ch['ticket']},state={})
        with self.assertRaises(PermissionError):self.req('claim',{'ticket':ch['ticket']},state={})
        with self.assertRaises(PermissionError):self.req('upload',{'phone_token':p['phone_token'],'jpeg':'YWJj'},state={})
        with self.assertRaises(ValueError):self.req('approve',{'id':ch['id'],'confirmation':'incorrecto'})
        with self.assertRaises(PermissionError):self.req('approve',{'id':ch['id'],'confirmation':p['confirmation']},sid='viewer')
    def test_signals_are_private_to_viewer_and_direction(self):
        ch,p=self.pair();v=self.req('view',{'id':ch['id']},sid='viewer');key={'id':ch['id'],'peer':v['peer']}
        self.req('viewer-signal',{**key,'message':{'type':'offer','sdp':'v=0'}},sid='viewer')
        with self.assertRaises(PermissionError):self.req('viewer-poll',key,sid='owner')
        poll=self.req('poll',{'phone_token':p['phone_token'],'publishing':True},state={});self.assertEqual(poll['messages'][0]['type'],'offer')
        self.req('signal',{'phone_token':p['phone_token'],'peer':v['peer'],'message':{'type':'answer','sdp':'v=0'}},state={})
        self.assertEqual(self.req('viewer-poll',key,sid='viewer')['messages'][0]['type'],'answer')
        with self.assertRaises(ValueError):self.req('signal',{'phone_token':p['phone_token'],'peer':v['peer'],'message':{'type':'offer','sdp':'v=0'}},state={})
        with self.assertRaises(PermissionError):phone_links.dispatch('/api/scanner/poll',{'phone_token':p['phone_token']},'phone',{},self.alive)
    def test_fallback_latest_frame_limits_and_expiry(self):
        ch,p=self.pair();v=self.req('view',{'id':ch['id']},sid='viewer');key={'id':ch['id'],'peer':v['peer']}
        self.req('frame',key,sid='viewer');self.assertTrue(self.req('poll',{'phone_token':p['phone_token']},state={})['fallback'])
        buf=io.BytesIO();Image.new('RGB',(64,48),'green').save(buf,format='JPEG');jpeg=base64.b64encode(buf.getvalue()).decode()
        self.req('upload',{'phone_token':p['phone_token'],'jpeg':jpeg},state={});bc.CHANNELS[ch['id']]['peers'][v['peer']]['frame_at']=0
        self.assertEqual(self.req('frame',key,sid='viewer')['jpeg'],jpeg)
        bc.CHANNELS[ch['id']]['uploaded']=0
        with self.assertRaises(ValueError):self.req('upload',{'phone_token':p['phone_token'],'jpeg':'YWJj'},state={})
        with self.assertRaises(ValueError):self.req('upload',{'phone_token':p['phone_token'],'jpeg':'A'*260001},state={})
        self.parents.pop('owner')
        with self.assertRaises(PermissionError):self.req('poll',{'phone_token':p['phone_token']},state={})
        self.assertFalse(bc.CHANNELS)
    def test_permissions_view_limits_and_revoke(self):
        reader=next(u for u in self.users if u['role']=='user' and not u['is_guard'] and u['area']=='Access Control');auth,_=self.login(reader)
        with self.assertRaises(PermissionError):self.req('create',{'name':'A','zone':'GENERAL_ACCESS'},state={**self.state,'auth':auth})
        ch,p=self.pair()
        for _ in range(4):self.req('view',{'id':ch['id']})
        with self.assertRaises(ValueError):self.req('view',{'id':ch['id']})
        self.req('revoke',{'id':ch['id']})
        with self.assertRaises(PermissionError):self.req('poll',{'phone_token':p['phone_token']},state={})
        for i in range(8):self.req('create',{'name':str(i),'zone':'GENERAL_ACCESS'})
        with self.assertRaises(ValueError):self.req('create',{'name':'9','zone':'GENERAL_ACCESS'})
    def test_permission_changes_stop_publishing_and_no_credentials_exposed(self):
        ch,p=self.pair();status=self.req('poll',{'phone_token':p['phone_token']},state={})
        for key in ('auth','sid','phone_hash','ticket_hash','frame'):self.assertNotIn(key,status)
        with db.get_connection() as c:c.execute('UPDATE users SET is_locked=1 WHERE id=?',(self.dpo['id'],))
        with self.assertRaises(PermissionError):self.req('poll',{'phone_token':p['phone_token']},state={})

if __name__=='__main__':unittest.main()
