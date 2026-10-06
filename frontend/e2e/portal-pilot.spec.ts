import { test, expect } from '@playwright/test';
test('portal persistente registra, solicita en ambas escuelas y reingresa', async ({page})=>{
 test.skip(process.env.E2E_PORTAL_PILOT !== '1','Requires isolated portal fixture');
 await page.goto('/portal/cuenta');
 await expect(page.getByRole('heading',{name:'Crear cuenta de usuario de servicios'})).toBeVisible();
 await page.getByLabel('Nombre',{exact:true}).fill('Usuario del ensayo aislado');
 await page.getByLabel('Correo electrónico').fill('portal@example.invalid');
 await page.getByLabel('Teléfono de contacto').fill('9991234567');
 await page.getByLabel('Contraseña',{exact:true}).fill(process.env.E2E_PASSWORD!);
 await page.getByRole('button',{name:'Crear cuenta',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Solicitar atención'})).toBeVisible();
 for(const slug of ['odontologia','psicologia']){
  await page.getByLabel('Servicio',{exact:true}).selectOption(slug);
  await page.getByRole('button',{name:'Enviar solicitud',exact:true}).click();
  await expect(page.getByRole('status')).toContainText('Solicitud enviada');
 }
 await expect(page.locator('.portal-request')).toHaveCount(2);
 await page.reload();await expect(page.locator('.portal-request')).toHaveCount(2);
 await page.getByRole('button',{name:'Cerrar sesión',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Crear cuenta de usuario de servicios'})).toBeVisible();
 await page.getByRole('button',{name:'Ya tengo cuenta'}).click();
 await page.getByLabel('Correo electrónico').fill('portal@example.invalid');
 await page.getByLabel('Contraseña',{exact:true}).fill(process.env.E2E_PASSWORD!);
 await page.getByRole('button',{name:'Ingresar',exact:true}).click();
 await expect(page.locator('.portal-request')).toHaveCount(2);
 page.on('dialog',d=>d.accept());
 await page.getByRole('button',{name:'Retirar solicitud'}).first().click();
 await expect(page.getByText('Solicitud retirada.',{exact:true})).toBeVisible();
 await expect(page.locator('.portal-request').filter({hasText:'Retirada'})).toHaveCount(1);
 await page.setViewportSize({width:390,height:844});
 expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
});
