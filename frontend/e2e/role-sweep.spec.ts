import { expect, test } from "@playwright/test"
import { login } from "./helpers"

/**
 * Every screen a role can open must load without a refused API call. If the menu shows a screen to a role, the API
 * behind it must allow that role to read what the screen needs (or the screen must not ask for it).
 */
const ROLES = [
  "superadmin", "poolmanager", "maker", "checker", "risk", "secretariat", "board", "auditor", "pm", "signatory",
] as const

for (const role of ROLES) {
  test.setTimeout(300_000)
  test(`role sweep: ${role} opens every screen in its menu without refused calls`, async ({ page }) => {
    const refused: string[] = []
    page.on("response", (res) => {
      const url = res.url()
      if (url.includes("/api/v1/") && [401, 403].includes(res.status()) && !url.includes("/auth/")) {
        refused.push(`${res.status()} ${res.request().method()} ${url.split("/api/v1/")[1]}`)
      }
    })

    await login(page, role)
    await page.waitForTimeout(800)
    const links = await page.locator("aside nav a").evaluateAll((as) => as.map((a) => (a as HTMLAnchorElement).getAttribute("href") ?? ""))
    expect(links.length).toBeGreaterThan(0)

    for (const href of links) {
      await page.goto(href)
      await page.waitForTimeout(1200)
      // Open each tab of the screen too: tabs load their own data.
      const tabs = page.locator("main button").filter({ hasText: /./ })
      const labels = await page.locator("main div.flex.gap-6.border-b button, main div.flex.gap-4.border-b button").allInnerTexts()
      for (const label of labels) {
        const tab = page.locator("main button", { hasText: label.trim() }).first()
        if (await tab.count()) {
          await tab.click().catch(() => undefined)
          await page.waitForTimeout(900)
        }
      }
      void tabs
    }
    expect(refused, `refused calls for ${role}:\n${[...new Set(refused)].join("\n")}`).toEqual([])
  })
}
