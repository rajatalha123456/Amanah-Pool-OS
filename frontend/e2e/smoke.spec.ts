import { expect, test } from "@playwright/test"
import { login } from "./helpers"

// Text that used to be hard-coded on screen and must never come back.
const FABRICATED = ["18.42", "8.70B", "5.58B", "11.82%", "14.10%", "SBD-2026-044", "FATWA-2025-01", "Moneeb", "Qaradawi"]

async function expectNoFabricatedFigures(page: import("@playwright/test").Page) {
  const body = await page.locator("body").innerText()
  for (const text of FABRICATED) expect(body, `"${text}" should not be shown`).not.toContain(text)
}

test("finance maker sees real dashboards without invented figures", async ({ page }) => {
  await login(page, "maker")
  await expect(page.getByText("Executive Command Center")).toBeVisible()
  await expectNoFabricatedFigures(page)

  await page.goto("/investments")
  await expect(page.getByText("TOTAL MANAGED FUNDS")).toBeVisible()
  await expect(page.getByText("LAST SIGNED PROFIT (ALL POOLS)")).toBeVisible()
  await expect(page.getByText("POOL OVERVIEW")).toBeVisible()
  await expectNoFabricatedFigures(page)
})

test("investment onboarding spec comes from recorded terms", async ({ page }) => {
  await login(page, "maker")
  await page.goto("/investments")
  await page.getByRole("button", { name: "Investor Onboarding" }).click()
  await expect(page.getByText("Shown from the pool's recorded configuration")).toBeVisible()
  await expect(page.getByText("AI CONFIGURATION CHECK")).toHaveCount(0)
  await page.getByRole("button", { name: /Contract/ }).first().click()
  await expect(page.getByText("Contract type")).toBeVisible()
  await expectNoFabricatedFigures(page)
})

test("community circle tabs render real data", async ({ page }) => {
  await login(page, "poolmanager")
  await page.goto("/community-circles")
  await expect(page.getByText("Community Circle Setup")).toBeVisible()
  await page.getByRole("button", { name: "Contribution Calendar" }).click()
  await expect(page.getByText("Contribution ledger by cycle")).toBeVisible()
  await page.getByRole("button", { name: "Rules, Draw & Closure" }).click()
  await expect(page.getByText("Circle rules & member acceptance")).toBeVisible()
  await expectNoFabricatedFigures(page)
})

test("investor only gets the self-service portal", async ({ page }) => {
  await login(page, "investor")
  await expect(page.getByText("My investment accounts")).toBeVisible()
  const nav = page.locator("aside")
  await expect(nav.getByText("My Portal")).toBeVisible()
  await expect(nav.getByText("Participants")).toHaveCount(0)
  await page.goto("/pools")
  await expect(page).toHaveURL(/localhost:5173\/$/)
})

test("governance config shows the maker-checker queue", async ({ page }) => {
  await login(page, "checker")
  await page.goto("/governance-config")
  await expect(page.getByText("Changes awaiting approval")).toBeVisible()
  await expect(page.getByText("Approval matrix").first()).toBeVisible()
})

test("auditor builds a period report and verifies the audit chain", async ({ page }) => {
  await login(page, "auditor")
  await page.goto("/reports")
  await page.getByRole("button", { name: /Period Report/ }).click()
  await page.locator('input[type="date"]').first().fill("2026-07-01")
  await page.locator('input[type="date"]').nth(1).fill("2026-09-30")
  await page.getByRole("button", { name: "Build report" }).click()
  await expect(page.getByText(/content hash [0-9a-f]{64}/)).toBeVisible()
  await expect(page.getByText("not a regulatory filing")).toBeVisible()
})

test("period close gates are display-only", async ({ page }) => {
  await login(page, "poolmanager")
  await page.goto("/period-close")
  await expect(page.getByText(/Period Close/i).first()).toBeVisible()
  await expect(page.locator('input[type="checkbox"]')).toHaveCount(0)
})

test("investor with a capital account sees it and its acknowledged disclosure", async ({ page }) => {
  await login(page, "mudarabah.investor@novulabsdemo.test")
  await expect(page.getByText("My investment accounts")).toBeVisible()
  await expect(page.getByText("INV-INDUS-003")).toBeVisible()
  await expect(page.getByText("acknowledged")).toBeVisible()
  await expect(page.getByText("No investment accounts are linked")).toHaveCount(0)
})

test("a bank pool's yield is plausible, not an artefact of seed data", async ({ page }) => {
  await login(page, "maker")
  await page.goto("/investments")
  const row = page.locator("tr", { hasText: "POOL-GEN-01" })
  await expect(row).toContainText("% p.a.")
  const text = await row.innerText()
  const yieldPct = Number(/(\d+\.\d+)% p\.a\./.exec(text)?.[1])
  expect(yieldPct).toBeGreaterThan(0)
  expect(yieldPct).toBeLessThan(25)
})

test("a finance maker can open governance config without a permission error", async ({ page }) => {
  await login(page, "maker")
  await page.goto("/governance-config")
  await expect(page.getByText("Changes awaiting approval")).toBeVisible()
  await expect(page.getByText("You do not have permission")).toHaveCount(0)
})

test("period close shows server-computed gates and the locked August record", async ({ page }) => {
  await login(page, "poolmanager")
  await page.goto("/period-close")
  await expect(page.locator('[title*="Computed by the server"]').first()).toBeAttached()
  await expect(page.getByText("SBP Statutory Seal")).toHaveCount(0)
  await expect(page.getByText("FATWA-2026-M09-001")).toHaveCount(0)
})

test("dashboards do not contradict themselves on open exceptions", async ({ page }) => {
  await login(page, "board")
  await page.goto("/shariah-governance")
  await expect(page.getByText("OPEN EXCEPTIONS")).toBeVisible()
  const open = Number((await page.locator("text=OPEN EXCEPTIONS").locator("xpath=following-sibling::*[1]").first().innerText()).trim())
  const delta = await page.locator("text=OPEN EXCEPTIONS").locator("xpath=../*").allInnerTexts()
  if (open === 0) expect(delta.join(" ")).not.toMatch(/[1-9]\d* high/)
})
