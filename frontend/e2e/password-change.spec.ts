import {test,expect} from '@playwright/test';
test('colaborador cambia su contraseña dentro de la aplicación',async({page})=>{
 await page.goto('/personal');await page.getByLabel('Usuario',{exact:true}).fill('e2e_director');await page.getByLabel('Contraseña',{exact:true}).fill(process.env.E2E_PASSWORD!);await page.getByRole('button',{name:'Ingresar',exact:true}).click();
 await page.getByRole('link',{name:'Cambiar contraseña',exact:true}).click();
 await expect(page.getByRole('heading',{name:'Cambiar contraseña',exact:true})).toBeVisible();
 await page.getByLabel('Contraseña actual',{exact:true}).fill(process.env.E2E_PASSWORD!);
 const password=process.env.E2E_PASSWORD!+'Cambio';
 await page.getByLabel('Nueva contraseña',{exact:true}).fill(password);await page.getByLabel('Confirmar nueva contraseña',{exact:true}).fill(password);await page.getByRole('button',{name:'Actualizar contraseña',exact:true}).click();
 await expect(page.getByRole('status').filter({hasText:'Contraseña actualizada'})).toBeVisible();
 await page.goto('/personal');await page.getByRole('button',{name:/Cerrar sesión/}).click();
 await page.getByLabel('Usuario',{exact:true}).fill('e2e_director');await page.getByLabel('Contraseña',{exact:true}).fill(password);await page.getByRole('button',{name:'Ingresar',exact:true}).click();await expect(page.getByRole('link',{name:'Cambiar contraseña',exact:true})).toBeVisible();
});
