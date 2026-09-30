// Public HTTPS checks. No enrollment of authenticators belonging to named users.
import {chromium} from '../../frontend/node_modules/playwright-core/index.mjs';
import {readFile,writeFile} from 'node:fs/promises';
import crypto from 'node:crypto';
const runtime=new URL('./runtime/',import.meta.url);
const folder=(await readFile(new URL('active-release.txt',runtime),'utf8')).trim();
const manifest=JSON.parse(await readFile(folder+'/manifest.json','utf8'));
if(!['0.35.0','0.35.1','0.35.2'].includes(manifest.version)||manifest.domain!=='plansaludmodelo.online')throw Error('Unexpected active release');
const bootstrap=JSON.parse(await readFile(folder+'/bootstrap.json','utf8'));
const legacy=JSON.parse(await readFile(new URL('accesos-demo.json',runtime),'utf8'));
const origin='https://plansaludmodelo.online';
function totp(secret){const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';let bits='';for(const ch of secret)bits+=alphabet.indexOf(ch).toString(2).padStart(5,'0');const bytes=[];for(let i=0;i+8<=bits.length;i+=8)bytes.push(parseInt(bits.slice(i,i+8),2));const counter=Buffer.alloc(8);counter.writeBigUInt64BE(BigInt(Math.floor(Date.now()/30000)));const h=crypto.createHmac('sha1',Buffer.from(bytes)).update(counter).digest(),off=h[h.length-1]&15;return String((h.readUInt32BE(off)&0x7fffffff)%1000000).padStart(6,'0');}
const browser=await chromium.launch({headless:true});const checks=[];
try{
 for(const a of bootstrap.accounts){
  const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(origin+'/personal');await page.getByLabel('Usuario',{exact:true}).fill(a.username);await page.getByLabel('Contraseña',{exact:true}).fill(a.password);
  const response=page.waitForResponse(r=>r.url()===origin+'/api/v1/session/'&&r.request().method()==='POST');
  await page.getByRole('button',{name:'Ingresar',exact:true}).click();const r=await response;if(r.status()!==200)throw Error('Login failed for '+a.role+' '+r.status());const state=await r.json();
  if(state.username!==a.username||!state.mfa_required||state.authenticated||!state.mfa_configured)throw Error('Unexpected MFA state for '+a.role);
  if(state.mfa_enabled)await page.getByLabel('Código de verificación o recuperación',{exact:true}).waitFor();
  else await page.getByRole('heading',{name:'Activar autenticador',exact:true}).waitFor();
  const denied=await page.evaluate(async()=>{const r=await fetch('/api/v1/schools/');return r.status;});if(denied!==403)throw Error('MFA gate did not block access');
  await page.goto(origin);await page.getByRole("heading",{name:"Tu bienestar tiene un lugar aquí.",exact:true}).waitFor();
  if(await page.getByLabel("Código de verificación o recuperación",{exact:true}).count())throw Error("Pending MFA replaced public cover");
  checks.push({account:a.username,public_cover_with_pending_mfa:true,password_login:true,personal_mfa_setup_required:!state.mfa_enabled,protected_api_blocked_before_mfa:true});await context.close();
 }
 for(const username of ['demo_direccion','demo_odontologia']){
  const a=legacy.accounts.find(a=>a.username===username);if(!a)throw Error('Missing legacy test account');
  const context=await browser.newContext();const page=await context.newPage();page.setDefaultTimeout(20000);
  await page.goto(origin+'/personal');await page.getByLabel('Usuario',{exact:true}).fill(a.username);await page.getByLabel('Contraseña',{exact:true}).fill(a.password);await page.getByRole('button',{name:'Ingresar',exact:true}).click();
  await page.getByLabel('Código de verificación o recuperación',{exact:true}).fill(totp(a.totp_secret));await page.getByRole('button',{name:'Verificar acceso',exact:true}).click();await page.getByRole('heading',{name:'Panel académico',exact:true}).waitFor();
  if(username==='demo_direccion'){
   await page.goto(origin+'/escuelas');await page.getByRole('button',{name:/Escuela de Odontología/}).click();await page.getByText('Consulta académica autorizada · Sin permiso para modificar registros',{exact:true}).waitFor();
   const result=await page.evaluate(async()=>{const schools=await fetch('/api/v1/schools/').then(r=>r.json());const dental=schools.results.find(s=>s.code==='odontologia');const forbidden=await fetch(`/api/v1/schools/${dental.id}/management/`);return {codes:schools.results.map(s=>s.code),dental_readonly:!dental.can_manage,management_status:forbidden.status};});if(!result.dental_readonly||result.management_status!==404)throw Error('Academic sharing exceeded scope');
   checks.push({account:username,public_mfa_login:true,health_dashboard:true,dental_academic_readonly:true,foreign_management_denied:true});
  }else{
   const result=await page.evaluate(async()=>{const r=await fetch('/api/v1/services/').then(r=>r.json());return r.results||r;});if(result.length!==1||result[0].id!==bootstrap.dental_services[0])throw Error('Legacy dental service scope changed');
   checks.push({account:username,public_mfa_login:true,own_dental_service_preserved:true});
  }
  await context.close();
 }
 await writeFile(folder+'/public-smoke.json',JSON.stringify({checked_at:new Date().toISOString(),public_https_verified:true,checks},null,2)+'\n',{mode:0o600});
 console.log('HTTPS público: tres cuentas institucionales verificadas hasta su verificación MFA personal; dos cuentas demo con MFA y permisos escolares comprobados.');
}catch(e){console.error(e.message);process.exitCode=1;}finally{await browser.close();}
