const {chromium}=require(process.env.PLAYWRIGHT_MODULE||'playwright');
const {execFileSync}=require('node:child_process');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const output=process.env.ST_QA_OUTPUT||path.resolve('..','qa-browser');
fs.mkdirSync(output,{recursive:true});
fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify({ok:false,status:'running',startedAt:new Date().toISOString()}));
fs.writeFileSync(path.join(output,'resultado-cctv-fluidez.json'),JSON.stringify({ok:false,status:'not_run'}));
const accessibility=[];
async function audit(page,name){
 await page.evaluate(fs.readFileSync(require.resolve('axe-core/axe.min.js'),'utf8'));
 const results=await page.evaluate(async()=>axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21a','wcag21aa']}}));
 const violations=results.violations.map(v=>({id:v.id,impact:v.impact,help:v.help,targets:v.nodes.map(n=>n.target)}));
 accessibility.push({screen:name,violations});
 fs.writeFileSync(path.join(output,'accessibility.json'),JSON.stringify(accessibility,null,2));
 assert.deepEqual(violations,[],`Accessibility violations: ${name}`);
}
const contrast=(a,b)=>{
 const light=rgb=>{const v=rgb.match(/[\d.]+/g).slice(0,3).map(x=>Number(x)/255).map(x=>x<=.04045?x/12.92:((x+.055)/1.055)**2.4);return v[0]*.2126+v[1]*.7152+v[2]*.0722};
 const x=light(a),y=light(b);return (Math.max(x,y)+.05)/(Math.min(x,y)+.05);
};
(async()=>{
 const browser=await chromium.launch({channel:process.env.ST_TEST_BROWSER_CHANNEL||'chrome',headless:true,args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream']});
 const checks=[],errors=[];let page;
 try{
  const base=process.env.ST_TEST_URL;
  const reduced=await browser.newContext({reducedMotion:'reduce'}),early=await reduced.newPage();
  await early.route('**/assets/app.js',route=>route.abort());
  await early.goto(base);assert.equal(await early.locator('html').getAttribute('data-motion'),'reduced');checks.push('OS reduced motion is applied before React loads');
  await reduced.close();
  const context=await browser.newContext({viewport:{width:1440,height:1000},locale:'es-MX'});
  page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(base);await page.getByRole('heading',{name:/Un espacio seguro/}).waitFor();
  await audit(page,'login');
  await page.screenshot({path:path.join(output,'01-inicio-next.png'),fullPage:true});
  const motion=page.getByLabel('Preferencia de movimiento',{exact:true});
  await motion.selectOption('reduced');assert.equal(await page.locator('html').getAttribute('data-motion'),'reduced');
  await page.reload();await page.getByRole('heading',{name:/Un espacio seguro/}).waitFor();
  assert.equal(await motion.inputValue(),'reduced');checks.push('Motion preference persists across reloads');
  await page.getByRole('textbox',{name:'Matrícula',exact:true}).fill(process.env.ST_TEST_ACCOUNT);
  await page.getByLabel('Contraseña',{exact:true}).fill('IngresoFicticioNext123!');
  await page.getByRole('button',{name:'Continuar',exact:true}).click();
  await page.getByLabel('Nueva contraseña',{exact:true}).fill('PrivadaFicticiaNext123!');
  await page.getByLabel('Confirmar contraseña',{exact:true}).fill('PrivadaFicticiaNext123!');
  await page.getByRole('button',{name:'Continuar con la verificación'}).click();
  await page.getByRole('heading',{name:'Protege tu identidad.'}).waitFor();
  const enrollment=await(await context.request.get(base+'api/session')).json();assert.equal(enrollment.stage,'enroll');
  const code=execFileSync(process.env.ST_TEST_PYTHON,['-c','import sys,pyotp;print(pyotp.TOTP(sys.stdin.read()).now())'],{input:enrollment.enrollment_key,encoding:'utf8'}).trim();
  await page.getByRole('textbox',{name:'Código de verificación'}).fill(code);
  await page.getByRole('button',{name:'Activar segundo factor'}).click();
  await page.getByRole('heading',{name:'Conserva tu acceso.'}).waitFor();
  assert.equal(await page.locator('.recovery-grid code').count(),8);
  await page.getByRole('checkbox',{name:'Guardé mis códigos en un lugar privado'}).check();
  await page.getByRole('button',{name:'Entrar a mi espacio'}).click();
  await page.getByRole('checkbox',{name:/He leído y acepto/}).check();
  await page.getByRole('button',{name:'Acepto Términos y Activar mi Gafete'}).click();
  await page.getByRole('heading',{name:'Centro de operaciones',exact:true}).waitFor();checks.push('Real individual-password, private-password, MFA, recovery and current-policy onboarding');
  assert.equal(await page.locator('.metric-card').count(),4);
  assert.equal(await page.locator('.operation-link').count(),3);
  await audit(page,'operations');
  const colors=await page.locator('.button.primary').first().evaluate(e=>({fg:getComputedStyle(e).color,bg:getComputedStyle(e).backgroundColor}));
  assert(contrast(colors.fg,colors.bg)>=4.5);checks.push('Primary button text contrast exceeds 4.5:1');
  await page.screenshot({path:path.join(output,'02-centro-operaciones-next.png'),fullPage:true});
  await page.locator('.operations-links').getByRole('button',{name:/Personas y permisos/}).click();
  await page.getByLabel('Buscar personas',{exact:true}).fill(process.env.ST_TEST_ACCOUNT);
  await page.getByRole('row').filter({hasText:process.env.ST_TEST_ACCOUNT}).click();
  const drawer=page.getByRole('dialog',{name:'Detalle de identidad'});await drawer.waitFor();
  await drawer.getByRole('button',{name:'Gafete QR',exact:true}).click();
  await drawer.getByRole('img',{name:'Gafete QR de acceso',exact:true}).waitFor();
  await audit(page,'identity-drawer');
  await page.keyboard.press('Escape');await drawer.waitFor({state:'hidden'});checks.push('Directory, own current QR and keyboard dismissal');
  await page.getByRole('button',{name:/Mi QR de acceso/,exact:true}).click();
  await page.getByRole('button',{name:'Actualizar QR',exact:true}).click();
  await page.getByRole('img',{name:'Gafete QR de acceso',exact:true}).waitFor();checks.push('Current QR refresh uses the real API');
  assert(await page.locator('.zone-pending').count()>0);checks.push('Assigned zones with missing internal licenses display a pending status');
  for(const width of [768,390,320]){
   await page.setViewportSize({width,height:900});
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`overflow at ${width}`);
   await page.screenshot({path:path.join(output,`03-qr-${width}-next.png`),fullPage:true});
  }
  checks.push('Tablet and mobile QR screens fit viewport');
  await audit(page,'mobile-qr');
  await page.getByRole('button',{name:'Abrir navegación',exact:true}).click();
  await page.getByRole('button',{name:'Terminal de Acceso',exact:true}).click();
  await page.getByRole('heading',{name:'Terminal de Acceso',exact:true}).waitFor();
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));checks.push('Mobile terminal remains navigable');
  await audit(page,'mobile-terminal');
  assert.equal(await page.locator('html').getAttribute('data-motion'),'reduced');
  assert.equal(await page.locator('.topbar .qr-quick-button').evaluate(e=>getComputedStyle(e).transitionDuration),'0s');
  await page.setViewportSize({width:1440,height:1000});
  checks.push(...await require('./browser_cameras.cjs')({page,context,base,browser}));
  await audit(page,'surveillance');
  checks.push('Automated WCAG 2.1 AA checks on six fixture screens');
  assert.deepEqual(errors,[]);
  const report={ok:true,checks,pageErrors:errors,accessibility,backend:'real isolated SQLite + Windows DPAPI',productionDataUsed:false};
  fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
 }catch(e){fs.writeFileSync(path.join(output,'validation.json'),JSON.stringify({ok:false,status:'failed',error:e.message,checks,pageErrors:errors,accessibility},null,2));if(page)await page.screenshot({path:path.join(output,'failure.png'),fullPage:true}).catch(()=>{});throw e;}
 finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
