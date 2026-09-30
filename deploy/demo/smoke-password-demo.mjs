import {chromium} from '../../frontend/node_modules/playwright-core/index.mjs';
import {readFile,writeFile} from 'node:fs/promises';
const folder=(await readFile(new URL('./runtime/active-release.txt',import.meta.url),'utf8')).trim();
const manifest=JSON.parse(await readFile(folder+'/manifest.json','utf8'));
if(!['0.35.3','0.35.4'].includes(manifest.version)||manifest.domain!=='plansaludmodelo.online')throw Error('Unexpected demo release');
const bootstrap=JSON.parse(await readFile(folder+'/bootstrap.json','utf8'));
const legacy=JSON.parse(await readFile(new URL('./runtime/accesos-demo.json',import.meta.url),'utf8'));
const accounts=[...bootstrap.accounts,...legacy.accounts.filter(a=>['demo_direccion','demo_odontologia'].includes(a.username))];
const browser=await chromium.launch({headless:true}),results=[];const origin='https://plansaludmodelo.online';
try{
 for(const account of accounts){
  const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(origin+'/personal');await page.getByRole('status').filter({hasText:'Acceso con usuario y contraseña'}).waitFor();
  if(await page.getByLabel('Etapas de acceso').count())throw Error('Obsolete two-step label');
  await page.getByLabel('Usuario',{exact:true}).fill(account.username);await page.getByLabel('Contraseña',{exact:true}).fill(account.password);
  const next=page.waitForResponse(r=>r.url()===origin+'/api/v1/session/'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Ingresar',exact:true}).click();const response=await next;const session=await response.json();
  if(response.status()!==200||!session.authenticated||session.mfa_required||!session.password_only_demo)throw Error('Password-only login failed for '+account.username);
  await page.getByRole('heading',{name:'Panel académico',exact:true}).waitFor();
  await page.reload();await page.getByRole('heading',{name:'Panel académico',exact:true}).waitFor();
  if(account.role==='salud'||account.role==='odontologia'||account.username==='demo_direccion'){
   await page.goto(origin+'/escuelas');
   const result=await page.evaluate(async()=>{const r=await fetch('/api/v1/schools/');const rows=(await r.json()).results;const dental=rows.find(s=>s.code==='odontologia');return {status:r.status,can_manage:dental?.can_manage,management:dental?(await fetch(`/api/v1/schools/${dental.id}/management/`)).status:null};});
   if(result.status!==200)throw Error('Schools unavailable');
   if(account.role==='salud'||account.username==='demo_direccion'){if(result.can_manage||result.management!==404)throw Error('Health access exceeds permission');}
   if(account.role==='odontologia'&&(!result.can_manage||result.management!==200))throw Error('Dental management missing');
  }
  results.push({account:account.username,password_only_login:true,reload_authenticated:true});await context.close();
 }
 await writeFile(folder+'/public-password-smoke.json',JSON.stringify({checked_at:new Date().toISOString(),https_verified:true,results},null,2)+'\n',{mode:0o600});
 console.log('Cinco cuentas verificadas por HTTPS: acceso sólo con contraseña, sesión conservada al recargar y permisos escolares mantenidos.');
}finally{await browser.close();}
