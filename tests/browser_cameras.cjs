const assert=require('node:assert/strict'),path=require('node:path');
module.exports=async({page,context,base,browser})=>{
 const badgeReply=page.waitForResponse(r=>new URL(r.url()).pathname==='/api/users/qr-badge'&&r.status()===200);
 await page.getByRole('button',{name:'Mi QR',exact:true}).click();
 await page.getByRole('heading',{name:'Mi QR de acceso',exact:true}).waitFor();
 await page.getByAltText('Gafete QR de acceso',{exact:true}).waitFor();
 const own=await(await badgeReply).json();assert.equal(own.badge.matricula,(await(await context.request.get(base+'api/session')).json()).user.username);assert.equal(await page.getByAltText('Gafete QR de acceso',{exact:true}).getAttribute('src'),'data:image/png;base64,'+own.qr_png_base64);
 await page.screenshot({path:path.join(process.env.ST_QA_OUTPUT||path.resolve(__dirname,'../../qa-browser'),'20-mi-qr.png'),fullPage:true});
 await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await page.screenshot({path:path.join(process.env.ST_QA_OUTPUT||path.resolve(__dirname,'../../qa-browser'),'23-mi-qr-movil.png'),fullPage:true,animations:'disabled'});await page.setViewportSize({width:1440,height:1000});
 await page.getByRole('button',{name:'Monitoreo CCTV',exact:true}).click();
 await page.getByRole('tab',{name:'Configurar cámaras',exact:true}).click();
 await page.getByText('Vincular una cámara nueva',{exact:true}).click();
 await page.getByLabel('Nombre de cámara',{exact:true}).fill('Puerta de laboratorio');
 await page.getByRole('button',{name:'Generar QR de cámara',exact:true}).click();
 const href=await page.getByRole('link',{name:'Abrir cámara en otro dispositivo',exact:true}).getAttribute('href');
 const mobile=await browser.newContext({viewport:{width:390,height:844},permissions:['camera']});const phone=await mobile.newPage();const errors=[];phone.on('pageerror',e=>errors.push(e.message));
 try{
  await phone.goto(href);await phone.getByRole('heading',{name:'Confirma el código en CCTV',exact:true}).waitFor();
  await page.getByRole('button',{name:'Confirmar cámara CCTV',exact:true}).waitFor();
  const cameraCookie=(await mobile.cookies()).find(c=>c.name==='st_camera');assert(cameraCookie?.httpOnly);assert(!await phone.evaluate(()=>document.cookie.includes('st_camera=')));assert.equal(await phone.evaluate(()=>sessionStorage.length),0);
  assert.equal(await phone.locator('.phone-confirm-code').innerText(),await page.locator('.phone-confirm-code').innerText());
  await page.getByRole('button',{name:'Confirmar cámara CCTV',exact:true}).click();
  await phone.getByRole('button',{name:'Transmitir cámara',exact:true}).click();
  await phone.waitForFunction(()=>document.querySelector('video')?.videoWidth>0);
  await page.getByRole('tab',{name:'Vigilancia',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.browser-camera-card video')?.videoWidth>0,{},{timeout:25000});
  await page.locator('.browser-camera-card .camera-signal').filter({hasText:'En vivo'}).waitFor();
  assert(await page.locator('.browser-camera-card').innerText().then(t=>t.includes('Directo WebRTC')));
  await page.locator('.surveillance-count').filter({hasText:'1 con señal'}).waitFor();
  const decodedBefore=await page.locator('.browser-camera-card video').evaluate(video=>video.getVideoPlaybackQuality().totalVideoFrames);
  await page.waitForTimeout(2500);
  const decodedAfter=await page.locator('.browser-camera-card video').evaluate(video=>video.getVideoPlaybackQuality().totalVideoFrames);
  require('node:fs').writeFileSync(path.join(process.env.ST_QA_OUTPUT||path.resolve(__dirname,'../../qa-browser'),'webrtc-decoder.json'),JSON.stringify({decodedBefore,decodedAfter},null,2));
  assert(decodedAfter-decodedBefore>=10,'WebRTC debe decodificar cuadros nuevos, no solo mostrar una imagen');
  const rtcFrames=decodedAfter-decodedBefore;
  await page.screenshot({path:path.join(process.env.ST_QA_OUTPUT||path.resolve(__dirname,'../../qa-browser'),'21-cctv-navegador.png'),fullPage:true});
  await require('./browser_surveillance.cjs')({page,context,base,browser});
  await phone.screenshot({path:path.join(process.env.ST_QA_OUTPUT||path.resolve(__dirname,'../../qa-browser'),'22-camara-telefono.png'),fullPage:true});
  assert(await phone.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.equal((await mobile.request.get(base+'api/data')).status(),401);
  await phone.getByRole('button',{name:'Detener transmisión',exact:true}).click();await page.locator('.browser-camera-card .camera-signal').filter({hasText:'Sin señal'}).waitFor();await phone.getByRole('button',{name:'Transmitir cámara',exact:true}).click();await page.locator('.browser-camera-card .camera-signal').filter({hasText:'En vivo'}).waitFor();
  // Fuerza que el espectador carezca de WebRTC: debe recibir cuadros HTTPS.
  await page.addInitScript(()=>{window.RTCPeerConnection=undefined});await page.reload();await page.getByRole('button',{name:'Monitoreo CCTV',exact:true}).click();
  await page.locator('.browser-camera-card .camera-signal').filter({hasText:'En vivo'}).waitFor({timeout:20000});
  assert(await page.locator('.browser-camera-card').innerText().then(t=>t.includes('Compatible HTTPS')));
  assert((await page.locator('.browser-camera-card img').getAttribute('src')).startsWith('/api/browser-camera/stream?'));
  await page.waitForFunction(()=>document.querySelector('.browser-camera-card img')?.naturalWidth>0);
  const streamUrl=new URL(await page.locator('.browser-camera-card img').getAttribute('src'),base),session=await(await context.request.get(base+'api/session')).json();
  async function sequence(){const r=await context.request.post(base+'api/browser-camera/frame',{headers:{Origin:new URL(base).origin,'X-CSRF-Token':session.csrf},data:{id:streamUrl.searchParams.get('id'),peer:streamUrl.searchParams.get('peer'),seq:-1}});assert.equal(r.status(),200);return(await r.json()).seq}
  const sequenceBefore=await sequence(),started=performance.now();await phone.waitForTimeout(2500);const uploaded=(await sequence())-sequenceBefore,seconds=(performance.now()-started)/1000;assert(uploaded>=20,'HTTPS continuo debe aceptar al menos 20 cuadros durante la muestra local: '+uploaded);
  require('node:fs').writeFileSync(path.join(process.env.ST_QA_OUTPUT||path.resolve(__dirname,'../../qa-browser'),'resultado-cctv-fluidez.json'),JSON.stringify({ok:true,transport:'WebRTC y MJPEG continuo; cámara sintética en Chrome local',sampleSeconds:seconds,acceptedJpegFrames:uploaded,acceptedJpegFps:uploaded/seconds,webRtcDecodedFrames:rtcFrames,webRtcSampleSeconds:2.5,webRtcDecodedFps:rtcFrames/2.5,realPhoneOrInternetBenchmark:false},null,2));
  await phone.getByRole('button',{name:'Desvincular este dispositivo',exact:true}).click();
  await phone.getByRole('alert').filter({hasText:'Cámara desvinculada'}).waitFor();
  await page.locator('.browser-camera-card').waitFor({state:'detached'});assert.deepEqual(errors,[]);
 }finally{await mobile.close()}
 return ['Mi QR abre directamente el gafete del titular autenticado','CCTV WebRTC entre dos navegadores con cámara simulada y hora CDMX','Alternativa HTTPS con cuadros JPEG recientes y sin grabación','Teléfono sin acceso administrativo y revocación efectiva','Centro de vigilancia individual, mosaico, cambio de cámara y liberación de vistas','Ronda automática de 15 s, pantalla completa y diseño móvil'];
};
