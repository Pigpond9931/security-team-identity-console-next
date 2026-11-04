"""Cuatro identidades en F1, tarjetas desconocidas y conservación de áreas."""
import json,unittest
import test_backend as base
import features as f
import four_person_access as four

db,sec=base.db,base.secure
class FourPersons(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):
        base.Backend.setUp(self);self.admin,_=self.login(self.dpo)
        self.selected=[self.dpo]+[u for u in self.users if u['role']=='area_admin'][:3]
        self.extra=next(u for u in self.users if u['role']=='user' and not u['is_guard'])
        self.cards={u['username']:str(80000001+i) for i,u in enumerate(self.selected+[self.extra])}
        for user in self.selected[1:]+[self.extra]:self.login(user)
        with db.get_connection() as c:
            for u in self.selected+[self.extra]:c.execute('UPDATE users SET rfid_uid=? WHERE id=?',(self.cards[u['username']],u['id']))
        self.before={u['id']:base.record(u['id']) for u in self.users}
        with sec.write_transaction() as c:four.configure(c,[u['username'] for u in self.selected])
    def scan(self,user=None,zone=four.ZONE,ref=None):
        return f.dispatch(self.admin,'POST','/api/access/verify',{},dict(zone=zone,method='RFID_125KHZ',direction='AUTO',ref=ref or self.cards[user['username']]))['result']
    def test_four_allow_fifth_and_unknown_deny_and_exit_recorded(self):
        for u in self.selected:self.assertEqual(self.scan(u)['verdict'],'VERIFIED')
        self.assertEqual(self.scan(self.extra)['verdict'],'DENIED')
        self.assertEqual(self.scan(ref='9999999911')['verdict'],'DENIED')
        self.assertEqual(self.scan(self.selected[0])['direction'],'CHECK_OUT')
    def test_other_zones_roles_and_credentials_preserved_and_fifth_entitlement_rejected(self):
        for u in self.users:
            old=self.before[u['id']];new=base.record(u['id'])
            for key in ('role','area','password_hash','mfa_secret','mfa_configured','rfid_uid'):self.assertEqual(old[key],new[key])
            self.assertEqual(set(json.loads(old['allowed_zones']))-{four.ZONE},set(json.loads(new['allowed_zones']))-{four.ZONE})
        with self.assertRaises(f.Conflict):f.dispatch(self.admin,'POST','/api/users/assign-license',{},dict(matricula=self.extra['username'],license_id=four.LICENSE))
        with self.assertRaises(ValueError):f.dispatch(self.admin,'POST','/api/access/settings',{},dict(rfid_capacity=5))
    def test_selection_must_have_exactly_four_registered_cards(self):
        with sec.write_transaction() as c:
            with self.assertRaises(ValueError):four.configure(c,[self.selected[0]['username']]*4)
            with self.assertRaises(ValueError):four.configure(c,[u['username'] for u in self.selected][:3]+['UNKNOWN'])
    def test_guest_cannot_bypass_four_identity_restriction(self):
        # Un pase de invitado válido no se convierte en la quinta identidad de F1.
        out=f.dispatch(self.admin,'POST','/api/visitors/create',{},dict(full_name='Invitado de prueba',organization='Prueba',purpose='Ensayo',host_matricula=self.dpo['username'],allowed_zone=four.ZONE,duration='2h',terms_accepted=True))
        with db.get_connection() as c:
            visitor=c.execute('SELECT * FROM visitors ORDER BY rowid DESC LIMIT 1').fetchone()
            c.execute('UPDATE visitors SET terms_accepted=1,terms_version=? WHERE visitor_id=?',(db.TERMS_VERSION,visitor['visitor_id']))
            visitor=c.execute('SELECT * FROM visitors WHERE visitor_id=?',(visitor['visitor_id'],)).fetchone()
            badge=f.badge(c,'VISITOR',visitor)
        result=f.dispatch(self.admin,'POST','/api/access/verify',{},dict(zone=four.ZONE,method='QR_BADGE',direction='AUTO',ref=badge['token']))['result']
        self.assertEqual(result['verdict'],'DENIED');self.assertIn('cuatro',result['reason'])

if __name__=='__main__':unittest.main()
