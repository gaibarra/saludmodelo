// Verify a newly authorized account without changing its provisional password.
const {chromium}=require('../../frontend/node_modules/playwright');
const fs=require('node:fs');const path=require('node:path');
(async()=>{
 const folder=path.resolve(__dirname,'runtime/odontologia-20261013');
 const data=JSON.parse(fs.readFileSync(path.join(folder,'accounts.json'),'utf8'));
 let password='';for await(const chunk of process.stdin)password+=chunk;password=password.trim();
 const browser=await chromium.launch({headless:true});
 try{
  const page=await browser.newPage();
  await page.goto('https://plansaludmodelo.online/personal');
  await page.getByLabel('Usuario',{exact:true}).fill(data.rows[0].username);
  await page.getByLabel('Contraseña',{exact:true}).fill(password);
  await page.getByRole('button',{name:'Ingresar',exact:true}).click();
  await page.getByRole('link',{name:'Cambiar contraseña',exact:true}).click();
  await page.getByRole('heading',{name:'Cambiar contraseña',exact:true}).waitFor();
  for(const label of ['Contraseña actual','Nueva contraseña','Confirmar nueva contraseña'])await page.getByLabel(label,{exact:true}).waitFor();
  const response=await page.request.get('https://plansaludmodelo.online/api/v1/schools/');
  const schools=await response.json();if(!response.ok()||schools.results.length)throw Error('Unexpected school administration access');
  await page.screenshot({path:path.join(folder,'password-form.png'),fullPage:true});
  await page.goto('https://plansaludmodelo.online/personal');await page.getByRole('button',{name:/Cerrar sesión/}).click();
  const result={login_verified:true,password_form_visible:true,school_administration_granted:false,password_changed:false};
  fs.writeFileSync(path.join(folder,'https-verification.json'),JSON.stringify(result,null,2)+'\n',{mode:0o600});console.log(JSON.stringify(result));
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exit(1)});
