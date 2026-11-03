"""Regresión de instalación limpia; no utiliza ni imprime credenciales reales."""
from pathlib import Path
from contextlib import closing
import os, subprocess, sys, tempfile, unittest, sqlite3

ROOT=Path(__file__).resolve().parents[1]
class Bootstrap(unittest.TestCase):
    def test_fresh_admin_individual_grant_no_demo_and_existing_database_preserved(self):
        (ROOT/'tests/scratch').mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=ROOT/'tests/scratch') as temp:
            env=dict(os.environ,ST_DATA_DIR=temp)
            env.pop('ST_TEST_MODE',None);env.pop('ST_DEMO_SEED',None)
            result=subprocess.run([sys.executable,str(ROOT/'bootstrap_admin.py')],input='9900100\nAdministrador Ficticio\n',text=True,capture_output=True,env=env,cwd=ROOT,timeout=60)
            self.assertEqual(result.returncode,0,result.stderr)
            database=Path(temp)/'identity.sqlite'
            with closing(sqlite3.connect(database)) as c:
                user=c.execute('SELECT username,role,must_change_password,mfa_configured,is_active FROM users').fetchall()
                self.assertEqual(user,[('9900100','system_admin',1,0,1)])
                self.assertEqual(c.execute('SELECT COUNT(*) FROM initial_password_grants WHERE used_at IS NULL').fetchone()[0],1)
            before=database.read_bytes()
            again=subprocess.run([sys.executable,str(ROOT/'bootstrap_admin.py')],input='',text=True,capture_output=True,env=env,cwd=ROOT,timeout=30)
            self.assertNotEqual(again.returncode,0)
            self.assertEqual(before,database.read_bytes())

    def test_invalid_identity_creates_no_database(self):
        with tempfile.TemporaryDirectory(dir=ROOT/'tests/scratch') as temp:
            env=dict(os.environ,ST_DATA_DIR=temp)
            env.pop('ST_TEST_MODE',None);env.pop('ST_DEMO_SEED',None)
            result=subprocess.run([sys.executable,str(ROOT/'bootstrap_admin.py')],input='invalida\nX\n',text=True,capture_output=True,env=env,cwd=ROOT,timeout=30)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((Path(temp)/'identity.sqlite').exists())

if __name__=='__main__':unittest.main()
