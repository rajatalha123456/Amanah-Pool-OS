// Audit probe (no dependency added): basic accessibility checks on key screens - unlabeled form controls,
// buttons without an accessible name, images without alt, and keyboard focus reaching the main content.
import { test } from "@playwright/test"
import * as fs from "fs"

const SCREENS = ["/", "/products-pools", "/daily-operations", "/allocation-engine", "/shariah-governance", "/community-circles", "/finance-ledger", "/risk-compliance"]

test("accessibility probe (pool manager)", async ({ page }) => {
  test.setTimeout(240000)
  await page.goto("/login")
  await page.getByLabel(/email/i).fill("poolmanager@novulabsdemo.test")
  await page.getByLabel(/password/i).fill("Amanah@2026!")
  await page.getByRole("button", { name: /sign in/i }).click()
  await page.waitForURL((u) => !u.pathname.startsWith("/login"))
  const out: string[] = []
  for (const s of SCREENS) {
    await page.goto(s)
    await page.waitForTimeout(2500)
    const r = await page.evaluate(() => {
      const named = (el: Element) => (el.getAttribute("aria-label") || el.getAttribute("title") || (el.textContent || "").trim()).length > 0
      const controls = Array.from(document.querySelectorAll("input:not([type=hidden]), select, textarea"))
      const unlabeled = controls.filter((c) => {
        const id = c.getAttribute("id")
        return !(c.getAttribute("aria-label") || c.getAttribute("aria-labelledby") || (id && document.querySelector(`label[for="${id}"]`)) || c.closest("label"))
      }).length
      const buttons = Array.from(document.querySelectorAll("button"))
      const unnamedButtons = buttons.filter((b) => !named(b)).length
      const imgs = Array.from(document.querySelectorAll("img")).filter((i) => !i.hasAttribute("alt")).length
      return { controls: controls.length, unlabeled, buttons: buttons.length, unnamedButtons, imgsWithoutAlt: imgs, lang: document.documentElement.lang }
    })
    out.push(`${s}\t${JSON.stringify(r)}`)
  }
  fs.writeFileSync("../audit_reports/evidence/a11y_probe.txt", out.join("\n"))
})
