import unittest
import test_backend as base
import features as f
import import_rfid_reference as importer
import rfid_cards

db, sec = base.db, base.secure


class ReferenceCards(unittest.TestCase):
    setUpClass = classmethod(base.Backend.setUpClass.__func__)
    login = base.Backend.login

    def setUp(self):
        base.Backend.setUp(self)
        with sec.write_transaction() as conn:
            importer.apply(conn)
        self.admin, _ = self.login(self.dpo)

    def scan(self, uid, zone):
        return f.dispatch(self.admin, 'POST', '/api/access/verify', {}, {'ref': uid, 'method': 'RFID_125KHZ', 'zone': zone})['result']

    def test_all_seven_codes_match_correct_accounts_and_areas(self):
        for username, role, area, cards, zones in importer.ASSIGNMENTS:
            user = next(x for x in self.users if x['username'] == username)
            if username != self.dpo['username']:
                self.login(user)
            for card in cards:
                for zone in db.ZONES:
                    result = self.scan(card, zone)
                    self.assertEqual(result['subject_id'], username)
                    self.assertEqual(result['verdict'], 'VERIFIED' if zone in zones else 'DENIED')

    def test_alias_duplicate_rejected_and_primary_revocation_clears_aliases(self):
        other = next(u for u in self.users if u['role'] == 'user')
        with self.assertRaises(ValueError):
            sec.update_user(self.admin, other['id'], rfid_uid='00007003')
        with sec.write_transaction() as conn:
            conn.execute('UPDATE users SET rfid_uid=NULL WHERE id=?', (self.dpo['id'],))
            user = conn.execute('SELECT * FROM users WHERE id=?', (self.dpo['id'],)).fetchone()
            self.assertEqual(rfid_cards.values(user), [])
            self.assertEqual(user['rfid_aliases'], '[]')
        self.assertEqual(self.scan('7003', db.ZONE_GENERAL)['verdict'], 'DENIED')

    def test_locked_account_and_unknown_card_still_denied(self):
        with sec.write_transaction() as conn:
            conn.execute('UPDATE users SET is_locked=1 WHERE username=?', ('9900003',))
        self.assertEqual(self.scan('0003333333', db.ZONE_CCTV)['verdict'], 'DENIED')
        self.assertEqual(self.scan('9999999', db.ZONE_GENERAL)['verdict'], 'DENIED')

    def test_missing_mfa_and_missing_license_still_denied(self):
        self.assertEqual(self.scan('0002222222', db.ZONE_SERVER)['verdict'], 'DENIED')
        user = next(u for u in self.users if u['username'] == '9900004')
        self.login(user)
        with sec.write_transaction() as conn:
            conn.execute('DELETE FROM user_licenses WHERE matricula=?', (user['username'],))
        self.assertEqual(self.scan('0002222222', db.ZONE_SERVER)['verdict'], 'DENIED')


if __name__ == '__main__':
    unittest.main()
