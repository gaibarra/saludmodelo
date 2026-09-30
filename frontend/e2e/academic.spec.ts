import { test, expect, Page } from "@playwright/test";
const password = process.env.E2E_PASSWORD!;
async function login(page: Page, user: string) {
  await page.goto("/personal");
  await page.getByLabel("Usuario", { exact: true }).fill(user);
  await page.getByLabel("Contraseña", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Panel académico" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Prácticas académicas", exact: true })
    .click();
  await expect(
    page.getByRole("button", { name: "Prácticas y avance" }),
  ).toBeVisible();
}
async function logout(page: Page) {
  await page.goto("/personal");
  await page.getByRole("button", { name: /Cerrar sesión/ }).click();
  await expect(
    page.getByRole("button", { name: "Ingresar", exact: true }),
  ).toBeVisible();
}
test("núcleo académico: Dirección asigna, alumna registra, supervisor devuelve y valida con historial", async ({
  page,
}) => {
  page.setDefaultTimeout(15000);
  await login(page, "e2e_academic_director");
  await page
    .getByRole("button", { name: "Configurar núcleo académico" })
    .click();
  const cycle = page.locator("form").filter({
    has: page.getByRole("heading", { name: "Nuevo ciclo", exact: true }),
  });
  await cycle.getByLabel("Código del ciclo").fill("PILOTO-2026");
  await cycle.getByLabel("Nombre del ciclo").fill("Ciclo académico sintético");
  await cycle.getByLabel("Inicio del ciclo").fill(process.env.E2E_START!);
  await cycle.getByLabel("Fin del ciclo").fill(process.env.E2E_END!);
  await cycle.getByRole("button", { name: "Crear ciclo" }).click();
  await expect(page.getByText("Registro académico guardado.")).toBeVisible();
  const student = page.locator("form").filter({
    has: page.getByRole("heading", { name: "Registrar alumno", exact: true }),
  });
  await student
    .getByLabel("Cuenta del alumno")
    .selectOption({ label: "Alumna sintética" });
  await student.getByLabel("Matrícula", { exact: true }).fill("A-2026-01");
  await student
    .getByLabel("Programa académico")
    .fill("Programa sintético de salud");
  await student
    .getByRole("button", { name: "Registrar alumno", exact: true })
    .click();
  await expect(
    page.getByText(
      "A-2026-01 · Alumna sintética · Programa sintético de salud",
      { exact: true },
    ),
  ).toBeVisible();
  const rotation = page.locator("form").filter({
    has: page.getByRole("heading", {
      name: "Asignar rotación y supervisor",
      exact: true,
    }),
  });
  for (const service of ["Odontología académica", "Nutrición académica"]) {
    await rotation
      .getByLabel("Alumno", { exact: true })
      .selectOption({ label: "A-2026-01 · Alumna sintética" });
    await rotation
      .getByLabel("Ciclo de la rotación")
      .selectOption({ label: "Ciclo académico sintético" });
    await rotation
      .getByLabel("Servicio de la rotación")
      .selectOption({ label: service + " · Sede académica" });
    await rotation
      .getByLabel("Supervisor", { exact: true })
      .selectOption({ label: "Supervisor sintético" });
    await rotation.getByLabel("Grupo", { exact: true }).fill("G-01");
    await rotation
      .getByLabel("Inicio de rotación")
      .fill(process.env.E2E_START!);
    await rotation.getByLabel("Fin de rotación").fill(process.env.E2E_END!);
    await rotation.getByLabel("Meta de minutos (opcional)").fill("600");
    await rotation
      .getByRole("button", { name: "Asignar rotación", exact: true })
      .click();
    await expect(rotation.getByLabel("Grupo", { exact: true })).toHaveValue("");
  }
  await logout(page);
  await login(page, "e2e_academic_student");
  await page
    .getByRole("button", { name: "Registrar práctica", exact: true })
    .click();
  await page.getByLabel("Mi rotación").selectOption({
    label:
      "Odontología académica · Ciclo académico sintético · Supervisor sintético",
  });
  await page
    .getByLabel("Actividad realizada")
    .fill("Orientación preventiva sintética");
  await page.getByLabel("Fecha de la práctica").fill(process.env.E2E_START!);
  await page.getByLabel("Duración de tu participación (minutos)").fill("60");
  await page
    .getByLabel("Competencia trabajada")
    .fill("Comunicación preventiva");
  await page
    .getByLabel("Referencia de evidencia", { exact: true })
    .fill("Bitácora sintética 001");
  await page.getByRole("button", { name: "Enviar al supervisor" }).click();
  await expect(page.getByRole("status")).toContainText(
    "Práctica enviada al supervisor",
  );
  await logout(page);
  await login(page, "e2e_academic_supervisor");
  let card = page.locator("article").filter({
    has: page.getByRole("heading", {
      name: "Orientación preventiva sintética",
    }),
  });
  await card.getByText("Revisar práctica", { exact: true }).click();
  await card.getByLabel("Decisión", { exact: true }).selectOption("return");
  await card
    .getByLabel("Observaciones del revisor")
    .fill("Precisar folio de la evidencia sintética.");
  await card.getByRole("button", { name: "Guardar revisión" }).click();
  await expect(card.getByText("Devuelta", { exact: true })).toBeVisible();
  await logout(page);
  await login(page, "e2e_academic_student");
  card = page.locator("article").filter({
    has: page.getByRole("heading", {
      name: "Orientación preventiva sintética",
    }),
  });
  await card
    .getByRole("button", { name: "Ver historial y observaciones" })
    .click();
  await expect(
    card.getByText("Precisar folio de la evidencia sintética."),
  ).toBeVisible();
  await card.getByText("Corregir y volver a enviar", { exact: true }).click();
  await card
    .getByLabel("Referencia de evidencia", { exact: true })
    .fill("Bitácora sintética 001, folio 3");
  await card
    .getByLabel("Qué corregiste")
    .fill("Se agregó el folio específico.");
  await card.getByRole("button", { name: "Enviar corrección" }).click();
  await expect(card.getByText("Por revisar", { exact: true })).toBeVisible();
  await logout(page);
  await login(page, "e2e_academic_supervisor");
  card = page.locator("article").filter({
    has: page.getByRole("heading", {
      name: "Orientación preventiva sintética",
    }),
  });
  await card.getByText("Revisar práctica", { exact: true }).click();
  await card
    .getByLabel("Observaciones del revisor")
    .fill("Participación y evidencia sintéticas revisadas.");
  await card.getByRole("button", { name: "Guardar revisión" }).click();
  await expect(card.getByText("Validada", { exact: true })).toBeVisible();
  await logout(page);
  await login(page, "e2e_academic_director");
  await expect(
    page
      .getByLabel("Resumen de participaciones")
      .getByText("1 h 0 min", { exact: true }),
  ).toBeVisible();
  await page
    .getByLabel("Servicio", { exact: true })
    .selectOption({ label: "Nutrición académica · Sede académica" });
  await expect(
    page.getByText("0 participaciones en esta selección."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Limpiar filtros" }).click();
  await expect(
    page.getByText("1 participaciones en esta selección."),
  ).toBeVisible();
  await page.screenshot({
    path: "test-results/academic-desktop.png",
    fullPage: true,
  });
  await page.setViewportSize({ width: 390, height: 844 });
  await expect(
    page.getByRole("heading", { name: "Prácticas de los alumnos" }),
  ).toBeVisible();
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBeTruthy();
  await page.screenshot({
    path: "test-results/academic-mobile.png",
    fullPage: true,
  });
});
