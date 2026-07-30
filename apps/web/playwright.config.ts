import { defineConfig, devices } from "@playwright/test";

// The full 8-step journey assumes the API (seeded) and web app are already running:
//   docker compose up   (or: make dev)
// Set E2E_BASE_URL to override the web origin.
export default defineConfig({
  testDir: "./tests/e2e",
  timeout: 30_000,
  fullyParallel: false,
  retries: 0,
  reporter: "list",
  use: {
    baseURL: process.env.E2E_BASE_URL || "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
