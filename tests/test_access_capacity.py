"""A visitor restriction is independent from the approved identity quota."""
import unittest
import test_backend as base
import features as f


class AccessCapacity(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login

    def setUp(self):
        base.Backend.setUp(self)
        self.admin,_=self.login(self.dpo)
        with base.db.get_connection() as c:
            c.execute("INSERT OR REPLACE INTO access_settings VALUES('restricted_four_enabled','1')")
            c.execute("INSERT OR REPLACE INTO access_settings VALUES('rfid_capacity','12')")
            c.execute("UPDATE licenses_catalog SET seats=12 WHERE license_id='LIC-DC-VAULT'")

    def test_existing_approved_quota_does_not_revert_to_four(self):
        result=f.dispatch(self.admin,'POST','/api/access/settings',{},dict(rfid_capacity=12))
        self.assertEqual(result['capacity'],12)
        with base.db.get_connection() as c:
            self.assertEqual(c.execute("SELECT seats FROM licenses_catalog WHERE license_id='LIC-DC-VAULT'").fetchone()[0],12)
            self.assertEqual(c.execute("SELECT value FROM access_settings WHERE key='restricted_four_enabled'").fetchone()[0],'1')

    def test_reduction_cannot_orphan_assigned_licenses(self):
        with base.db.get_connection() as c:
            c.execute("DELETE FROM user_licenses WHERE license_id='LIC-DC-VAULT'")
            for user in self.users[:2]:
                c.execute('INSERT INTO user_licenses(matricula,license_id,assigned_by,assigned_at) VALUES(?,?,?,?)',(user['username'],'LIC-DC-VAULT','fixture',base.db._now()))
        with self.assertRaises(f.Conflict):
            f.dispatch(self.admin,'POST','/api/access/settings',{},dict(rfid_capacity=1))
        self.assertEqual(f.dispatch(self.admin,'GET','/api/access/settings',{}, {})['capacity'],12)

    def test_ordinary_user_cannot_change_quota(self):
        actor,_=self.login(self.user)
        with self.assertRaises(PermissionError):
            f.dispatch(actor,'POST','/api/access/settings',{},dict(rfid_capacity=20))


if __name__=='__main__':unittest.main()
