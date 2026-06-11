import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://localhost:3002";

export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  reporter: [
    ["list"],
    ["html", { outputFolder: "playwright-report", open: "never" }],
  ],
  use: {
    baseURL,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
    video: "off",
    ignoreHTTPSErrors: true,
  },
  projects: [
    {
      name: "chrome-desktop",
      testIgnore: /public-mobile\.spec\.ts/,
      use: {
        ...devices["Desktop Chrome"],
        channel: "chrome",
      },
    },
    {
      name: "chrome-mobile-public",
      testMatch: /public-mobile\.spec\.ts/,
      use: {
        ...devices["Pixel 5"],
        channel: "chrome",
      },
    },
  ],
});
