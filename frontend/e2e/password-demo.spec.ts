import { test, expect } from "@playwright/test";
test("demostración con contraseña: cuenta con autenticador previo entra sin segundo paso", async ({ page }) => {
  test.skip(process.env.MFA_DEMO_PASSWORD_ONLY !== "1", "Requires explicitly enabled demonstration mode");
  await page.goto("/personal");
  await expect(page.getByRole("status")).toContainText("Acceso con usuario y contraseña");
  await expect(page.getByLabel("Etapas de acceso")).toHaveCount(0);
  await page.getByLabel("Usuario", { exact: true }).fill("e2e_recovery_target");
  await page.getByLabel("Contraseña", { exact: true }).fill(process.env.E2E_PASSWORD!);
  await page.getByRole("button", { name: "Ingresar", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Panel académico", exact: true })).toBeVisible();
  await expect(page.getByRole("heading", { name: "Verificación en dos pasos", exact: true })).toHaveCount(0);
  await page.reload();
  await expect(page.getByRole("heading", { name: "Panel académico", exact: true })).toBeVisible();
  await page.getByRole("button", { name: /Cerrar sesión/ }).click();
  await expect(page.getByRole("button", { name: "Ingresar", exact: true })).toBeVisible();
});
