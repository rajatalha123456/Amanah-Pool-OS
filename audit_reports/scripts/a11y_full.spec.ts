// Audit probe (no dependency added): every menu screen and tab of eight roles; lists form controls with no accessible name.
// Copy into frontend/e2e/ to run, delete afterwards.
import { test } from "@playwright/test"
import * as fs from "fs"
import { login } from "./helpers"

const ROLES = ["poolmanager", "maker", "checker", "risk", "board", "auditor", "signatory", "investor"] as const

test("a11y probe", async ({ page }) => {
  test.setTimeout(900000)
  const out: string[] = []
  for (const role of ROLES) {
    await login(page, role)
    await page.waitForTimeout(600)
    const links = await page.locator("aside nav a").evaluateAll((as) => as.map((a) => (a as HTMLAnchorElement).getAttribute("href") ?? ""))
    for (const href of links.length ? links : ["/"]) {
      await page.goto(href)
      await page.waitForTimeout(1500)
      const tabs = await page.locator("main div.flex.gap-6.border-b button, main div.flex.gap-4.border-b button").allInnerTexts()
      for (const label of ["", ...tabs]) {
        if (/download|export|generate|simulate|run |submit|approve|sign|certify|lock/i.test(label)) continue
        if (label) {
          const tab = page.locator("main button", { hasText: label.trim() }).first()
          if (await tab.count()) { await tab.click().catch(() => undefined); await page.waitForTimeout(700) }
        }
        const bad = await page.evaluate(() => {
          const res: string[] = []
          document.querySelectorAll("input:not([type=hidden]), select, textarea").forEach((c) => {
            const id = c.getAttribute("id")
            const ok = c.getAttribute("aria-label") || c.getAttribute("aria-labelledby") || (id && document.querySelector(`label[for="${id}"]`)) || c.closest("label")
            if (!ok) res.push(`${c.tagName.toLowerCase()}[${c.getAttribute("type") || ""}] ph="${c.getAttribute("placeholder") || ""}" cls="${(c.getAttribute("class") || "").slice(0, 40)}"`)
          })
          document.querySelectorAll("button, a[href]").forEach((b) => {
            const name = b.getAttribute("aria-label") || b.getAttribute("title") || (b.textContent || "").trim()
            if (!name) res.push(`button/link without a name: ${(b.outerHTML || "").slice(0, 100)}`)
          })
          return res
        })
        for (const b of bad) out.push(`${role}\t${href}\t${label || "-"}\t${b}`)
      }
    }
    await page.evaluate(() => localStorage.clear())
  }
  fs.writeFileSync("../audit_reports/evidence/a11y_full_after.txt", [...new Set(out)].join("\n"))
})
