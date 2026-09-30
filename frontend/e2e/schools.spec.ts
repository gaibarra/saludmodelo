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
test("escuelas independientes: administración dental, consulta de Salud y revocación", async ({
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
  await health
    .getByRole("button", { name: /Escuela de Odontología de prueba/ })
    .click();
  await expect(
    health.getByText(
      "Consulta académica autorizada · Sin permiso para modificar registros",
      { exact: true },
    ),
  ).toBeVisible();
  await expect(
    health.getByRole("heading", {
      name: /Administración de Escuela de Odontología/,
    }),
  ).toHaveCount(0);
  await expect(
    health.getByText("Validadas: 1 participaciones · 1.5 horas", {
      exact: true,
    }),
  ).toBeVisible();
  await health
    .getByRole("link", { name: "Consultar prácticas de esta escuela" })
    .click();
  await expect(health.getByLabel("Escuela", { exact: true })).toHaveValue(
    /\d+/,
  );
  await expect(
    health.getByText("Práctica dental supervisada de prueba", { exact: true }),
  ).toBeVisible();
  await health.goto("/academico/evaluaciones");
  await health
    .getByLabel("Ciclo académico", { exact: true })
    .selectOption({
      label: "Escuela de Odontología de prueba · Ciclo dental de prueba",
    });
  await health
    .getByRole("button", { name: "Informes de cierre", exact: true })
    .click();
  await health
    .getByRole("link", { name: /Abrir informe/ })
    .first()
    .click();
  await expect(
    health.getByText("Bitácora sintética dental", { exact: false }).first(),
  ).toBeVisible();
  await expect(
    health.getByRole("button", { name: /Cerrar ciclo/ }),
  ).toHaveCount(0);
  const reportUrl = health.url();
  await health.setViewportSize({ width: 390, height: 844 });
  expect(
    await health.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth + 1,
    ),
  ).toBeTruthy();
  await dental.goto("/escuelas");
  const revoke = dental
    .locator("form")
    .filter({
      has: dental.getByRole("button", {
        name: "Revocar consulta",
        exact: true,
      }),
    });
  await revoke
    .getByLabel("Motivo de revocación")
    .fill("Finalizó la consulta de prueba");
  await revoke
    .getByRole("button", { name: "Revocar consulta", exact: true })
    .click();
  await expect(dental.getByText(/Revocada/)).toBeVisible();
  await health.goto(reportUrl);
  await expect(health.getByRole("alert")).toBeVisible();
  await dentalContext.close();
  await healthContext.close();
});
