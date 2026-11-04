"""Hot camera RPCs keep authorization but cannot reserve SQLite's writer."""
import io,sqlite3,unittest
from unittest.mock import patch
from PIL import Image
import test_backend as base
import test_browser_cameras as cameras
import browser_cameras as bc


class CameraReadTransactions(unittest.TestCase):
    setUpClass=classmethod(base.Backend.setUpClass.__func__)
    login=base.Backend.login
    setUp=cameras.BrowserCameras.setUp
    alive=cameras.BrowserCameras.alive
    req=cameras.BrowserCameras.req
    pair=cameras.BrowserCameras.pair

    def test_frames_and_signals_do_not_reserve_the_database_writer(self):
        ch,phone=self.pair()
        image=io.BytesIO();Image.new('RGB',(64,48),'green').save(image,'JPEG')
        with patch.object(base.secure,'write_transaction',side_effect=AssertionError('Video reserved SQLite writer')):
            self.req('list');self.req('status',{'id':ch['id']})
            view=self.req('view',{'id':ch['id']},sid='viewer')
            key={'id':ch['id'],'peer':view['peer']}
            self.req('viewer-signal',{**key,'message':{'type':'offer','sdp':'v=0'}},sid='viewer')
            self.assertEqual(self.req('poll',{'phone_token':phone['phone_token']},state={})['messages'][0]['type'],'offer')
            self.req('signal',{'phone_token':phone['phone_token'],'peer':view['peer'],'message':{'type':'answer','sdp':'v=0'}},state={})
            self.assertEqual(self.req('viewer-poll',key,sid='viewer')['messages'][0]['type'],'answer')
            self.assertTrue(self.req('upload-frame',{'phone_token':phone['phone_token'],'source_seq':1,'_raw_jpeg':image.getvalue()},state={})['accepted'])
            self.assertEqual(self.req('frame',key,sid='viewer')['seq'],1)
            self.req('leave',key,sid='viewer')

    def test_authorization_inside_camera_read_rpc_is_query_only(self):
        def accidental_write(c,u):
            c.execute("INSERT INTO access_settings VALUES('accidental-camera-write','1')")
        with patch.object(bc.f,'camera_admin',side_effect=accidental_write),self.assertRaises(sqlite3.OperationalError):
            self.req('list')
        with base.db.get_connection() as c:
            self.assertIsNone(c.execute("SELECT 1 FROM access_settings WHERE key='accidental-camera-write'").fetchone())

    def test_lifecycle_operations_still_persist_audit_events(self):
        first,phone=self.pair();self.req('revoke',{'id':first['id']})
        second,phone=self.pair();self.req('disconnect',{'phone_token':phone['phone_token']},state={})
        with base.db.get_connection() as c:
            result={r[0]:r[1] for r in c.execute("SELECT action,COUNT(*) FROM audit_log WHERE action LIKE 'CCTV_BROWSER_%' GROUP BY action")}
        self.assertEqual(result,{'CCTV_BROWSER_CREATED':2,'CCTV_BROWSER_APPROVED':2,'CCTV_BROWSER_REVOKED':2})

    def test_invalid_path_is_rejected_before_opening_a_transaction(self):
        with patch.object(base.secure,'read_transaction',side_effect=AssertionError('Unknown route opened DB')):
            with self.assertRaises(ValueError):bc.dispatch('/api/browser-camera/not-a-route',{},'owner',self.state,self.alive)


if __name__=='__main__':unittest.main()
