const {chromium}=require('playwright'),assert=require('node:assert/strict'),path=require('node:path'),fs=require('node:fs');
(async()=>{
 const browser=await chromium.launch({channel:'chrome',headless:true}),base=process.env.ST_TEST_URL,errors=[];
 try{
  const owner=await browser.newContext({viewport:{width:1440,height:1000}});
  await owner.addCookies([{name:'st_session',value:'owner',url:base}]);
  const page=await owner.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);await page.getByRole('button',{name:'Personas y permisos',exact:true}).click();
  await page.getByLabel('Buscar personas').fill('PERSONA NUEVO INGRESO');
  await page.locator('tr').filter({hasText:'Persona Nuevo Ingreso'}).click();
  const panel=page.locator('article').filter({has:page.getByRole('heading',{name:'Primer ingreso sin enlace ni QR',exact:true})});
  await panel.getByRole('button',{name:'Generar contraseña temporal individual',exact:true}).waitFor();
  const response=page.waitForResponse(r=>r.url().endsWith('/api/users/initial-password')&&r.request().method()==='POST');
  await panel.getByRole('button',{name:'Generar contraseña temporal individual',exact:true}).click();
  const issued=await(await response).json();assert(issued.temporary_password);assert(!issued.activation_url);assert(!issued.activation_qr);
  await panel.getByRole('button',{name:'Ocultar contraseña',exact:true}).click();
  assert.equal(await panel.locator('img').count(),0);assert.equal(await panel.locator('code').count(),0);
  await panel.evaluate(el=>el.scrollIntoView({block:'start'}));
  await page.screenshot({path:path.join(__dirname,'../design/39-primer-ingreso-individual.png'),fullPage:true,animations:'disabled'});
  const holder=await browser.newContext({viewport:{width:390,height:844}}),phone=await holder.newPage();phone.on('pageerror',e=>errors.push(e.message));
  await phone.goto(base);await phone.getByLabel('Matrícula',{exact:true}).fill(process.env.ST_TEST_USERNAME);await phone.getByLabel('Contraseña',{exact:true}).fill(issued.temporary_password);
  await phone.getByRole('button',{name:'Continuar',exact:true}).click();await phone.getByRole('heading',{name:'Hazla tuya.',exact:true}).waitFor();
  assert.equal(await phone.getByLabel('Código de activación privado',{exact:true}).count(),0);
  assert.equal(await phone.locator('img').count(),0);
  assert(await phone.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await phone.screenshot({path:path.join(__dirname,'../design/40-primer-ingreso-movil.png'),fullPage:true,animations:'disabled'});
  await phone.getByLabel('Nueva contraseña',{exact:true}).fill('MiPrivadaBrowser123!');await phone.getByLabel('Confirmar contraseña',{exact:true}).fill('MiPrivadaBrowser123!');
  await phone.getByRole('button',{name:'Continuar con la verificación',exact:true}).click();await phone.getByRole('heading',{name:'Protege tu identidad.',exact:true}).waitFor();
  assert.equal(await phone.getByAltText('Código QR para registrar tu segundo factor',{exact:true}).count(),1);
  await page.setViewportSize({width:390,height:844});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);
  fs.writeFileSync(path.join(__dirname,'resultado-primer-ingreso-browser.json'),JSON.stringify({checks:['Emisión administrativa sin QR ni enlace','Contraseña oculta antes de capturar','Ingreso directo a cambio de contraseña en móvil','Sin pantalla de activación privada','MFA del titular conservado','Sin desbordamiento móvil'],pageErrors:errors},null,2));
  console.log('6 comprobaciones visuales aprobadas; sin errores de JavaScript ni contraseñas en capturas.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exit(1)});
