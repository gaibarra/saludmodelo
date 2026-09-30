import { test, expect } from "@playwright/test";

test("portada pública: seis servicios y sesión pendiente de MFA separada", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { name: "Tu bienestar tiene un lugar aquí." })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Servicios de salud", exact: true }).getByRole("link")).toHaveCount(6);
  await page.getByRole("navigation", { name: "Servicios de salud", exact: true }).getByRole("link", { name: "Odontología", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Odontología", exact: true })).toBeVisible();
  await expect(page.getByRole("navigation", { name: "Servicios de salud", exact: true }).getByRole("link")).toHaveCount(6);
  await page.getByRole("navigation", { name: "Portal público", exact: true }).getByRole("link", { name: "Acceso del personal" }).click();
  await expect(page.getByRole("heading", { name: "Tu trabajo, conectado con la formación." })).toBeVisible();
  await expect(page.getByLabel("Escuelas independientes")).toContainText("Escuela de Salud");
  await expect(page.getByLabel("Escuelas independientes")).toContainText("Escuela de Odontología");
  await page.screenshot({path:"../docs/capturas/personal-acceso-0.35.2.png",fullPage:true});
  await page.getByLabel("Usuario", { exact: true }).fill("e2e_recovery_target");
  await page.getByLabel("Contraseña", { exact: true }).fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Verificación en dos pasos", exact: true })).toBeVisible();
  await page.screenshot({path:"../docs/capturas/personal-verificacion-0.35.2.png",fullPage:true});
  // A retained, partially authenticated session must not replace the public cover.
  await page.getByRole("link", { name: "← Portal de servicios", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Tu bienestar tiene un lugar aquí." })).toBeVisible();
  await expect(page.getByLabel("Código de verificación o recuperación", { exact: true })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Tu bienestar tiene un lugar aquí." })).toBeVisible();
  await page.getByRole("navigation", { name: "Portal público", exact: true }).getByRole("link", { name: "Acceso del personal" }).click();
  await expect(page.getByRole("heading", { name: "Verificación en dos pasos", exact: true })).toBeVisible();
  // Returning to the public page never bypasses the protected API gate.
  expect((await page.request.get("/api/v1/schools/")).status()).toBe(403);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  await expect(page.getByRole("navigation", { name: "Portal público", exact: true }).getByRole("link", { name: "Acceso del personal" })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.goto("/personal");
  await expect(page.getByRole("heading", { name: "Verificación en dos pasos", exact: true })).toBeVisible();
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await page.getByRole("button", { name: "Cerrar sesión", exact: true }).click();
  await expect(page).toHaveURL(/\/personal$/);
  await expect(page.getByRole("button", { name: "Ingresar", exact: true })).toBeVisible();
  await page.goto("/portal");
  await expect(page.getByRole("heading", { name: "Tu bienestar tiene un lugar aquí." })).toBeVisible();
});
