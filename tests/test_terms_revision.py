"""Un aviso nuevo no reutiliza la aceptación previa de cuentas o visitantes."""
import unittest
import test_backend as base
import features as f

db,sec=base.db,base.secure

class TermsRevision(unittest.TestCase):
 setUpClass=classmethod(base.Backend.setUpClass.__func__)
 login=base.Backend.login
 def setUp(self):
  base.Backend.setUp(self);self.admin,_=self.login(self.dpo);self.person,_=self.login(self.user)
 def test_account_must_explicitly_accept_current_revision(self):
  with db.get_connection() as c:
   c.execute('UPDATE users SET terms_version=? WHERE id=?',('v1.0',self.user['id']))
   before=dict(c.execute('SELECT * FROM users WHERE id=?',(self.user['id'],)).fetchone())
  with self.assertRaises(PermissionError):f.dispatch(self.person,'GET','/api/licenses',{}, {})
  with self.assertRaises(ValueError):f.dispatch(self.person,'POST','/api/auth/accept-terms',{}, {'accepted':True,'version':'v1.0'})
  f.dispatch(self.person,'POST','/api/auth/accept-terms',{}, {'accepted':True,'version':db.TERMS_VERSION})
  with db.get_connection() as c:
   after=c.execute('SELECT * FROM users WHERE id=?',(self.user['id'],)).fetchone();self.assertTrue(f.accepted(after))
   for name in ('role','area','password_hash','mfa_secret','rfid_uid','security_version'):self.assertEqual(before[name],after[name])
   self.assertTrue(c.execute("SELECT 1 FROM audit_log WHERE action='TERMS_ACCEPTED' AND target=? AND details LIKE ?",(self.user['username'],'%version='+db.TERMS_VERSION+'%')).fetchone())
 def test_old_visitor_acceptance_cannot_issue_or_use_current_badge(self):
  out=f.dispatch(self.admin,'POST','/api/visitors/create',{}, {'full_name':'Invitado de prueba','allowed_zone':'GENERAL_ACCESS','duration':'2h','terms_accepted':True})
  vid=out['visitor']['visitor_id'];token=out['badge']['token'];self.assertTrue(token)
  with db.get_connection() as c:c.execute('UPDATE visitors SET terms_version=? WHERE visitor_id=?',('v1.0',vid))
  body={'ref':token,'zone':'GENERAL_ACCESS','method':'QR_BADGE','direction':'AUTO'}
  denied=f.dispatch(self.admin,'POST','/api/access/verify',{},body)['result'];self.assertEqual(denied['verdict'],'DENIED')
  with sec.write_transaction() as c:
   visitor=c.execute('SELECT * FROM visitors WHERE visitor_id=?',(vid,)).fetchone();self.assertIsNone(f.badge(c,'VISITOR',visitor)['token'])
   data=f.pass_payload(c,{'tipo':'VISITOR','ref':vid},True);self.assertTrue(data['terms']['accepted']);self.assertTrue(data['badge']['token'])
   visitor=c.execute('SELECT * FROM visitors WHERE visitor_id=?',(vid,)).fetchone();self.assertEqual(visitor['terms_version'],db.TERMS_VERSION)
  rows=f.dispatch(self.admin,'GET','/api/visitors',{}, {})['visitors'];self.assertEqual(next(v for v in rows if v['visitor_id']==vid)['terms_accepted'],1)
 def test_migration_preserves_legacy_acceptance_without_upgrading_it(self):
  out=f.dispatch(self.admin,'POST','/api/visitors/create',{}, {'full_name':'Invitado antiguo','allowed_zone':'GENERAL_ACCESS','duration':'2h','terms_accepted':True})
  vid=out['visitor']['visitor_id']
  with db.get_connection() as c:
   c.execute('UPDATE visitors SET terms_version=NULL WHERE visitor_id=?',(vid,));before=dict(c.execute('SELECT * FROM visitors WHERE visitor_id=?',(vid,)).fetchone())
  db.migrate_extensions();db.migrate_extensions()
  with db.get_connection() as c:
   after=dict(c.execute('SELECT * FROM visitors WHERE visitor_id=?',(vid,)).fetchone());self.assertEqual(before,after);self.assertFalse(f.accepted(after))
  rows=f.dispatch(self.admin,'GET','/api/visitors',{}, {})['visitors'];self.assertEqual(next(v for v in rows if v['visitor_id']==vid)['terms_accepted'],0)

if __name__=='__main__':unittest.main()
