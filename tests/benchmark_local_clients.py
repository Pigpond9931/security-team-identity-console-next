"""Bounded localhost HTTP probe. Creates its own server and fictitious sessions."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import argparse,http.client,io,json,math,os,secrets,sys,tempfile,threading,time

parser=argparse.ArgumentParser()
parser.add_argument('--queue',type=int,choices=(5,64),help='Override experimental de la cola; no acepta un destino externo.')
args=parser.parse_args()
ROOT=Path(__file__).resolve().parents[1]
OUTPUT=Path(os.environ.get('ST_QA_OUTPUT',str(ROOT.parent/'qa-load')))
OUTPUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT))
with tempfile.TemporaryDirectory(prefix='NextClients35-') as directory:
    os.environ['ST_DATA_DIR']=directory;os.environ['ST_TEST_MODE']='1'
    import server,browser_cameras as bc
    from PIL import Image
    queue_size=args.queue or server.ThreadingHTTPServer.request_queue_size
    OUT=OUTPUT/f'clients-35-queue-{queue_size}.json'
    server.initialize()
    hashed=server.secure.hash_password(secrets.token_urlsafe(24))
    encrypted=server.secure.encrypt_secret(server.db.generate_mfa_secret())
    with server.secure.write_transaction() as c:
        for number in (34,35):
            c.execute('INSERT INTO users(username,full_name,role,area,is_guard,password_hash,created_at) VALUES(?,?,?,?,?,?,?)',
                (str(9900000+number),'Persona ficticia '+str(number),'user','Access Control',0,hashed,server.db._now()))
        c.execute("UPDATE users SET role='user',area='Access Control',is_guard=0,password_hash=?,mfa_secret=?,mfa_configured=1,must_change_password=0,ever_enrolled=1,terms_accepted=1,terms_version=?,terms_accepted_at=?,allowed_zones='[\"GENERAL_ACCESS\"]'",
            (hashed,encrypted,server.db.TERMS_VERSION,server.db._now()))
        c.execute("UPDATE users SET role='dpo',area=NULL WHERE id=1")
        users=[dict(r) for r in c.execute('SELECT * FROM users ORDER BY id')]
    accounts=[]
    for user in users:
        sid,state=server.make_session()
        auth={'user_id':user['id'],'security_version':user['security_version'],'issued_at':time.time()}
        if user['id']==1:auth['cctv_session']=True
        state.update(stage='dashboard',auth=auth)
        accounts.append({'sid':sid,'csrf':state['csrf'],'username':user['username']})
    assert len(accounts)==35
    assert Path(server.db.DB_PATH).resolve().is_relative_to(Path(directory).resolve())
    owner=accounts[0];owner_state=server.SESSIONS[owner['sid']]
    alive=lambda sid,auth:sid in server.SESSIONS and server.SESSIONS[sid].get('auth')==auth
    ch=bc.dispatch('/api/browser-camera/create',{'name':'Cámara sintética de carga','zone':'GENERAL_ACCESS'},owner['sid'],owner_state,alive)
    phone=bc.dispatch('/api/browser-camera/claim',{'ticket':ch['ticket']},'fixture-phone',{},alive)
    bc.dispatch('/api/browser-camera/approve',{'id':ch['id'],'confirmation':phone['confirmation']},owner['sid'],owner_state,alive)
    phone_sid,phone_state=server.make_session()
    class Quiet(server.Handler):
        def log_message(self,*args):pass
    class Http(server.ThreadingHTTPServer):request_queue_size=queue_size
    httpd=Http(('127.0.0.1',0),Quiet)
    thread=threading.Thread(target=httpd.serve_forever,daemon=True);thread.start()
    origin='http://127.0.0.1:'+str(httpd.server_port)
    samples=[];sample_lock=threading.Lock()
    def request(account,path,body=None,extra=None):
        headers={'Cookie':'st_session='+account['sid']}
        method='GET' if body is None else 'POST'
        if body is not None:
            headers.update(Origin=origin,**{'X-CSRF-Token':account['csrf'],'Content-Type':'application/json'})
            if not isinstance(body,bytes):body=json.dumps(body).encode()
        if extra:headers.update(extra)
        started=time.monotonic();status=0;result={}
        connection=http.client.HTTPConnection('127.0.0.1',httpd.server_port,timeout=12)
        try:
            connection.request(method,path,body,headers)
            response=connection.getresponse();status=response.status;result=json.loads(response.read())
        except (OSError,ValueError,http.client.HTTPException):status=0
        finally:
            connection.close()
            with sample_lock:samples.append({'path':path,'status':status,'ms':(time.monotonic()-started)*1000})
        return status,result
    def stats(rows):
        values=sorted(r['ms'] for r in rows)
        p=lambda fraction:round(values[min(len(values)-1,math.ceil(fraction*len(values))-1)],1) if values else None
        return {'requests':len(rows),'status_counts':{str(s):sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})},
            'latency_ms':{'p50':p(.5),'p95':p(.95),'max':round(max(values),1) if values else None}}
    results={}
    try:
        barrier=threading.Barrier(35)
        def reader(account):
            barrier.wait(timeout=10)
            for path in ('/api/session','/api/data','/api/users/qr-badge'):
                status,result=request(account,path)
                if status==200 and path.endswith('qr-badge'):assert result['badge']['matricula']==account['username']
        started=time.monotonic()
        with ThreadPoolExecutor(max_workers=35) as pool:list(pool.map(reader,accounts))
        results['35_clients_read_burst']={**stats(samples),'seconds':round(time.monotonic()-started,2)}
        samples.clear();barrier=threading.Barrier(37)
        buffer=io.BytesIO();Image.new('RGB',(640,360),(40,70,90)).save(buffer,'JPEG');jpeg=buffer.getvalue()
        counts={'camera_accepted':0,'access_verified':0}
        def mixed_reader(account):
            barrier.wait(timeout=10)
            for _ in range(8):request(account,'/api/data')
        def writer():
            barrier.wait(timeout=10)
            for account in accounts[:20]:
                status,result=request(owner,'/api/access/verify',{'zone':'GENERAL_ACCESS','method':'QR_BADGE','direction':'AUTO',
                    'ref':server.features.sign({'purpose':'BADGE','tipo':'USER','ref':account['username'],'sv':0,'exp':int(time.time()+60)})})
                if status==200 and result['result']['verdict']=='VERIFIED':counts['access_verified']+=1
                time.sleep(.05)
        def producer():
            barrier.wait(timeout=10);deadline=time.monotonic()+5;sequence=0
            account={'sid':phone_sid,'csrf':phone_state['csrf']}
            while time.monotonic()<deadline:
                sequence+=1
                status,result=request(account,'/api/browser-camera/upload-frame',jpeg,{'Cookie':'st_session='+phone_sid+'; st_camera='+phone['phone_token'],
                    'Content-Type':'image/jpeg','X-Frame-Sequence':str(sequence)})
                if status==200 and result.get('accepted'):counts['camera_accepted']+=1
                time.sleep(1/30)
        started=time.monotonic()
        with ThreadPoolExecutor(max_workers=37) as pool:
            futures=[pool.submit(mixed_reader,a) for a in accounts]+[pool.submit(writer),pool.submit(producer)]
            for future in futures:future.result(timeout=60)
        results['35_readers_with_terminal_and_one_camera']={**stats(samples),'seconds':round(time.monotonic()-started,2),**counts,
            'per_route':{p:stats([r for r in samples if r['path']==p]) for p in sorted({r['path'] for r in samples})}}
        report={'ok':all(set(scenario['status_counts'])=={'200'} for scenario in results.values()) and counts['access_verified']==20 and counts['camera_accepted']>0,
            'queue':queue_size,'clients':35,'preauthenticated_fixture_sessions':True,'authentication_load_measured':False,
            'transport':'localhost HTTP; Python clients; synthetic JPEG','production_data_used':False,
            'real_wifi_phone_or_cloudflare_test':False,'results':results}
        OUT.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8');print(json.dumps(report))
    finally:
        httpd.shutdown();httpd.server_close();thread.join();bc.CHANNELS.clear()
