"""Primer ingreso individual con bases temporales; no imprime contraseñas."""
import concurrent.futures
import http.client
import json
import threading
import unittest
from unittest.mock import patch
import test_backend as base
import features as f
import initial_passwords as ip
import hardening
import pyotp

db, sec, server = base.db, base.secure, base.server


class InitialPasswords(unittest.TestCase):
    setUpClass = classmethod(base.Backend.setUpClass.__func__)
    login = base.Backend.login

    def setUp(self):
        base.Backend.setUp(self)
        self.admin, _ = self.login(self.dpo)

    def issue(self, user=None):
        return f.dispatch(self.admin, 'POST', '/api/users/initial-password', {}, {'matricula': (user or self.user)['username']})

    def test_issue_preserves_identity_cards_zones_and_never_logs_secret(self):
        before = base.records()
        out = self.issue()
        self.assertTrue(out['single_use'])
        for old, new in zip(before, base.records()):
            allowed = {'password_hash', 'must_change_password', 'security_version', 'updated_at'} if old['id'] == self.user['id'] else set()
            self.assertTrue(all(old[k] == new[k] for k in old if k not in allowed))
        with db.get_connection() as c:
            for row in c.execute('SELECT * FROM audit_log'):
                self.assertNotIn(out['temporary_password'], str(tuple(row)))
            self.assertNotIn(out['temporary_password'], str([tuple(r) for r in c.execute('SELECT * FROM initial_password_grants')]))

    def test_one_use_concurrent_claim_and_no_cross_account(self):
        out = self.issue()
        auth = sec.authenticate(self.user['username'], out['temporary_password'])
        def claim(_):
            state = {}
            try:
                with sec.write_transaction() as c:
                    ip.claim(c, auth['user'], state)
                return True
            except ValueError:
                return False
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(claim, range(2))), 1)

    def test_expiry_reissue_and_old_password_revocation(self):
        first = self.issue()
        auth = sec.authenticate(self.user['username'], first['temporary_password'])
        second = self.issue()
        with sec.write_transaction() as c:
            with self.assertRaises(ValueError):
                ip.claim(c, auth['user'], {})
            c.execute('UPDATE initial_password_grants SET expires=0')
        current = sec.authenticate(self.user['username'], second['temporary_password'])
        with sec.write_transaction() as c:
            with self.assertRaises(ValueError):
                ip.claim(c, current['user'], {})
        self.assertEqual(sec.authenticate(self.user['username'], first['temporary_password'])['status'], 'invalid')

    def test_global_scope_and_enrolled_identity_protection(self):
        leader = next(u for u in self.users if u['role'] == 'area_admin')
        auth, _ = self.login(leader)
        with self.assertRaises(PermissionError):
            f.dispatch(auth, 'POST', '/api/users/initial-password', {}, {'matricula': self.user['username']})
        before = base.record(leader['id'])
        with self.assertRaises(ValueError):
            self.issue(leader)
        self.assertEqual(before, base.record(leader['id']))

    def test_new_account_and_unenrolled_reset_are_ready_without_qr(self):
        new_password = sec.create_user(self.admin, 'PRIMER-INGRESO', 'Persona temporal', 'user', db.AREA_AC)
        with sec.write_transaction() as c:
            user = c.execute('SELECT * FROM users WHERE username=?', ('PRIMER-INGRESO',)).fetchone()
            self.assertTrue(ip.claim(c, sec.public_user(user), {}))
        reset = sec.reset_password(self.admin, self.user['id'])
        auth = sec.authenticate(self.user['username'], reset)
        with sec.write_transaction() as c:
            self.assertTrue(ip.claim(c, auth['user'], {}))
        self.assertNotEqual(new_password, reset)

    def test_shared_password_does_not_authorize_enrollment(self):
        auth = sec.authenticate(self.user['username'], db.TEMP_PASSWORD)
        state = {}
        with sec.write_transaction() as c:
            self.assertFalse(ip.claim(c, auth['user'], state))
        self.assertFalse(hardening.activation_valid(state, auth['user']))

    def test_http_complete_first_login_without_activation_link(self):
        out = self.issue()
        httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        cookie = ''; csrf = ''; host = '127.0.0.1:' + str(httpd.server_port)
        def req(path, body=None):
            nonlocal cookie, csrf
            conn = http.client.HTTPConnection('127.0.0.1', httpd.server_port, timeout=8)
            headers = {'Host': host, 'Origin': 'http://' + host, 'Cookie': cookie, 'X-CSRF-Token': csrf, 'Content-Type': 'application/json'}
            conn.request('GET' if body is None else 'POST', path, None if body is None else json.dumps(body), headers)
            response = conn.getresponse(); value = json.loads(response.read()); status = response.status
            if response.getheader('Set-Cookie'):
                cookie = response.getheader('Set-Cookie').split(';')[0]
            csrf = value.get('csrf', csrf); conn.close()
            return status, value
        try:
            req('/api/session')
            status, state = req('/api/auth/login', {'username': self.user['username'], 'password': out['temporary_password']})
            self.assertEqual((status, state['stage']), (200, 'password'))
            self.assertNotIn('enrollment_key', state)
            self.assertNotEqual(req('/api/data')[0], 200)
            self.assertEqual(req('/api/auth/password', {'password': out['temporary_password']})[0], 400)
            status, state = req('/api/auth/password', {'password': 'MiPrivadaNueva123!'})
            self.assertEqual((status, state['stage']), (200, 'enroll'))
            secret = state['enrollment_key']
            status, state = req('/api/auth/mfa', {'code': pyotp.TOTP(secret).now()})
            self.assertEqual((status, state['stage']), (200, 'backup'))
            self.assertEqual(req('/api/auth/backup-saved', {})[1]['stage'], 'terms')
            req('/api/auth/accept-terms', {'accepted': True, 'version': db.TERMS_VERSION})
            self.assertEqual(req('/api/data')[0], 200)
            req('/api/auth/logout', {})
            status, state = req('/api/auth/login', {'username': self.user['username'], 'password': 'MiPrivadaNueva123!'})
            self.assertEqual((status, state['stage']), (200, 'mfa'))
            self.assertNotIn('enrollment_key', state)
        finally:
            httpd.shutdown(); httpd.server_close()


if __name__ == '__main__':
    unittest.main()
