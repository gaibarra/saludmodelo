import {test,expect} from '@playwright/test';
test('logo institucional: portal personal módulos modales e informe impreso',async({page})=>{
 page.setDefaultTimeout(15000);
 for(const route of ['/','/portal','/portal/directorio','/portal/cuenta','/portal/servicios/odontologia','/personal']){
  await page.goto(route);const logo=page.getByAltText('Logo institucional de Modelo').first();await expect(logo).toBeVisible();await expect.poll(()=>logo.evaluate((e:HTMLImageElement)=>e.complete&&e.naturalWidth>0)).toBe(true);
 }
 await page.screenshot({path:'../docs/capturas/logo-acceso-0.39.2.png',fullPage:true});
 await page.getByLabel('Usuario',{exact:true}).fill('e2e_dental_director');await page.getByLabel('Contraseña',{exact:true}).fill(process.env.E2E_PASSWORD!);await page.getByRole('button',{name:'Ingresar',exact:true}).click();await expect(page.getByRole('heading',{name:'Panel académico',exact:true})).toBeVisible();
 for(const route of ['/personal','/personal/plan','/escuelas','/caja','/academico','/academico/evaluaciones','/administracion','/consultas','/cumplimiento','/capacidad','/decisiones','/seguimiento','/reportes','/seguridad','/solicitudes-servicio']){await page.goto(route);await expect(page.getByAltText('Logo institucional de Modelo').first()).toBeVisible();}
 await page.goto('/escuelas');await page.getByRole('button',{name:'＋ Crear cuenta',exact:true}).click();await expect(page.getByRole('dialog').getByAltText('Logo institucional de Modelo')).toBeVisible();await page.getByRole('dialog').getByRole('button',{name:'Cancelar',exact:true}).click();
 const cycles=await (await page.request.get('/api/v1/academic/cycles/')).json();const cycle=cycles.results.find((c:{name:string})=>c.name==='Ciclo dental de prueba');expect(cycle).toBeTruthy();const reports=await (await page.request.get(`/api/v1/academic/cycles/${cycle.id}/reports/`)).json();await page.goto(`/academico/informes/${reports.results[0].id}`);
 const logo=page.locator('.academic-report-content').getByAltText('Logo institucional de Modelo');await expect(logo).toBeVisible();await expect.poll(()=>logo.evaluate((e:HTMLImageElement)=>e.complete&&e.naturalWidth>0)).toBe(true);
 await page.emulateMedia({media:'print'});await expect(logo).toBeVisible();await expect(page.locator('.institutional-masthead')).toBeHidden();await page.pdf({path:'../docs/capturas/logo-informe-0.39.2.pdf',format:'A4',printBackground:true});await page.emulateMedia({media:'screen'});
 await page.setViewportSize({width:390,height:844});for(const route of ['/','/personal','/caja','/escuelas']){await page.goto(route);await expect(page.getByAltText('Logo institucional de Modelo').first()).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);}
 await page.goto('/');await page.screenshot({path:'../docs/capturas/logo-portal-movil-0.39.2.png',fullPage:true});
});
