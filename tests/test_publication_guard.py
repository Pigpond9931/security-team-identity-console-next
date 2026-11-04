import unittest
import test_backend as base


class PublicationGuard(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login

    def setUp(self):base.Backend.setUp(self)

    def test_new_system_administrator_does_not_require_a_dpo(self):
        self.login(self.dpo)
        with base.db.get_connection() as c:
            c.execute("UPDATE users SET role='system_admin' WHERE id=?",(self.dpo['id'],))
            self.assertTrue(base.secure.publication_ready(c))

    def test_ordinary_user_with_complete_factors_is_not_enough(self):
        self.login(self.user)
        with base.db.get_connection() as c:self.assertFalse(base.secure.publication_ready(c))

    def test_pending_policy_locked_inactive_and_missing_factors_prevent_publication(self):
        self.login(self.dpo)
        for field,value in [('terms_version','previous'),('terms_accepted',0),('is_locked',1),('is_active',0),('mfa_configured',0),('must_change_password',1)]:
            with base.db.get_connection() as c:
                before=c.execute('SELECT '+field+' FROM users WHERE id=?',(self.dpo['id'],)).fetchone()[0]
                c.execute('UPDATE users SET '+field+'=? WHERE id=?',(value,self.dpo['id']))
                self.assertFalse(base.secure.publication_ready(c),field)
                c.execute('UPDATE users SET '+field+'=? WHERE id=?',(before,self.dpo['id']))


if __name__=='__main__':unittest.main()
