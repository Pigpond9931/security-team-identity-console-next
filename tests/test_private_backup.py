from contextlib import closing
from pathlib import Path
import hashlib,json,os,sqlite3,subprocess,sys,tempfile,unittest
from unittest.mock import patch
import test_backend as base
import features,maintenance


class PrivateBackup(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):base.Backend.setUp(self);self.login(self.dpo)

    def test_manifest_complete_protected_and_restore_keeps_factors(self):
        features.qr_key()
        receipt=base.server.DATA/'test-receipt.dpapi'
        receipt.write_bytes(base.secure.store.protect(b'fictitious receipt'))
        try:
            with tempfile.TemporaryDirectory(prefix='SecurityTeamBackup-') as parent:
                dest=Path(parent)/'snapshot';maintenance.backup(dest)
                manifest=json.loads((dest/'backup-manifest.json').read_text())
                names={r['name'] for r in manifest['files']}
                self.assertTrue({'identity.sqlite','.mfa-key','.qr-key','test-receipt.dpapi'}<=names)
                for record in manifest['files']:
                    self.assertEqual(hashlib.sha256((dest/record['name']).read_bytes()).hexdigest(),record['sha256'])
                self.assertTrue(base.secure.store.directory_acl(dest)['protected'])
                before=(dest/'.mfa-key').read_bytes()
                env=dict(os.environ,ST_DATA_DIR=str(dest));env.pop('ST_TEST_MODE',None)
                code="import server;server.initialize();\nwith server.db.get_connection() as c:\n rows=c.execute('SELECT mfa_secret FROM users WHERE mfa_configured=1').fetchall();assert rows and all(server.secure.decrypt_secret(r[0]) for r in rows)\n"
                run=subprocess.run([sys.executable,'-c',code],cwd=base.ROOT,env=env,capture_output=True,timeout=30)
                self.assertEqual(run.returncode,0,run.stderr.decode(errors='replace'))
                self.assertEqual((dest/'.mfa-key').read_bytes(),before)
                self.assertEqual((dest/'.qr-key').read_bytes(),(base.server.DATA/'.qr-key').read_bytes())
        finally:receipt.unlink(missing_ok=True)

    def test_backup_inside_repository_and_existing_destination_are_rejected(self):
        with self.assertRaises(ValueError):maintenance.backup(base.ROOT/'backups')
        with tempfile.TemporaryDirectory(prefix='SecurityTeamBackup-') as dest:
            with self.assertRaises(ValueError):maintenance.backup(dest)

    def test_missing_database_does_not_create_one_or_destination(self):
        with tempfile.TemporaryDirectory(prefix='SecurityTeamBackup-') as parent:
            missing=Path(parent)/'missing.sqlite';dest=Path(parent)/'snapshot'
            with patch.object(base.db,'DB_PATH',str(missing)),self.assertRaises(ValueError):maintenance.backup(dest)
            self.assertFalse(missing.exists());self.assertFalse(dest.exists())


if __name__=='__main__':unittest.main()
