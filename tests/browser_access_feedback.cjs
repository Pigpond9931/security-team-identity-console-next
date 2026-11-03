const assert=require('node:assert/strict'),path=require('node:path');
module.exports=async({page,context,base})=>{
 const popup=()=>page.getByRole('dialog',{name:'Resultado de acceso',exact:true});
 const baseline=page.waitForResponse(r=>r.url().includes('/api/access/latest?limit=1'));
 await page.getByRole('button',{name:'Terminal de Acceso',exact:true}).click();await baseline;
 assert.equal(await popup().count(),0,'No debe anunciar de nuevo una lectura histórica al abrir la terminal');
 await page.getByRole('button',{name:'Gafete QR',exact:true}).click();await page.getByText('Introducir contenido QR',{exact:true}).click();
 const badge=await(await context.request.get(base+'api/users/qr-badge')).json();
 await page.getByRole('textbox',{name:'Token QR',exact:true}).fill(badge.badge.token);
 await page.getByRole('button',{name:'Verificar QR',exact:true}).click();
 await popup().getByRole('heading',{name:'Acceso permitido',exact:true}).waitFor();
 assert(await page.getByRole('button',{name:'Pantalla de kiosco',exact:true}).count());
 assert.equal(await page.evaluate(()=>document.body.style.overflow),'hidden');
 const bounds=await popup().boundingBox(),viewport=page.viewportSize();assert(bounds.width>=viewport.width&&bounds.height>=viewport.height);
 await page.screenshot({path:path.join(__dirname,'../design/24-acceso-permitido.png'),fullPage:true});
 // Un lector USB tipo teclado puede enviar otra credencial sin cerrar el aviso.
 await page.keyboard.type('9999999901',{delay:10});await page.keyboard.press('Enter');
 await popup().getByRole('heading',{name:'Acceso denegado',exact:true}).waitFor();
 await popup().getByText('TARJETA RFID',{exact:true}).waitFor();
 await popup().getByText('RFID:9999999901',{exact:true}).waitFor();
 await page.setViewportSize({width:390,height:844});
 assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
 await page.screenshot({path:path.join(__dirname,'../design/25-acceso-denegado-movil.png'),fullPage:true});
 await popup().waitFor({state:'detached',timeout:6500});
 assert.equal(await page.evaluate(()=>document.body.style.overflow),'');
 assert(await page.getByLabel('Lector RFID USB 125 kHz',{exact:true}).evaluate(el=>el===document.activeElement));
 // Consulta de estado repetida: no debe reabrir el aviso del mismo evento.
 await page.waitForResponse(r=>r.url().includes('/api/access/latest?limit=1'));
 assert.equal(await popup().count(),0);
 await page.setViewportSize({width:1440,height:1000});
 await page.getByRole('textbox',{name:'Token QR',exact:true}).fill('QR-INVALIDO-PRUEBA');
 await page.getByRole('button',{name:'Verificar QR',exact:true}).click();
 await popup().getByRole('heading',{name:'Acceso denegado',exact:true}).waitFor();
 await page.keyboard.press('Escape');await popup().waitFor({state:'detached'});
 const events=await(await context.request.get(base+'api/access/events?limit=2')).json();
 assert.equal(events.events[0].method,'QR_BADGE');assert.equal(events.events[1].method,'RFID_125KHZ');
 return ['Aviso automático de acceso permitido por QR sin activar kiosco','RFID emulado durante el aviso cambia inmediatamente a acceso denegado','Aviso de pantalla completa, diseño móvil, cierre automático y foco del lector','Escape cierra el aviso y las consultas repetidas no anuncian de nuevo la última lectura'];
};
