"""Una captura por canal, cuadro más reciente y fan-out MJPEG acotado."""
import io
import threading
import time
import urllib.request
from collections import deque
from PIL import Image, ImageOps, UnidentifiedImageError

MAX_CHANNELS=8
PROFILES={'smooth':{'width':640,'fps':24,'quality':52},'balanced':{'width':960,'fps':24,'quality':63},'detail':{'width':1280,'fps':25,'quality':72}}
_encode_slots=threading.BoundedSemaphore(2)
MAX_FRAME=4*1024*1024
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kw):return None

def optimize(jpeg,profile):
    if not 0<len(jpeg)<=MAX_FRAME:raise ValueError('Cuadro fuera de límites.')
    with Image.open(io.BytesIO(jpeg)) as image:
        if image.width>4096 or image.height>4096:raise ValueError('Resolución de origen excesiva; usa hasta 1080p en el teléfono.')
        if image.format=='JPEG' and max(image.size)<=profile['width'] and len(jpeg)<=image.width*image.height*.16 and not image.info.get('exif'):
            return jpeg,image.size  # Evita volver a comprimir cuadros pequeños ya adecuados.
        image=ImageOps.exif_transpose(image).convert('RGB')
        image.thumbnail((profile['width'],profile['width']),Image.Resampling.BILINEAR)
        out=io.BytesIO();image.save(out,format='JPEG',quality=profile['quality'],optimize=False)
        return out.getvalue(),image.size

class Feed:
    def __init__(self,url,profile):
        self.url=url;self.profile=PROFILES[profile];self.condition=threading.Condition();self.stop=threading.Event()
        self.frame=None;self.sequence=0;self.captured=0;self.clients=0;self.created=time.monotonic();self.error='Conectando a la cámara…';self.dimensions=(0,0);self.started=time.monotonic();self.next_frame=0;self.timestamps=deque(maxlen=40)
        self.thread=threading.Thread(target=self.run,daemon=True,name='camera-capture');self.thread.start()
    def publish(self,data):
        started=time.monotonic()
        if started+.002<self.next_frame or not _encode_slots.acquire(blocking=False):return
        try:frame,dimensions=optimize(data,self.profile)
        finally:_encode_slots.release()
        with self.condition:
            self.frame=frame;self.dimensions=dimensions;self.sequence+=1;self.captured=time.time();self.timestamps.append(self.captured);self.error='';self.condition.notify_all()
        interval=1/self.profile['fps']
        self.next_frame=self.next_frame+interval if self.next_frame and started-self.next_frame<interval else started+interval
    def run(self):
        opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
        while not self.stop.is_set():
            if self.clients==0 and time.monotonic()-self.created>20:break
            try:
                request=urllib.request.Request(self.url,headers={'Accept':'multipart/x-mixed-replace,image/jpeg','Connection':'close'})
                with opener.open(request,timeout=5) as response:
                    mime=response.headers.get('Content-Type','').lower()
                    if mime.startswith('image/'):
                        self.publish(response.read(MAX_FRAME+1));self.stop.wait(1/self.profile['fps']);continue
                    if not mime.startswith('multipart/x-mixed-replace'):raise ValueError('La ruta devuelve una página, no MJPEG/JPEG. Prueba /video o la ruta indicada por la app.')
                    buffer=b''
                    while not self.stop.is_set():
                        if self.clients==0 and time.monotonic()-self.created>20:break
                        chunk=response.read1(16384)
                        if not chunk:break
                        buffer+=chunk
                        newest=None
                        while True:
                            start=buffer.find(b'\xff\xd8');end=buffer.find(b'\xff\xd9',max(0,start))
                            if start<0:buffer=buffer[-2:];break
                            if end<0:
                                buffer=buffer[start:]
                                if len(buffer)>MAX_FRAME:raise ValueError('El cuadro excede 4 MB; reduce resolución en el teléfono.')
                                break
                            newest=buffer[start:end+2];buffer=buffer[end+2:]
                        if newest:self.publish(newest)
            except (OSError,ValueError,UnidentifiedImageError,Image.DecompressionBombError) as error:
                with self.condition:
                    self.error=str(error)[:180] if isinstance(error,ValueError) else 'Sin conexión. Revisa la IP del teléfono, el puerto y el permiso de red local.'
                    self.condition.notify_all()
                self.stop.wait(1.5)
        self.stop.set()
    def latest(self,sequence,timeout=2):
        with self.condition:
            self.condition.wait_for(lambda:self.sequence!=sequence or self.stop.is_set(),timeout)
            return self.sequence,self.frame,self.captured
    def status(self):
        with self.condition:return {'connected':bool(self.frame and time.time()-self.captured<8),'error':self.error,'frames':self.sequence,'width':self.dimensions[0],'height':self.dimensions[1],
            'frame_age_ms':round((time.time()-self.captured)*1000) if self.frame else None,'target_fps':self.profile['fps'],'actual_fps':round((len(self.timestamps)-1)/(self.timestamps[-1]-self.timestamps[0]),1) if len(self.timestamps)>1 and self.timestamps[-1]>self.timestamps[0] and time.time()-self.captured<2 else 0,'frame_bytes':len(self.frame) if self.frame else 0,'viewers':self.clients,'queue_size':1}

_lock=threading.Lock();_feeds={}
def get_feed(channel):
    key=(channel['url'],channel['profile'])
    with _lock:
        old=_feeds.get(channel['id'])
        if old and old[0]==key and not old[1].stop.is_set():return old[1]
        if old:old[1].stop.set()
        feed=Feed(*key);_feeds[channel['id']]=(key,feed);return feed
def existing_status():
    with _lock:return {str(key):feed.status() for key,(_,feed) in _feeds.items() if not feed.stop.is_set()}

def reconcile(channels):
    """Cierra capturas retiradas o cuyo origen cambió al guardar la configuración."""
    desired={c['id']:(c['url'],c['profile']) for c in channels}
    with _lock:
        for channel_id,(key,feed) in list(_feeds.items()):
            if desired.get(channel_id)!=key:
                feed.stop.set()
                with feed.condition:feed.condition.notify_all()
                del _feeds[channel_id]
def stop_all():
    with _lock:
        for _,feed in _feeds.values():feed.stop.set()
        _feeds.clear()

def probe(url):
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
    try:
        start=time.monotonic()
        with opener.open(urllib.request.Request(url,headers={'Accept':'multipart/x-mixed-replace,image/jpeg'}),timeout=4) as r:
            mime=r.headers.get('Content-Type','').lower()
            if not (mime.startswith('multipart/x-mixed-replace') or mime.startswith('image/')):raise ValueError('La dirección abre una página de control. Indica la ruta MJPEG/JPEG de la cámara.')
            return {'ok':True,'content_type':mime,'connect_ms':round((time.monotonic()-start)*1000),'message':'Cámara encontrada. Guarda el canal para comenzar.'}
    except ValueError:raise
    except OSError:raise ValueError('No se pudo conectar. Enciende el servidor HTTP en IP Camera Lite, revisa la IP y conecta teléfono y laptop a una red que permita comunicación entre ellos.') from None
