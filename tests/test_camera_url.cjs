const assert=require('node:assert/strict');
(async()=>{
 const {cameraAddressPaste,normalizeCameraAddress}=await import('../frontend/camera-url.js');
 const address='http://172.16.15.36:8081/video';
 assert.equal(cameraAddressPaste(address),address);
 assert.equal(cameraAddressPaste('/'+address),address);
 assert.equal(normalizeCameraAddress('http://172.16.15.36:8081/'+address),address);
 assert.equal(normalizeCameraAddress('  '+address+'  '),address);
 assert.equal(cameraAddressPaste('/video'),null);
 assert.equal(cameraAddressPaste('rtsp://172.16.15.36/video'),null);
 assert.equal(normalizeCameraAddress('http://172.16.15.36:8081/http://192.168.1.9/video'),'http://172.16.15.36:8081/http://192.168.1.9/video');
 assert.equal(cameraAddressPaste('http://user:password@127.0.0.1:8081/video'),'http://user:password@127.0.0.1:8081/video'); // Conserva datos que debe rechazar la API; no omite su validación.
 console.log('8 comprobaciones correctas: pegado de URL, reparación de ruta y conservación de límites del servidor.');
})().catch(e=>{console.error(e);process.exitCode=1});
