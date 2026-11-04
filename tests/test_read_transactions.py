import concurrent.futures,sqlite3,threading,unittest
from pathlib import Path
from unittest.mock import patch
import test_backend as base
import features as f


class ReadTransactions(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    def setUp(self):
        base.Backend.setUp(self)
        self.admin,_=self.login(self.dpo)

    def test_get_never_uses_the_writer_transaction(self):
        with patch.object(base.secure,'write_transaction',side_effect=AssertionError('GET reserved the writer')):
            self.assertIn('licenses',f.dispatch(self.admin,'GET','/api/licenses',{},{}))

    def test_query_only_prevents_an_accidental_write_in_get(self):
        def accidental_write(c):
            c.execute("INSERT INTO access_settings VALUES('accidental-read-write','1')")
        with patch.object(f,'catalog',side_effect=accidental_write),self.assertRaises(sqlite3.OperationalError):
            f.dispatch(self.admin,'GET','/api/licenses',{}, {})
        with base.db.get_connection() as c:
            self.assertIsNone(c.execute("SELECT 1 FROM access_settings WHERE key='accidental-read-write'").fetchone())

    def test_two_wallet_generations_can_overlap_without_writer_lock(self):
        self.login(self.user);f.qr_key()
        barrier=threading.Barrier(2)
        def wallet(badge):barrier.wait(timeout=4);return b'fictitious image bytes'
        def request(user):return f.dispatch(self.admin,'GET','/api/users/qr-badge.png',{'matricula':user['username']},{})
        with patch.object(f,'build_wallet_png',side_effect=wallet):
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
                responses=list(pool.map(request,[self.dpo,self.user]))
        self.assertTrue(all(response['png_base64'] for response in responses))

    def test_read_method_cannot_enter_a_mutation_or_camera_probe(self):
        for path in ('/api/cctv/test','/api/visitors/create','/api/users/assign-license'):
            with self.assertRaises(ValueError):f.dispatch(self.admin,'GET',path,{}, {})

    def test_read_only_connection_does_not_create_a_missing_database(self):
        missing=Path(base.TEMP.name)/'must-not-be-created.sqlite'
        with patch.object(base.db,'DB_PATH',str(missing)),self.assertRaises(sqlite3.OperationalError):
            with base.secure.read_transaction():pass
        self.assertFalse(missing.exists())


if __name__=='__main__':unittest.main()
