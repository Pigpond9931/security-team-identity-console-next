import concurrent.futures,http.client,sqlite3,threading,unittest,json,secrets
from pathlib import Path
from urllib.parse import quote
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

    def test_public_pass_get_preview_never_reserves_the_writer(self):
        user,_=self.login(self.user)
        issued=f.dispatch(user,'POST','/api/users/mobile-pass',{}, {})
        token=issued['pass_token']
        httpd=base.server.ThreadingHTTPServer(('127.0.0.1',0),base.server.Handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        host='127.0.0.1:'+str(httpd.server_port)
        try:
            with patch.object(base.secure,'write_transaction',side_effect=AssertionError('GET reservó el escritor')):
                connection=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=8)
                connection.request('GET','/api/public-pass?token='+quote(token),headers={'Host':host})
                response=connection.getresponse();payload=json.loads(response.read());connection.close()
            self.assertEqual(response.status,200)
            self.assertTrue(payload['requires_claim']);self.assertTrue(payload['requires_login'])
        finally:httpd.shutdown();httpd.server_close();base.server.SESSIONS.clear()

    def test_public_pass_receipt_and_download_never_reserve_the_writer(self):
        import pass_exchange
        user,_=self.login(self.user)
        issued=f.dispatch(user,'POST','/api/users/mobile-pass',{}, {})
        sid=secrets.token_urlsafe(32)
        with base.secure.write_transaction() as c:
            receipt=pass_exchange.claim(c,issued['pass_token'],sid,user)
        base.server.SESSIONS[sid]={'created':base.time.time(),'stage':'dashboard','auth':user,'csrf':'fixture'}
        httpd=base.server.ThreadingHTTPServer(('127.0.0.1',0),base.server.Handler)
        threading.Thread(target=httpd.serve_forever,daemon=True).start()
        try:
            with patch.object(base.secure,'write_transaction',side_effect=AssertionError('GET reserved writer')):
                for suffix in ('','?download=1'):
                    connection=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=8)
                    connection.request('GET','/api/public-pass'+suffix,headers={
                        'Cookie':'st_session='+sid+'; st_pass='+receipt})
                    response=connection.getresponse();payload=json.loads(response.read());connection.close()
                    self.assertEqual(response.status,200,payload)
                    self.assertTrue(payload['badge']['token'])
                    if suffix:self.assertTrue(payload['png_base64'])
        finally:httpd.shutdown();httpd.server_close();base.server.SESSIONS.clear()


if __name__=='__main__':unittest.main()
