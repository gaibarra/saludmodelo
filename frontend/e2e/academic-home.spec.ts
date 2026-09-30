import { test, expect } from "@playwright/test";
test("panel académico: escuelas autorizadas, consulta compartida y acceso al plan conservado", async ({ browser }) => {
  for (const user of ["e2e_school_admin", "e2e_health_director", "e2e_dental_director"]) {
    const context = await browser.newContext();const page = await context.newPage();
    await page.goto("/personal");
    await page.getByLabel("Usuario", {exact:true}).fill(user);
    await page.getByLabel("Contraseña", {exact:true}).fill(process.env.E2E_PASSWORD!);
    await page.getByRole("button", {name:"Ingresar",exact:true}).click();
    await expect(page.getByRole("heading", {name:"Panel académico",exact:true})).toBeVisible();
    const dental = page.getByRole("article", {name:"Escuela de Odontología de prueba",exact:true});
    await expect(dental).toBeVisible();
    if(user==="e2e_school_admin") await page.screenshot({path:"../docs/capturas/panel-academico-ensayo-0.35.4.png",fullPage:true});
    if(user==="e2e_dental_director") await expect(page.getByRole("article",{name:"Escuela de Salud de prueba",exact:true})).toHaveCount(0);
    if(user==="e2e_health_director") {
      await expect(dental).toContainText("Sin permiso para modificar registros");
      await dental.getByRole("link", {name:/Consultar escuela/}).click();
      await expect(page.getByText("Consulta académica autorizada · Sin permiso para modificar registros",{exact:true})).toBeVisible();
    } else {
      await dental.getByRole("link", {name:/Abrir escuela/}).click();
      await expect(page.getByRole("heading", {name:"Administración de Escuela de Odontología de prueba",exact:true})).toBeVisible();
    }
    await page.goto("/personal");
    await page.getByRole("link", {name:"Prácticas académicas",exact:true}).click();
    await expect(page.getByRole("button",{name:"Prácticas y avance",exact:true})).toBeVisible();
    await page.goto("/personal");
    await page.getByRole("link", {name:"Plan y cuestionarios",exact:true}).click();
    await expect(page.getByRole("heading", {name:"Mi trabajo de hoy",exact:true})).toBeVisible();
    await page.goto("/personal");await page.setViewportSize({width:390,height:844});
    await expect(page.getByRole("heading",{name:"Panel académico",exact:true})).toBeVisible();
    expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)).toBe(true);
    await context.close();
  }
});
