// Read-only public verification: never submit registration or requests.
const {chromium}=require('../../frontend/node_modules/playwright');
const fs=require('node:fs');
const path=require('node:path');
(async()=>{
 const folder=path.resolve(process.argv[2]||'');
 const root=path.resolve(__dirname,'runtime/releases')+path.sep;
 if(!folder.startsWith(root))throw Error('Expected own release folder');
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900}});
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('https://plansaludmodelo.online/portal/cuenta');
  await page.getByRole('heading',{name:'Crear cuenta de usuario de servicios'}).waitFor();
  const text=await page.locator('body').innerText();
  if(text.includes('Datos ficticios')||text.includes('todavía no recibe solicitudes reales'))throw Error('Stale demo copy');
  const session=await (await page.request.get('https://plansaludmodelo.online/api/v1/public/session/')).json();
  const staff=await (await page.request.get('https://plansaludmodelo.online/api/v1/session/')).json();
  const catalog=await (await page.request.get('https://plansaludmodelo.online/api/v1/public/services/')).json();
  if(!session.enabled||session.authenticated||!catalog.appointments_enabled||!staff.password_only_pilot||staff.password_only_demo)throw Error('Unexpected configuration');
  await page.screenshot({path:path.join(folder,'portal-desktop.png'),fullPage:true});
  await page.setViewportSize({width:390,height:844});
  if(!await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth))throw Error('Mobile overflow');
  await page.screenshot({path:path.join(folder,'portal-mobile.png'),fullPage:true});
  if(errors.length)throw Error(errors.join('\n'));
  const result={registration_visible:true,persistent_portal_enabled:session.enabled,password_only_pilot:staff.password_only_pilot,requests_enabled:catalog.appointments_enabled,available_services:catalog.services.filter(s=>s.request_enabled).map(s=>s.slug),mobile_verified:true,accounts_created:0,requests_created:0};
  fs.writeFileSync(path.join(folder,'public-verification.json'),JSON.stringify(result,null,2)+'\n',{mode:0o600});
  console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
