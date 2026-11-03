const assert=require('node:assert/strict'),path=require('node:path'),{execFileSync}=require('node:child_process');
module.exports=async({context,base,browser})=>{
 const data=await(await context.request.get(base+'api/data')).json();
 const target=data.users.find(u=>u.role==='user'&&u.area==='Monitoring'&&!u.is_guard&&!u.mfa_configured&&!u.is_locked);
 assert(target);const owner=await(await context.request.get(base+'api/session')).json(),origin=new URL(base).origin;
 const granted=await context.request.post(base+'api/users/assign-license',{headers:{Origin:origin,'X-CSRF-Token':owner.csrf},data:{matricula:target.username,license_id:'LIC-CCTV-ADMIN'}});assert.equal(granted.status(),200);
 const cameraContext=await browser.newContext({viewport:{width:1440,height:1000}});
 try{
  let state=await(await cameraContext.request.get(base+'api/session')).json();
  async function post(p,b){const r=await cameraContext.request.post(base+'api/'+p,{headers:{Origin:origin,'X-CSRF-Token':state.csrf},data:b});assert.equal(r.status(),200,p);const result=await r.json();if(result.csrf)state=result;return result}
  const activationResponse=await context.request.post(base+'api/users/activation',{headers:{Origin:origin,'X-CSRF-Token':owner.csrf},data:{matricula:target.username}});assert.equal(activationResponse.status(),200);
  const activation=await activationResponse.json();const activationPage=await cameraContext.newPage();await activationPage.goto(activation.activation_url);await activationPage.getByRole('link',{name:'Continuar al inicio de sesión',exact:true}).waitFor();await activationPage.close();state=await(await cameraContext.request.get(base+'api/session')).json();
  await post('auth/login',{username:target.username,password:'SoloPruebasLocal2026!'});
  await post('auth/password',{password:'PrivadaCamaraDePrueba123!'});
  const code=execFileSync(process.env.ST_TEST_PYTHON,['-c','import sys,pyotp;print(pyotp.TOTP(sys.stdin.read()).now())'],{input:state.enrollment_key,encoding:'utf8'}).trim();
  await post('auth/mfa',{code});await post('auth/backup-saved',{});await post('auth/accept-terms',{accepted:true,version:state.terms.version});
  assert.equal(state.user.role,'user');assert.equal(state.permissions.cctv_admin,true);assert.equal(state.permissions.terminal,false);
  const page=await cameraContext.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));await page.goto(base);
  await page.getByRole('heading',{name:'Mi QR de acceso',exact:true}).waitFor();
  assert.equal(await page.locator('.role-chip').innerText(),'Admin de cámaras');
  assert.equal(await page.getByRole('button',{name:'Personas y permisos',exact:true}).count(),0);
  await page.getByRole('button',{name:'Monitoreo CCTV',exact:true}).click();
  await page.getByRole('tab',{name:'Configurar cámaras',exact:true}).click();
  await page.getByText('Vincular una cámara nueva',{exact:true}).click();await page.getByRole('button',{name:'Generar QR de cámara',exact:true}).click();
  await page.getByAltText('QR para vincular cámara CCTV', {exact:true}).waitFor();
  await page.getByText('Cámaras con IP Camera Lite / dirección local',{exact:true}).click();
  await page.getByRole('button',{name:'Agregar canal',exact:true}).waitFor();
  await page.screenshot({path:path.join(__dirname,'../design/26-administrador-camaras.png'),fullPage:true});
  const denied=await cameraContext.request.post(base+'api/users/update',{headers:{Origin:origin,'X-CSRF-Token':state.csrf},data:{id:data.users.find(u=>u.id!==target.id).id,changes:{role:'system_admin'}}});assert.equal(denied.status(),403);
  const revoked=await context.request.post(base+'api/users/revoke-license',{headers:{Origin:origin,'X-CSRF-Token':owner.csrf},data:{matricula:target.username,license_id:'LIC-CCTV-ADMIN'}});assert.equal(revoked.status(),200);
  await page.reload();await page.getByRole('button',{name:'Monitoreo CCTV',exact:true}).click();await page.getByRole('heading',{name:'Centro de vigilancia',exact:true}).waitFor();await page.getByText('Consulta autorizada',{exact:true}).waitFor();assert.equal(await page.getByRole('tab',{name:'Configurar cámaras',exact:true}).count(),0);
  const readonly=await cameraContext.request.post(base+'api/cctv/channels',{headers:{Origin:origin,'X-CSRF-Token':state.csrf},data:{channels:[]}});assert.equal(readonly.status(),403);
  assert.deepEqual(errors,[]);
 }finally{await cameraContext.close()}
 return ['Permiso de cámaras conserva rol Usuario y no habilita directorio ni terminal','Administrador de cámaras visible en React, configura cámaras IP y vincula un navegador','API rechaza administración de usuarios desde una cuenta con permiso de cámaras','Revocar administración deja Monitoring con vigilancia de consulta y sin configuración'];
};
