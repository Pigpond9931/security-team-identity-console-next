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
                from runtime_paths import STORE_MARKER
                self.assertTrue({'identity.sqlite','.mfa-key','.qr-key','test-receipt.dpapi',STORE_MARKER}<=names)
                for record in manifest['files']:
                    self.assertEqual(hashlib.sha256((dest/record['name']).read_bytes()).hexdigest(),record['sha256'])
                self.assertTrue(base.secure.store.directory_acl(dest)['protected'])
                before=(dest/'.mfa-key').read_bytes()
                env=dict(os.environ,ST_DATA_DIR=str(dest));env.pop('ST_TEST_MODE',None)
                token=features.sign({'purpose':'BADGE','tipo':'USER','ref':self.dpo['username'],'sv':0,'exp':int(__import__('time').time()+300)})
                code="import server,sys;server.initialize();\nwith server.db.get_connection() as c:\n rows=c.execute('SELECT mfa_secret FROM users WHERE mfa_configured=1').fetchall();assert rows and all(server.secure.decrypt_secret(r[0]) for r in rows)\nassert server.features.verify(sys.stdin.read(),'BADGE')['tipo']=='USER'\n"
                run=subprocess.run([sys.executable,'-c',code],input=token.encode(),cwd=base.ROOT,env=env,capture_output=True,timeout=30)
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

    def test_missing_qr_key_refuses_backup_without_regeneration(self):
        key=base.server.DATA/'.qr-key';saved=key.read_bytes();key.unlink()
        try:
            with tempfile.TemporaryDirectory(prefix='SecurityTeamMissingQr-') as parent:
                destination=Path(parent)/'snapshot'
                with self.assertRaises(ValueError):maintenance.backup(destination)
                self.assertFalse(destination.exists());self.assertFalse(key.exists())
        finally:base.secure.store.atomic_write(key,saved)

    def test_cli_backup_preserves_old_schema_and_source_keys_before_initialization(self):
        with tempfile.TemporaryDirectory(prefix='SecurityTeamLegacyBackup-') as parent:
            source=Path(parent)/'source';source.mkdir();dest=Path(parent)/'snapshot'
            database=source/'identity.sqlite'
            with closing(sqlite3.connect(database)) as c:
                c.execute('CREATE TABLE users(id INTEGER PRIMARY KEY,mfa_secret TEXT)')
                c.execute('INSERT INTO users VALUES(1,?)',('fernet:fictitious-old-ciphertext',))
                c.execute('PRAGMA user_version=7');c.commit()
            # Deliberately older raw key representation. Backup must preserve it,
            # not migrate or regenerate it as server.initialize() would attempt.
            from cryptography.fernet import Fernet
            (source/'.mfa-key').write_bytes(Fernet.generate_key())
            (source/'.qr-key').write_bytes(base.secure.store.protect(b'fictitious-qr-key'))
            before={p.name:p.read_bytes() for p in source.iterdir()}
            env=dict(os.environ,ST_DATA_DIR=str(source))
            result=subprocess.run([sys.executable,str(base.ROOT/'maintenance.py'),'backup',str(dest)],
                cwd=base.ROOT,env=env,capture_output=True,text=True,timeout=30)
            self.assertEqual(result.returncode,0,result.stderr)
            for name,content in before.items():self.assertEqual((source/name).read_bytes(),content,name)
            with closing(sqlite3.connect(dest/'identity.sqlite')) as c:
                self.assertEqual(c.execute('PRAGMA user_version').fetchone()[0],7)
                self.assertEqual([r[1] for r in c.execute('PRAGMA table_info(users)')],['id','mfa_secret'])
                self.assertEqual(c.execute('SELECT mfa_secret FROM users').fetchone()[0],'fernet:fictitious-old-ciphertext')
            for name in ('.mfa-key','.qr-key'):self.assertEqual((dest/name).read_bytes(),before[name])
            self.assertTrue((dest/'backup-manifest.json').is_file())


if __name__=='__main__':unittest.main()
