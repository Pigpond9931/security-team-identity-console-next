const assert=require('node:assert/strict'),path=require('node:path');
module.exports=async({page,context,base,browser})=>{
 const out=path.join(__dirname,'..','design');
 await page.getByRole('button',{name:'Terminal de Acceso',exact:true}).click();
 await page.getByRole('button',{name:'Teléfono',exact:true}).click();
 await page.getByRole('button',{name:'Vincular teléfono como escáner',exact:true}).click();
 const delivery=page.getByRole('link',{name:'Abrir escáner en el teléfono',exact:true});await delivery.waitFor();const pairUrl=await delivery.getAttribute('href');
 await page.screenshot({path:path.join(out,'17-vincular-telefono.png'),fullPage:true});
 const phoneContext=await browser.newContext({viewport:{width:390,height:844},permissions:['camera']});const phone=await phoneContext.newPage();const errors=[];phone.on('pageerror',e=>errors.push(e.message));
 try{
  await phone.goto(pairUrl);await phone.getByRole('heading',{name:'Confirma este código en la laptop',exact:true}).waitFor();
  await page.getByRole('button',{name:'Confirmar teléfono',exact:true}).waitFor();
  assert.equal((await phone.locator('.phone-confirm-code').innerText()).trim(),(await page.locator('.phone-confirm-code').innerText()).trim());
  assert.equal(await phone.getByRole('button',{name:'Encender cámara del teléfono',exact:true}).count(),0);
  await phone.screenshot({path:path.join(out,'18-confirmar-telefono.png'),fullPage:true});
  await page.getByRole('button',{name:'Confirmar teléfono',exact:true}).click();
  await phone.getByRole('button',{name:'Encender cámara del teléfono',exact:true}).click();
  await phone.waitForFunction(()=>document.querySelector('video')?.videoWidth>0);
  await phone.getByRole('button',{name:'Apagar cámara del teléfono',exact:true}).click();
  const badge=await(await context.request.get(base+'api/users/qr-badge')).json();
  await phone.getByLabel('Imagen QR del teléfono',{exact:true}).setInputFiles({name:'gafete.png',mimeType:'image/png',buffer:Buffer.from(badge.qr_png_base64,'base64')});
  await phone.getByRole('heading',{name:'VERIFICADO',exact:true}).waitFor();
  await page.getByRole('heading',{name:'VERIFICADO',exact:true}).waitFor();
  await page.getByRole('dialog',{name:'Resultado de acceso',exact:true}).getByRole('heading',{name:'Acceso permitido',exact:true}).waitFor();
  await page.getByRole('button',{name:'Siguiente lectura',exact:true}).click();
  assert(await phone.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.equal((await phoneContext.request.get(base+'api/data')).status(),401);
  await phone.screenshot({path:path.join(out,'19-escaner-telefono.png'),fullPage:true});
  await page.getByRole('button',{name:'Desvincular teléfono',exact:true}).click();
  await phone.getByRole('alert').filter({hasText:/desvinculado|vínculo|Vínculo/}).waitFor();
  assert.deepEqual(errors,[]);
 }finally{await phoneContext.close()}
 return ['Vinculación del escáner mediante QR de un solo uso y confirmación en la laptop','Cámara del navegador móvil probada con dispositivo simulado','Lectura del gafete desde el teléfono reflejada en la laptop sin sesión administrativa en el teléfono','Revocación del teléfono y diseño móvil sin desbordamiento'];
};
