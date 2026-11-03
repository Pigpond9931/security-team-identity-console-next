"""Contraseña común temporal, separación de privilegios y desbloqueo."""
import unittest
import test_backend as base
import features as f
import initial_passwords as ip
import test_initial_passwords as original

db,sec,server=base.db,base.secure,base.server
class GroupOnboarding(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):
        base.Backend.setUp(self);self.admin,_=self.login(self.dpo)
        self.user=next(u for u in self.users if u['role']=='user' and u['area']=='Access Control' and not u['is_guard'])
    def issue(self,user=None):return f.dispatch(self.admin,'POST','/api/users/initial-password-group',{},dict(acknowledged=True))
    def test_one_password_per_group_distinct_hashes_and_preserved_configured_accounts(self):
        before=base.record(self.dpo['id']);out=self.issue();self.assertGreater(len(out['issued']),1)
        self.assertEqual(before,base.record(self.dpo['id']))
        hashes=[]
        for user in out['issued']:
            result=sec.authenticate(user['matricula'],out['temporary_password'])
            self.assertEqual(result['status'],'ok');hashes.append(base.record(result['user']['id'])['password_hash'])
        self.assertEqual(len(set(hashes)),len(hashes))
        with db.get_connection() as c:self.assertNotIn(out['temporary_password'],str([tuple(r) for r in c.execute('SELECT * FROM audit_log')]))
    def test_privileged_and_locked_accounts_keep_their_credentials(self):
        target=self.user
        f.dispatch(self.admin,'POST','/api/users/assign-license',{},dict(matricula=target['username'],license_id='LIC-CCTV-ADMIN'))
        locked=next(u for u in self.users if u['role']=='user' and u['id']!=target['id'])
        sec.update_user(self.admin,locked['id'],is_locked=1)
        protected={u['id']:base.record(u['id']) for u in self.users if u['role']!='user' or u['id'] in (target['id'],locked['id'])}
        out=self.issue();issued={u['matricula'] for u in out['issued']}
        for uid,before in protected.items():
            self.assertEqual(before,base.record(uid));self.assertNotIn(before['username'],issued)
    def test_grant_consumed_separately_and_reissue_invalidates_old_password(self):
        out=self.issue();users=out['issued'][:2]
        for user in users:
            auth=sec.authenticate(user['matricula'],out['temporary_password'])
            with sec.write_transaction() as c:self.assertTrue(ip.claim(c,auth['user'],{}))
            with sec.write_transaction() as c:
                with self.assertRaises(ValueError):ip.claim(c,auth['user'],{})
        newer=self.issue()
        self.assertEqual(sec.authenticate(self.user['username'],out['temporary_password'])['status'],'invalid')
        self.assertEqual(sec.authenticate(self.user['username'],newer['temporary_password'])['status'],'ok')
    def test_confirmation_scope_and_expiry(self):
        with self.assertRaises(ValueError):f.dispatch(self.admin,'POST','/api/users/initial-password-group',{}, {})
        ordinary,_=self.login(self.user)
        with self.assertRaises(PermissionError):f.dispatch(ordinary,'POST','/api/users/initial-password-group',{},dict(acknowledged=True))
        out=self.issue();target=out['issued'][0];auth=sec.authenticate(target['matricula'],out['temporary_password'])
        with sec.write_transaction() as c:
            c.execute('UPDATE initial_password_grants SET expires=0')
            with self.assertRaises(ValueError):ip.claim(c,auth['user'],{})
    def test_http_shared_first_login_still_requires_private_password_mfa_and_terms(self):
        original.InitialPasswords.test_http_complete_first_login_without_activation_link(self)
    def test_privilege_added_after_group_issuance_requires_individual_enrollment(self):
        out=self.issue();auth=sec.authenticate(self.user['username'],out['temporary_password'])
        with self.assertRaises(ValueError):f.dispatch(self.admin,'POST','/api/users/assign-license',{},dict(matricula=self.user['username'],license_id='LIC-CCTV-ADMIN'))
        with sec.write_transaction() as c:
            c.execute("INSERT INTO user_licenses(matricula,license_id,assigned_by,assigned_at) VALUES(?,?,?,?)",(self.user['username'],'LIC-CCTV-ADMIN',self.dpo['username'],db._now()))
            with self.assertRaises(ValueError):ip.claim(c,auth['user'],{})
        individual=f.dispatch(self.admin,'POST','/api/users/initial-password',{},dict(matricula=self.user['username']))
        auth=sec.authenticate(self.user['username'],individual['temporary_password'])
        with sec.write_transaction() as c:self.assertTrue(ip.claim(c,auth['user'],{}))
    def test_unlock_resets_attempts_preserves_factors_and_is_audited(self):
        auth,_=self.login(self.user);before=base.record(self.user['id'])
        sec.update_user(self.admin,self.user['id'],is_locked=1)
        with db.get_connection() as c:c.execute('UPDATE users SET failed_attempts=5 WHERE id=?',(self.user['id'],))
        sec.update_user(self.admin,self.user['id'],is_locked=0)
        after=base.record(self.user['id'])
        self.assertEqual((after['is_locked'],after['failed_attempts']),(0,0))
        for key in ('password_hash','mfa_secret','mfa_configured','ever_enrolled','rfid_uid','allowed_zones'):self.assertEqual(before[key],after[key])
        self.assertIsNone(sec.current_user(auth))
        with db.get_connection() as c:self.assertEqual(c.execute("SELECT COUNT(*) FROM audit_log WHERE action='ACCOUNT_UNLOCKED' AND target=?",(self.user['username'],)).fetchone()[0],1)
    def test_area_admin_cannot_unlock_global_or_other_area(self):
        lead=next(u for u in self.users if u['role']=='area_admin' and u['area']=='Access Control');auth,_=self.login(lead)
        other=next(u for u in self.users if u['role']=='user' and u['area']!='Access Control')
        for target in (self.dpo,other):
            with self.assertRaises(PermissionError):sec.update_user(auth,target['id'],is_locked=0)

if __name__=='__main__':unittest.main()
