import json,unittest
import test_backend as base
import features as f


class QrReadiness(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):
        base.Backend.setUp(self)
        self.admin,_=self.login(self.dpo)
        self.person,_=self.login(self.user)
        with base.db.get_connection() as c:
            c.execute('UPDATE users SET allowed_zones=? WHERE id=?',(json.dumps(['GENERAL_ACCESS','DATA_CENTER_VAULT']),self.user['id']))

    def badge(self):return f.dispatch(self.person,'GET','/api/users/qr-badge',{}, {})['badge']

    def test_assigned_zone_without_license_is_visible_but_pending(self):
        badge=self.badge();statuses={row['zone']:row['ready'] for row in badge['access_requirements']}
        self.assertEqual(statuses,{'GENERAL_ACCESS':True,'DATA_CENTER_VAULT':False})
        self.assertGreater(badge['expires_at'],0);self.assertTrue(badge['token'])
        self.assertEqual(f.verify(badge['token'],'BADGE')['sv'],base.record(self.user['id'])['security_version'])

    def test_refresh_reflects_license_and_revocation_without_weakening_scan(self):
        before=base.record(self.user['id'])['security_version']
        f.dispatch(self.admin,'POST','/api/users/assign-license',{},dict(matricula=self.user['username'],license_id='LIC-DC-VAULT'))
        self.assertTrue(self.badge()['access_requirements'][1]['ready'])
        f.dispatch(self.admin,'POST','/api/users/revoke-license',{},dict(matricula=self.user['username'],license_id='LIC-DC-VAULT'))
        badge=self.badge();self.assertFalse(badge['access_requirements'][1]['ready'])
        self.assertEqual(before,base.record(self.user['id'])['security_version'])
        result=f.dispatch(self.admin,'POST','/api/access/verify',{},dict(zone='DATA_CENTER_VAULT',method='QR_BADGE',direction='AUTO',ref=badge['token']))['result']
        self.assertEqual(result['verdict'],'DENIED')


if __name__=='__main__':unittest.main()
