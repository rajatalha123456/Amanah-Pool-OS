import { test } from "@playwright/test"
import { login } from "./helpers"

const SHOTS: Array<[string, string, string, string?]> = [
  ["maker", "/", "command"],
  ["maker", "/risk-compliance", "risk"],
  ["maker", "/governance-config", "govconfig"],
  ["poolmanager", "/period-close", "periodclose"],
  ["board", "/shariah-governance", "shariah"],
  ["maker", "/allocation-engine", "allocation"],
  ["maker", "/finance-ledger", "ledger"],
  ["maker", "/products-pools", "products"],
  ["maker", "/participants", "participants"],
  ["maker", "/daily-operations", "dailyops"],
  ["auditor", "/reports", "reports"],
  ["board", "/ai-analytics", "ai"],
  ["superadmin", "/administration", "admin"],
]

for (const [role, path, name] of SHOTS) {
  test(`shot ${name}`, async ({ page }) => {
    await page.setViewportSize({ width: 1400, height: 1000 })
    await login(page, role)
    await page.goto(path)
    await page.waitForTimeout(2500)
    await page.screenshot({ path: `shots/${name}.png` })
  })
}
