"""Cámara HTTP simulada: límites, cuadros recientes y una captura compartida."""
import io
import sys
import threading
import time
import unittest
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import camera_hub as hub
from PIL import Image

def jpeg(size=(1920,1080)):
    buffer=io.BytesIO();Image.new('RGB',size,(30,90,60)).save(buffer,'JPEG');return buffer.getvalue()

class Camera(unittest.TestCase):
    def tearDown(self):hub.stop_all()
    def test_profiles_resize_no_upscale(self):
        for name,profile in hub.PROFILES.items():
            data,dimensions=hub.optimize(jpeg(),profile)
            self.assertEqual(dimensions[0],profile['width']);self.assertLess(len(data),len(jpeg()))
            self.assertEqual(Image.open(io.BytesIO(data)).format,'JPEG')
        self.assertEqual(hub.optimize(jpeg((100,80)),hub.PROFILES['smooth'])[1],(100,80))
    def test_limits_and_corrupt_image(self):
        for data in (b'',b'x'*(hub.MAX_FRAME+1),b'not an image'):
            with self.assertRaises((ValueError,OSError)):hub.optimize(data,hub.PROFILES['smooth'])
        with self.assertRaises(ValueError):hub.optimize(jpeg((4097,10)),hub.PROFILES['smooth'])
    def serve(self,mode):
        data=jpeg((800,600));calls=[]
        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                calls.append(self.path)
                if self.path=='/redirect':self.send_response(302);self.send_header('Location','/snapshot');self.end_headers();return
                self.send_response(200);self.send_header('Content-Type','image/jpeg' if mode=='snapshot' else 'multipart/x-mixed-replace; boundary=cam');self.end_headers()
                if mode=='snapshot':self.wfile.write(data);return
                try:
                    for _ in range(40):
                        self.wfile.write(b'--cam\r\nContent-Type: image/jpeg\r\n\r\n'+data+b'\r\n');self.wfile.flush();time.sleep(.035)
                except OSError:pass
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
        self.addCleanup(server.server_close);self.addCleanup(server.shutdown)
        return 'http://127.0.0.1:'+str(server.server_port),calls
    def test_snapshot_probe_and_redirect_rejected(self):
        url,calls=self.serve('snapshot');self.assertTrue(hub.probe(url+'/snapshot')['ok'])
        with self.assertRaises(ValueError):hub.probe(url+'/redirect')
        self.assertEqual(calls,['/snapshot','/redirect'])
    def test_mjpeg_shared_capture_latest_only(self):
        url,calls=self.serve('mjpeg');channel={'id':7,'url':url+'/video','profile':'smooth'}
        first=hub.get_feed(channel);first.clients=2
        self.assertIs(first,hub.get_feed(channel))
        seq,frame,_=first.latest(0,3);self.assertGreater(seq,0);self.assertTrue(frame.startswith(b'\xff\xd8'))
        time.sleep(.5);new_seq,new_frame,_=first.latest(seq,.5)
        self.assertGreater(new_seq,seq);self.assertTrue(new_frame);self.assertEqual(len(calls),1)
        status=first.status();self.assertEqual(status['queue_size'],1);self.assertEqual(status['viewers'],2);self.assertEqual(status['width'],640)
    def test_channel_change_replaces_worker(self):
        url,_=self.serve('snapshot');first=hub.get_feed({'id':1,'url':url,'profile':'smooth'})
        second=hub.get_feed({'id':1,'url':url,'profile':'balanced'})
        self.assertIsNot(first,second);self.assertTrue(first.stop.is_set())
        hub.reconcile([]);self.assertTrue(second.stop.is_set());self.assertEqual(hub.existing_status(),{})
    def test_smooth_profile_can_follow_a_fluid_source_without_duplicate_capture(self):
        url,calls=self.serve('mjpeg');channel={'id':18,'url':url+'/video','profile':'smooth'}
        feed=hub.get_feed(channel);feed.clients=2;feed.latest(0,3)
        self.assertIs(feed,hub.get_feed(channel));time.sleep(.9)
        status=feed.status()
        self.assertGreater(status['actual_fps'],16)
        self.assertEqual(status['queue_size'],1);self.assertEqual(len(calls),1)

if __name__=='__main__':unittest.main()
