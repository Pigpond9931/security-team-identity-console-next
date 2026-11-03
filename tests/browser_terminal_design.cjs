const assert=require('node:assert/strict'),path=require('node:path'),{execFileSync}=require('node:child_process');
module.exports=async({page,context,base,browser})=>{
 const out=path.join(__dirname,'../design');
 await page.getByRole('tab',{name:'Operación',exact:true}).click();await page.getByRole('button',{name:'Tarjeta RFID',exact:true}).click();await page.evaluate(()=>window.scrollTo(0,0));
 assert.equal(await page.getByRole('tab',{name:'Operación',exact:true}).getAttribute('aria-selected'),'true');
 assert(await page.getByRole('textbox',{name:'Lector RFID USB 125 kHz',exact:true}).isVisible());
 await page.screenshot({path:path.join(out,'31-terminal-operacion.png'),fullPage:true,animations:'disabled'});
 await page.getByRole('tab',{name:'Configuración',exact:true}).click();
 assert(await page.getByRole('textbox',{name:'Lector RFID USB 125 kHz',exact:true}).isHidden());
 const before=await page.getByLabel('Zona / Puerta',{exact:true}).inputValue();await page.keyboard.press('F2');assert.equal(await page.getByLabel('Zona / Puerta',{exact:true}).inputValue(),before,'Los atajos de lectura no operan sobre la configuración');
 await page.getByRole('tab',{name:'Configuración',exact:true}).press('Home');
 assert.equal(await page.getByRole('tab',{name:'Operación',exact:true}).getAttribute('aria-selected'),'true');
 assert(await page.getByRole('tab',{name:'Operación',exact:true}).evaluate(el=>el===document.activeElement));
 await page.getByRole('button',{name:'Gafete QR',exact:true}).click();
 await page.getByRole('button',{name:'Encender cámara QR',exact:true}).click();await page.waitForFunction(()=>document.querySelector('.terminal-qr-preview video')?.videoWidth>0);
 await page.getByRole('tab',{name:'Actividad',exact:true}).click();
 assert(await page.evaluate(()=>document.querySelector('.terminal-qr-preview video').srcObject.getTracks().every(t=>t.readyState==='ended')));
 await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(out,'32-terminal-actividad.png'),fullPage:true,animations:'disabled'});
 await page.getByRole('tab',{name:'Operación',exact:true}).click();await page.getByRole('button',{name:'Teléfono',exact:true}).click();await page.getByRole('button',{name:'Vincular teléfono como escáner',exact:true}).click();
 const pairedLink=await page.getByRole('link',{name:'Abrir escáner en el teléfono',exact:true}).getAttribute('href');
 await page.getByRole('tab',{name:'Actividad',exact:true}).click();await page.getByRole('tab',{name:'Operación',exact:true}).click();assert.equal(await page.getByRole('link',{name:'Abrir escáner en el teléfono',exact:true}).getAttribute('href'),pairedLink);await page.getByRole('button',{name:'Desvincular teléfono',exact:true}).click();
 await page.getByRole('button',{name:'Tarjeta RFID',exact:true}).click();await page.getByRole('button',{name:'Pantalla de kiosco',exact:true}).click();assert(await page.getByRole('textbox',{name:'Lector RFID USB 125 kHz',exact:true}).isHidden());assert(await page.getByRole('region',{name:'Última decisión de acceso',exact:true}).isVisible());await page.getByRole('button',{name:'Salir de pantalla de kiosco',exact:true}).click();
 await page.getByRole('tab',{name:'Configuración',exact:true}).click();await page.getByText('Administrar tarjetas y licencias de bóveda',{exact:true}).click();await page.evaluate(()=>window.scrollTo(0,0));await page.screenshot({path:path.join(out,'33-terminal-configuracion.png'),fullPage:true,animations:'disabled'});
 await page.getByRole('tab',{name:'Operación',exact:true}).click();await page.setViewportSize({width:390,height:844});await page.waitForFunction(()=>document.querySelector('.sidebar').getBoundingClientRect().right<=1);await page.evaluate(()=>window.scrollTo(0,0));
 assert(await page.evaluate(()=>[...document.querySelectorAll('.terminal-banner,.terminal-tabs,.terminal-area-grid,.terminal-workspace,.terminal-reader,.terminal-decision')].every(el=>el.getBoundingClientRect().right<=innerWidth+1)));
 await page.screenshot({path:path.join(out,'34-terminal-movil.png'),fullPage:true,animations:'disabled'});await page.setViewportSize({width:1440,height:1000});
 const records=await(await context.request.get(base+'api/data')).json(),target=records.users.find(u=>u.role==='user'&&u.area==='Access Control'&&!u.is_guard&&!u.mfa_configured),owner=await(await context.request.get(base+'api/session')).json(),origin=new URL(base).origin;
 assert(target);const promoted=await context.request.post(base+'api/users/update',{headers:{Origin:origin,'X-CSRF-Token':owner.csrf},data:{id:target.id,changes:{role:'area_admin'}}});assert.equal(promoted.status(),200);const limited=await browser.newContext({viewport:{width:1440,height:1000}});
 try{
  let state=await(await limited.request.get(base+'api/session')).json();
  const a=await context.request.post(base+'api/users/activation',{headers:{Origin:origin,'X-CSRF-Token':owner.csrf},data:{matricula:target.username}});assert.equal(a.status(),200);const link=await a.json();
  const activated=await limited.newPage();await activated.goto(link.activation_url);await activated.getByRole('link',{name:'Continuar al inicio de sesión',exact:true}).waitFor();await activated.close();state=await(await limited.request.get(base+'api/session')).json();
  async function post(p,b){const r=await limited.request.post(base+'api/'+p,{headers:{Origin:origin,'X-CSRF-Token':state.csrf},data:b});assert.equal(r.status(),200,p);const data=await r.json();if(data.csrf)state=data;return data}
  await post('auth/login',{username:target.username,password:'SoloPruebasLocal2026!'});await post('auth/password',{password:'PrivadaTerminalPrueba123!'});
  const code=execFileSync(process.env.ST_TEST_PYTHON,['-c','import sys,pyotp;print(pyotp.TOTP(sys.stdin.read()).now())'],{input:state.enrollment_key,encoding:'utf8'}).trim();await post('auth/mfa',{code});await post('auth/backup-saved',{});await post('auth/accept-terms',{accepted:true,version:state.terms.version});
  const op=await limited.newPage();const errors=[];op.on('pageerror',e=>errors.push(e.message));await op.goto(base);await op.getByRole('button',{name:'Terminal de Acceso',exact:true}).click();await op.getByRole('button',{name:'F4 IAM',exact:true}).waitFor();
  assert.equal(await op.getByRole('tab',{name:'Configuración',exact:true}).count(),0);assert(await op.getByRole('button',{name:'F2 Identity Management',exact:true}).isDisabled());assert(await op.getByRole('button',{name:'F3 Monitoring',exact:true}).isDisabled());
  const denied=await limited.request.post(base+'api/access/terminal-settings',{headers:{Origin:origin,'X-CSRF-Token':state.csrf},data:{occupancy_limit:2}});assert.equal(denied.status(),403);
  await op.evaluate(()=>window.scrollTo(0,0));await op.screenshot({path:path.join(out,'35-terminal-operador-limitado.png'),fullPage:true,animations:'disabled'});assert.deepEqual(errors,[]);
 }finally{await limited.close()}
 return ['Terminal separada en Operación, Actividad y Configuración con navegación por teclado','Cambiar de pestaña apaga la webcam y conserva el vínculo del escáner','Pantalla de kiosco opcional y diseño móvil sin desbordamiento','Responsable de área sin configuración global y con zonas fuera de alcance deshabilitadas'];
};
