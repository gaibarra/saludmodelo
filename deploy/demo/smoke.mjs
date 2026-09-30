// Read-only checks against this demo only. LOCAL mode does not verify public TLS.
import { chromium } from '../../frontend/node_modules/playwright-core/index.mjs';
import { readFile, mkdir, writeFile } from 'node:fs/promises';
import crypto from 'node:crypto';
const mode=process.argv[2];
if(!['local','public'].includes(mode)) throw Error('Use: node deploy/demo/smoke.mjs local|public');
const root=new URL('./runtime/',import.meta.url);
const credentials=JSON.parse(await readFile(new URL('accesos-demo.json',root),'utf8'));
const origin='https://plansaludmodelo.online';
if(credentials.url!==origin) throw Error('Unexpected target');
function totp(secret){
  const alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ234567';
  let bits='';for(const char of secret) bits+=alphabet.indexOf(char).toString(2).padStart(5,'0');
  const bytes=[];for(let i=0;i+8<=bits.length;i+=8)bytes.push(parseInt(bits.slice(i,i+8),2));
  const counter=Buffer.alloc(8);counter.writeBigUInt64BE(BigInt(Math.floor(Date.now()/30000)));
  const h=crypto.createHmac('sha1',Buffer.from(bytes)).update(counter).digest();const offset=h[h.length-1]&15;
  return String((h.readUInt32BE(offset)&0x7fffffff)%1000000).padStart(6,'0');
}
const browser=await chromium.launch({headless:true});
const report={mode,checked_at:new Date().toISOString(),public_tls_verified:mode==='public',checks:[]};
try {
  for(const name of ['odontologia','direccion','revision','colaborador']) {
    const account=credentials.accounts.find(a=>a.username===`demo_${name}`);
    const context=await browser.newContext({viewport:{width:1365,height:950}});
    if(mode==='local')await context.route(`${origin}/**`,async route=>{
      const req=route.request();const url=new URL(req.url());
      const response=await route.fetch({url:'http://127.0.0.1:3117'+url.pathname+url.search,headers:{...await req.allHeaders(),host:'plansaludmodelo.online','x-forwarded-proto':'https'}});
      await route.fulfill({response});
    });
    const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
    await page.goto(origin+'/personal/plan');await page.getByLabel('Usuario',{exact:true}).fill(account.username);
    await page.getByLabel('Contraseña',{exact:true}).fill(account.password);
    await page.getByRole('button',{name:'Ingresar',exact:true}).click();
    await page.getByLabel('Código de verificación o recuperación',{exact:true}).fill(totp(account.totp_secret));
    await page.getByRole('button',{name:'Verificar acceso',exact:true}).click();
    await page.getByRole('heading',{name:'Mi trabajo de hoy',exact:true}).waitFor();
    const data=await page.evaluate(async()=>{
      const s=await fetch('/api/v1/session/').then(r=>r.json());
      const services=await fetch('/api/v1/services/').then(r=>r.json());
      return {authenticated:s.authenticated,mfa:s.mfa_verified,services:services.results||services};
    });
    if(!data.authenticated||!data.mfa||data.services.length!==1||!data.services[0].name.includes('DEMO'))throw Error(`Scope/MFA check failed: ${account.username}`);
    report.checks.push(`${account.username}: login, MFA, one isolated service`);
    await page.getByRole('button',{name:/Odontología · DEMO/}).click();
    await page.getByRole('heading',{name:/Cómo identifican al paciente/}).waitFor();
    if(await page.locator('article.panel').count()!==6)throw Error('Expected six original questions');
    report.checks.push(`${account.username}: six original questions visible`);
    if(name==='odontologia')await page.screenshot({path:new URL('demo-inicio.png',root).pathname,fullPage:true});
    const paths=name==='direccion'?['/administracion','/capacidad']:name==='odontologia'?['/seguimiento','/reportes']:[];
    for(const path of paths){
      await page.goto(origin+path);await page.waitForLoadState('networkidle');
      if(!await page.getByText('DEMOSTRACIÓN · Datos ficticios de Odontología · No registrar información de pacientes',{exact:true}).isVisible())throw Error('Demo notice missing');
      if(path==='/seguimiento') {
        await page.getByLabel('Servicio de seguimiento',{exact:true}).selectOption(String(credentials.service_id));
        await page.getByRole('button',{name:/Tarea \d+: DEMO: definir suplencia por ausencia del docente/}).waitFor();
        await page.getByRole('button',{name:'Comparar tareas con capacidad',exact:true}).click();
        await page.getByText(/demo_odontologia · 2026-10-05: Dentro de capacidad/).waitFor();
      }
      if(path==='/capacidad') {
        await page.getByLabel('Institución de la capacidad').selectOption(String(credentials.institution_id));
        await page.getByRole('button',{name:'Consultar capacidad',exact:true}).click();
        await page.getByText(/demo_odontologia · 2026-10-05: 120 minutos disponibles/).first().waitFor();
        await page.screenshot({path:new URL('demo-capacidad.png',root).pathname,fullPage:true});
      }
      if(path==='/reportes') {
        await page.getByLabel('Servicio del informe').selectOption(String(credentials.service_id));
        await page.getByRole('button',{name:'Preparar borrador semanal',exact:true}).click();
        await page.getByRole('region',{name:'Borrador semanal',exact:true}).waitFor();
      }
      const text=await page.locator('body').innerText();if(text.includes('Internal Server Error')||text.includes('Application error'))throw Error(`Rendering failed ${path}`);
      report.checks.push(`${account.username}: ${path} rendered`);
      if(name==='odontologia'&&path==='/seguimiento')await page.screenshot({path:new URL('demo-seguimiento.png',root).pathname,fullPage:true});
    }
    if(errors.length)throw Error(`Browser JavaScript errors: ${errors.join('; ')}`);
    await context.close();
  }
  await writeFile(new URL(`smoke-${mode}.json`,root),JSON.stringify(report,null,2),{mode:0o600});
  console.log(JSON.stringify(report,null,2));
} catch(error) {
  let message=String(error?.stack||error);
  for(const account of credentials.accounts)for(const secret of [account.password,account.totp_secret,...account.recovery_codes])message=message.replaceAll(secret,'[REDACTED]');
  console.error(message);process.exitCode=1;
} finally {await browser.close();}
