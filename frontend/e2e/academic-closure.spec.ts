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
  await page.goto("/academico/evaluaciones");
  await expect(
    page.getByLabel("Ciclo académico", { exact: true }),
  ).toBeVisible();
}
async function logout(page: Page) {
  await page.goto("/personal");
  await page.getByRole("button", { name: /Cerrar sesión/ }).click();
  await expect(
    page.getByRole("button", { name: "Ingresar", exact: true }),
  ).toBeVisible();
}
test("cierre académico: rúbrica, evaluación, informes individuales y consolidado, cierre y reapertura", async ({
  page,
}) => {
  page.setDefaultTimeout(15000);
  await login(page, "e2e_closure_director");
  await page.getByRole("button", { name: "Rúbricas y competencias" }).click();
  await page.getByRole("button", { name: "Añadir competencia" }).click();
  await page
    .getByLabel("Servicio de la competencia", { exact: true })
    .selectOption({ label: "Odontología cierre · Sede cierre" });
  await page.getByLabel("Código de competencia").fill("COM-01");
  await page
    .getByLabel("Nombre de competencia")
    .fill("Comunicación con el paciente");
  await page
    .getByLabel("Criterio observable")
    .fill("Explica el procedimiento y verifica comprensión.");
  for (let i = 1; i <= 4; i++)
    await page
      .getByLabel(`Descripción del nivel ${i}`, { exact: true })
      .fill(`Descripción observable sintética del nivel ${i}.`);
  await page
    .getByLabel("Nivel mínimo requerido", { exact: true })
    .selectOption("2");
  await page
    .getByLabel("Motivo y referencia institucional")
    .fill("Criterio sintético autorizado para este ensayo.");
  await page.getByRole("button", { name: "Guardar rúbrica" }).click();
  await expect(
    page.getByRole("heading", {
      name: "COM-01 · Comunicación con el paciente",
    }),
  ).toBeVisible();
  await logout(page);
  await login(page, "e2e_closure_supervisor");
  await page
    .getByLabel("Rotación a evaluar", { exact: true })
    .selectOption({
      label: "CIERRE-1 · Alumna cierre uno · Odontología cierre",
    });
  await page.getByText("Evaluar competencia", { exact: true }).click();
  await page.getByLabel("Nivel observado", { exact: true }).selectOption("3");
  await page.getByRole("checkbox").check();
  await page
    .getByLabel("Justificación de la evaluación")
    .fill("La alumna explica y verifica comprensión según la evidencia.");
  await page.getByRole("button", { name: "Guardar evaluación" }).click();
  await expect(
    page.getByText("Nivel requerido alcanzado", { exact: true }),
  ).toBeVisible();
  await logout(page);
  await login(page, "e2e_closure_director");
  await page
    .getByRole("button", { name: "Informes de cierre", exact: true })
    .click();
  await page
    .getByRole("button", { name: "Generar versión del informe" })
    .click();
  await page.getByRole("link", { name: "Abrir informe 1" }).click();
  await expect(
    page.getByRole("heading", { name: "Informe consolidado de prácticas" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "CIERRE-2 · Alumna cierre dos" }),
  ).toBeVisible();
  await page
    .getByLabel("Contenido del informe", { exact: true })
    .selectOption({ label: "CIERRE-1 · Alumna cierre uno" });
  await expect(
    page.getByRole("heading", { name: "Informe individual de prácticas" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "CIERRE-2 · Alumna cierre dos" }),
  ).toHaveCount(0);
  await page.emulateMedia({ media: "print" });
  await page.pdf({
    path: "test-results/academic-individual-report.pdf",
    format: "A4",
    printBackground: true,
  });
  await page.emulateMedia({ media: "screen" });
  await page
    .getByLabel("Contenido del informe", { exact: true })
    .selectOption("");
  await page.getByRole("checkbox").check();
  await page
    .getByLabel("Motivo del cierre", { exact: true })
    .fill("Cierre documental sintético con pendientes explícitos.");
  await page
    .getByRole("button", { name: "Confirmar cierre del ciclo" })
    .click();
  await expect(page.getByRole("status")).toContainText("Ciclo cerrado.");
  const reportUrl = page.url();
  await page.screenshot({
    path: "test-results/academic-closure-report.png",
    fullPage: true,
  });
  await logout(page);
  await login(page, "e2e_closure_student");
  await page
    .getByRole("button", { name: "Informes de cierre", exact: true })
    .click();
  await page.getByRole("link", { name: "Abrir informe 1" }).click();
  await expect(
    page.getByRole("heading", { name: "Informe individual de prácticas" }),
  ).toBeVisible();
  await expect(
    page.getByText("Alumna cierre dos", { exact: false }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Confirmar cierre del ciclo" }),
  ).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await logout(page);
  await login(page, "e2e_closure_director");
  await page.goto(reportUrl);
  await page
    .getByText("Reabrir ciclo para corregir registros", { exact: true })
    .click();
  await page
    .getByLabel("Motivo de reapertura")
    .fill("Revisión posterior documentada para corregir registros.");
  await page
    .getByRole("button", { name: "Reabrir ciclo", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText("Ciclo reabierto.");
  await expect(
    page.getByText(
      "Cierre histórico; no representa un cierre vigente del ciclo.",
    ),
  ).toBeVisible();
});
