import { defineConfig } from "@playwright/test";
const baseURL = process.env.SIDE_A_URL || "http://127.0.0.1:4216/";
export default defineConfig({
  testDir: "./tests",
  testMatch: "**/*.e2e.ts",
  timeout: 45000,
  workers: 1,
  use: {
    baseURL,
    headless: true,
    // Trace snapshots can perturb the real media clock on this host. Opt in for diagnosis.
    trace: process.env.SIDE_A_TRACE ? "retain-on-failure" : "off",
    screenshot: "only-on-failure",
  },
  projects: [
    { name: "wide", use: { viewport: { width: 1440, height: 1000 } } },
    {
      name: "narrow",
      use: { viewport: { width: 390, height: 844 }, hasTouch: true },
    },
  ],
  webServer: process.env.SIDE_A_URL
    ? undefined
    : { command: "npm run dev", url: baseURL, reuseExistingServer: true },
});
