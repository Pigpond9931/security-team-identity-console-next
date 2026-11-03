const assert=require('node:assert/strict'),path=require('node:path');
module.exports=async({page,context,base,browser})=>{
 const origin=new URL(base).origin,state=await(await context.request.get(base+'api/session')).json();
 async function action(p,b,ctx=context,csrf=state.csrf){const r=await ctx.request.post(base+'api/browser-camera/'+p,{headers:{Origin:origin,'X-CSRF-Token':csrf},data:b});assert.equal(r.status(),200,p);return r.json()}
 const link=await action('create',{name:'Cámara secundaria de prueba',zone:'MONITORING_CCTV'});
 const temporary=await browser.newContext();
 try{
  const terms=await(await temporary.request.get(base+'api/terms')).json();
  const claimed=await action('claim',{ticket:new URL(link.pair_url).hash.split('ticket=')[1]},temporary,terms.csrf);
  await action('approve',{id:link.id,confirmation:claimed.confirmation});
  await page.getByRole('button',{name:/02 Cámara secundaria de prueba/}).waitFor();
  await page.getByRole('button',{name:'Cámara siguiente',exact:true}).click();
  await page.getByText('Cámara 2 de 2',{exact:true}).waitFor();
  async function counts(){return(await action('list',{})).channels.map(c=>({id:c.id,n:c.viewers}))}
  await page.waitForTimeout(700);assert.equal((await counts()).find(c=>c.id!==link.id).n,0,'cambiar de cámara libera la vista anterior');
  await page.getByRole('button',{name:'Mosaico',exact:true}).click();await page.locator('.surveillance-views.grid .browser-camera-card').nth(1).waitFor();
  await page.waitForTimeout(700);assert((await counts()).every(c=>c.n===1));
  await page.screenshot({path:path.join(__dirname,'../design/29-centro-vigilancia-mosaico.png'),fullPage:true,animations:'disabled'});
  await page.getByRole('button',{name:'Individual',exact:true}).click();await page.locator('.surveillance-views.focus .browser-camera-card').waitFor();assert.equal(await page.locator('.browser-camera-card').count(),1);
  await page.getByRole('button',{name:'Ronda automática',exact:true}).click();assert.equal(await page.getByRole('button',{name:/Ronda automática/}).getAttribute('aria-pressed'),'true');
  await page.getByText('Cámara 1 de 2 · Ronda cada 15 s',{exact:true}).waitFor({timeout:18000});
  await page.getByRole('button',{name:/Ronda automática/}).click();
  await page.getByRole('button',{name:'Pantalla completa',exact:true}).click();await page.getByRole('button',{name:'Salir de pantalla completa',exact:true}).waitFor();await page.getByRole('button',{name:'Salir de pantalla completa',exact:true}).click();await page.waitForFunction(()=>!document.fullscreenElement&&!document.querySelector('.surveillance-center').classList.contains('surveillance-full'));
  await page.setViewportSize({width:390,height:844});await page.waitForFunction(()=>document.querySelector('.sidebar').getBoundingClientRect().right<=1);await page.waitForTimeout(300);assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));assert(await page.evaluate(()=>{const root=document.querySelector('.surveillance-center').getBoundingClientRect();return ['.surveillance-heading','.surveillance-toolbar','.surveillance-stage','.surveillance-navigation'].every(s=>document.querySelector(s).getBoundingClientRect().right<=root.right+1)}));await page.screenshot({path:path.join(__dirname,'../design/30-centro-vigilancia-movil.png'),fullPage:true,animations:'disabled'});await page.setViewportSize({width:1440,height:1000});
  await page.getByRole('tab',{name:'Configurar cámaras',exact:true}).click();await page.waitForTimeout(700);assert((await counts()).every(c=>c.n===0),'configuración no transmite cámaras');
  await action('revoke',{id:link.id});await page.getByRole('tab',{name:'Vigilancia',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.browser-camera-card video')?.videoWidth>0,{},{timeout:20000});
 }finally{await temporary.close()}
};
