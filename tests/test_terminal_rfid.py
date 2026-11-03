"""Adaptación de referencia RFID; solo base temporal e identidades ficticias."""
import concurrent.futures,unittest
import test_backend as base
import features as f,access_terminal as terminal
db,sec=base.db,base.secure

class TerminalRFID(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):base.Backend.setUp(self);self.admin,_=self.login(self.dpo)
    def req(self,path,body=None,auth=None):return f.dispatch(auth or self.admin,'GET' if body is None else 'POST',path,{},body or {})
    def prepare(self,user,uid):
        auth,_=self.login(user);sec.update_user(self.admin,user['id'],rfid_uid=uid);return auth
    def scan(self,uid,direction='AUTO',zone='GENERAL_ACCESS'):
        return self.req('/api/access/verify',{'ref':uid,'method':'RFID_125KHZ','zone':zone,'direction':direction})['result']
    def test_areas_use_existing_zones_without_changing_permissions(self):
        before=base.records();out=self.req('/api/access/terminal')
        self.assertEqual([a['key'] for a in out['areas']],['F1','F2','F3','F4'])
        self.assertEqual([a['zone'] for a in out['areas']],['DATA_CENTER_VAULT','SERVER_ROOM','MONITORING_CCTV','GENERAL_ACCESS'])
        self.assertEqual(out['occupancy_limit'],0);self.assertEqual(before,base.records())
    def test_regular_user_denied_and_area_operator_sees_only_scope(self):
        auth=self.prepare(self.user,'1194')
        with self.assertRaises(PermissionError):self.req('/api/access/terminal',auth=auth)
        leader=next(u for u in self.users if u['role']=='area_admin' and u['area']==db.AREA_AC);auth,_=self.login(leader)
        out=self.req('/api/access/terminal',auth=auth);self.assertFalse(out['can_configure'])
        self.assertEqual({a['zone'] for a in out['areas'] if a['enabled']},set(f.operator_zones(base.record(leader['id']))))
        with self.assertRaises(PermissionError):self.req('/api/access/terminal-settings',{'occupancy_limit':3},auth)
    def test_cap_blocks_new_entry_but_allows_exit_without_account_lock(self):
        self.prepare(self.user,'001194');other=next(u for u in self.users if u['role']=='user' and u['id']!=self.user['id']);self.prepare(other,'555555')
        self.req('/api/access/terminal-settings',{'occupancy_limit':1})
        self.assertEqual(self.scan('1194')['verdict'],'VERIFIED')
        for _ in range(3):self.assertIn('Aforo lleno',self.scan('555555')['reason'])
        self.assertEqual(base.record(other['id'])['failed_attempts'],0);self.assertFalse(base.record(other['id'])['is_locked'])
        self.assertEqual(self.scan('0001194')['direction'],'CHECK_OUT')
        self.assertEqual(self.scan('555555')['verdict'],'VERIFIED')
        self.assertEqual(self.req('/api/access/terminal')['inside_count'],1)
    def test_concurrent_last_place_is_atomic(self):
        users=[u for u in self.users if u['role']=='user'][:2]
        for i,u in enumerate(users):self.prepare(u,str(700+i))
        self.req('/api/access/terminal-settings',{'occupancy_limit':1})
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(self.scan,['700','701']))
        self.assertEqual(sum(e['verdict']=='VERIFIED' for e in results),1)
        self.assertEqual(self.req('/api/access/terminal')['inside_count'],1)
    def test_capacity_does_not_bypass_licenses_or_zone_permissions(self):
        auth=self.prepare(self.user,'1194');before=base.record(self.user['id'])
        self.req('/api/access/terminal-settings',{'occupancy_limit':0})
        self.assertEqual(self.scan('1194',zone='DATA_CENTER_VAULT')['verdict'],'DENIED')
        self.assertEqual(base.record(self.user['id']),before)
    def test_invalid_limit_and_scoped_event_history(self):
        for value in (-1,501,True,'3',None):
            with self.assertRaises(ValueError):self.req('/api/access/terminal-settings',{'occupancy_limit':value})
        event=self.scan('9999999');out=self.req('/api/access/terminal');self.assertEqual(out['events'][0]['id'],event['id'])
        self.assertEqual(out['inside_count'],0)

if __name__=='__main__':unittest.main()
