import { test, expect, Page } from "@playwright/test";
async function login(page: Page, user: string) {
  await page.goto("/personal");
  await page.getByLabel("Usuario", { exact: true }).fill(user);
  await page
    .getByLabel("Contraseña", { exact: true })
    .fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Panel académico" }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Escuelas", exact: true }).click();
}
test("escuelas independientes: sin consulta cruzada", async ({
  browser,
}) => {
  const dentalContext = await browser.newContext(),
    healthContext = await browser.newContext();
  const dental = await dentalContext.newPage(),
    health = await healthContext.newPage();
  dental.setDefaultTimeout(15000);
  health.setDefaultTimeout(15000);
  await login(dental, "e2e_dental_director");
  await expect(
    dental.getByRole("heading", {
      name: "Administración de Escuela de Odontología de prueba",
    }),
  ).toBeVisible();
  await expect(
    dental.getByRole("button", { name: /Escuela de Salud de prueba/ }),
  ).toHaveCount(0);
  const form = dental
    .locator("form")
    .filter({
      has: dental.getByRole("heading", {
        name: "Registrar servicio",
        exact: true,
      }),
    });
  await form
    .getByLabel("Nombre del servicio")
    .fill("Clínica adicional escolar");
  await form
    .getByLabel("Sede", { exact: true })
    .selectOption({ label: "Sede escuelas" });
  await form
    .getByRole("button", { name: "Registrar servicio", exact: true })
    .click();
  await expect(
    dental
      .getByRole("listitem")
      .filter({ hasText: "Clínica adicional escolar" }),
  ).toBeVisible();
  await login(health, "e2e_health_director");
  await expect(health.getByRole("button", { name: /Escuela de Odontología de prueba/ })).toHaveCount(0);
  await expect(health.getByRole("heading", { name: "Administración de Escuela de Salud de prueba" })).toBeVisible();
  for (const page of [dental, health]) {
    await expect(page.getByRole("heading", { name: "Compartir información académica" })).toHaveCount(0);
    await page.goto("/academico");
  }
  await expect(health.getByText("Práctica dental supervisada de prueba", {exact:true})).toHaveCount(0);
  await dentalContext.close();
  await healthContext.close();
});
