import { defineConfig } from "@playwright/test"

/**
 * End-to-end checks against the real backend + frontend. Start both first:
 *   backend:  python manage.py runserver 8000   (after migrate + seed_project_data)
 *   frontend: npm run dev
 * Then: npx playwright test
 */
export default defineConfig({
  testDir: "./e2e",
  timeout: 45_000,
  workers: 1,
  retries: 0,
  reporter: [["list"]],
  use: { baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173", trace: "retain-on-failure", screenshot: "only-on-failure" },
})
