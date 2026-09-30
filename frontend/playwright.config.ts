import { defineConfig } from "@playwright/test";
if (!process.env.E2E_BASE_URL || !process.env.E2E_PASSWORD)
  throw new Error(
    "Use tests/run_browser.py; never point these tests at an existing application.",
  );
export default defineConfig({
  testDir: "./e2e",
  testMatch: "*.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 180000,
  use: {
    baseURL: process.env.E2E_BASE_URL,
    viewport: { width: 1280, height: 900 },
    trace: "retain-on-failure",
  },
  reporter: [
    ["list"],
    ["json", { outputFile: "test-results/browser-results.json" }],
  ],
});
