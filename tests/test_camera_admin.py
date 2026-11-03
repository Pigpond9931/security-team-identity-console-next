import time,unittest
from unittest.mock import patch
import test_backend as base
import features as f
import browser_cameras as bc
db,sec=base.db,base.secure

class CameraAdmin(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):
        base.Backend.setUp(self);bc.CHANNELS.clear()
        self.monitor=next(u for u in self.users if u['role']=='user' and u['area']=='Monitoring' and not u['is_guard'])
        self.auth,_=self.login(self.monitor);self.admin,_=self.login(self.dpo)
    def req(self,path,body=None,auth=None):return f.dispatch(auth or self.auth,'GET' if body is None else 'POST',path,{},body or {})
    def grant(self):return self.req('/api/users/assign-license',{'matricula':self.monitor['username'],'license_id':'LIC-CCTV-ADMIN'},self.admin)
    def test_camera_administrator_can_configure_ip_and_create_browser_camera(self):
        self.assertFalse(self.req('/api/cctv/channels')['can_edit']);self.grant()
        self.assertTrue(self.req('/api/cctv/channels')['can_edit'])
        self.req('/api/cctv/destinations',{'action':'approve','url':'http://192.168.10.20:8081/video'},self.admin)
        self.req('/api/cctv/channels',{'channels':[{'name':'Prueba','url':'http://192.168.10.20:8081/video','profile':'smooth'}]})
        with patch.object(f.camera_hub,'probe',return_value={'ok':True}) as probe:
            self.assertTrue(self.req('/api/cctv/test',{'url':'http://192.168.10.20:8081/video'})['ok']);probe.assert_called_once()
        self.assertIn('server_addresses',self.req('/api/cctv/network'))
        state={'stage':'dashboard','created':time.time(),'auth':self.auth}
        created=bc.dispatch('/api/browser-camera/create',{'name':'Móvil','zone':'GENERAL_ACCESS'},'owner',state,lambda sid,auth:True)
        self.assertEqual(created['status'],'waiting')
    def test_permission_does_not_grant_user_management_or_physical_access(self):
        before=base.record(self.monitor['id']);self.grant();self.assertEqual(base.record(self.monitor['id']),before)
        snapshot=sec.dashboard_data(self.auth);self.assertEqual([u['id'] for u in snapshot['users']],[self.monitor['id']])
        with self.assertRaises(PermissionError):sec.update_user(self.auth,self.user['id'],role='system_admin')
        with self.assertRaises(PermissionError):self.req('/api/users/zones',{'matricula':self.user['username'],'zones':['SERVER_ROOM']})
        with self.assertRaises(PermissionError):self.req('/api/users/assign-license',{'matricula':self.monitor['username'],'license_id':'LIC-CCTV-ADMIN'})
        with self.assertRaises(PermissionError):self.req('/api/access/settings',{'rfid_capacity':40})
    def test_area_leader_cannot_grant_or_revoke_camera_administration(self):
        leader=next(u for u in self.users if u['role']=='area_admin' and u['area']=='Monitoring');auth,_=self.login(leader)
        for action in ('assign-license','revoke-license'):
            with self.assertRaises(PermissionError):self.req('/api/users/'+action,{'matricula':self.monitor['username'],'license_id':'LIC-CCTV-ADMIN'},auth)
    def test_revocation_stops_camera_operations_and_scoped_phone(self):
        self.grant();state={'stage':'dashboard','created':time.time(),'auth':self.auth};alive=lambda sid,auth:True
        def camera(path,body,state_override=None):return bc.dispatch('/api/browser-camera/'+path,body,'owner',state if state_override is None else state_override,alive)
        link=camera('create',{'name':'Móvil','zone':'GENERAL_ACCESS'});phone=camera('claim',{'ticket':link['ticket']},{})
        camera('approve',{'id':link['id'],'confirmation':phone['confirmation']})
        self.req('/api/users/revoke-license',{'matricula':self.monitor['username'],'license_id':'LIC-CCTV-ADMIN'},self.admin)
        self.assertFalse(self.req('/api/cctv/channels')['can_edit'])
        with self.assertRaises(PermissionError):self.req('/api/cctv/channels',{'channels':[]})
        with self.assertRaises(PermissionError):camera('poll',{'phone_token':phone['phone_token']},{})
        self.assertFalse(bc.CHANNELS)
    def test_view_permission_alone_is_not_camera_administration(self):
        auth,_=self.login(self.user)
        self.req('/api/users/assign-license',{'matricula':self.user['username'],'license_id':'LIC-CCTV-MON'},self.admin)
        self.assertFalse(self.req('/api/cctv/channels',auth=auth)['can_edit'])
        with self.assertRaises(PermissionError):self.req('/api/cctv/test',{'url':'http://192.168.1.5:8081/video'},auth)
        with self.assertRaises(ValueError):
            self.grant();self.req('/api/cctv/test',{'url':'http://127.0.0.1:8765/api/data'})

if __name__=='__main__':unittest.main()
