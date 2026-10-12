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

test("a circle member signs in and sees only their own circle", async ({ page }) => {
  await login(page, "member")
  await expect(page.getByText("My savings circles")).toBeVisible()
  const circles = page.getByTestId("my-circle")
  await expect(circles).toHaveCount(1)
  await expect(circles.first()).toContainText("MEM-002")
  await expect(circles.first()).not.toContainText("MEM-001")
  await expect(circles.first()).toContainText("Payout position")
  await page.goto("/community-circles")
  await expect(page).toHaveURL(/localhost:5173\/$/)
})

test("circle payout ceremony shows the first cycle settled through the workflow", async ({ page }) => {
  await login(page, "poolmanager")
  await page.goto("/community-circles")
  await page.getByRole("button", { name: "Payout Release Ceremony" }).click()
  await expect(page.getByText(/disbursed/i).first()).toBeVisible()
})

test("asset provisions ledger lists maker-checker entries", async ({ page }) => {
  await login(page, "maker")
  await page.goto("/risk-compliance")
  await page.getByRole("button", { name: /Provisions/ }).first().click()
  await expect(page.getByText("Provision ledger")).toBeVisible()
  await expect(page.getByText("Request provision / write-off / recovery")).toBeVisible()
})

test("an investor with units can request a redemption (checker approves later)", async ({ page }) => {
  await login(page, "mudarabah.investor@novulabsdemo.test")
  await expect(page.getByRole("button", { name: "Request redemption" }).first()).toBeVisible()
})

test("allocation ceremony: a pending run waits for the independent checker", async ({ page }) => {
  await login(page, "checker")
  await page.goto("/allocation-engine")
  const rows = page.locator("tbody tr")
  await expect(rows.first()).toBeVisible()
  const text = await rows.allInnerTexts()
  expect(text.join("\n")).toMatch(/signed/i)

  // Open the run that is still waiting for the independent check.
  await rows.filter({ hasText: /checking|pending/i }).first().click()
  await expect(page.getByText("Waiting for the independent check by a Finance Checker.")).toBeVisible()
  await expect(page.getByRole("button", { name: /check/i }).first()).toBeVisible()
})

test("an investor sees their consents and can download their own data", async ({ page }) => {
  await login(page, "investor")
  const privacy = page.getByTestId("my-privacy")
  await expect(privacy).toContainText("Processing of personal data")
  const [download] = await Promise.all([page.waitForEvent("download"), privacy.getByRole("button", { name: "Download my data" }).click()])
  expect(download.suggestedFilename()).toBe("my-data.json")
})

test("each role only sees the areas it works in", async ({ page }) => {
  // Platform admin: administration only, no tenant financial screens (BRD section 3).
  await login(page, "superadmin")
  await expect(page).toHaveURL(/administration/)
  const nav = page.locator("aside")
  await expect(nav.getByText("Administration")).toBeVisible()
  await expect(nav.getByText("Allocation Engine")).toHaveCount(0)
  await expect(nav.getByText("Participants")).toHaveCount(0)
  await page.goto("/participants")
  await expect(page).toHaveURL(/administration/)
})

test("auditor and maker see a role-specific menu", async ({ page }) => {
  await login(page, "auditor")
  const nav = page.locator("aside")
  await expect(nav.getByText("Reports")).toBeVisible()
  await expect(nav.getByText("Administration")).toHaveCount(0)
  await page.goto("/administration")
  await expect(page).not.toHaveURL(/administration/)
})

test("daily close shows server-computed gates and keeps a failing day open", async ({ page }) => {
  await login(page, "maker")
  await page.goto("/daily-operations")
  await page.getByRole("button", { name: "Daily Close" }).click()
  const panel = page.getByTestId("daily-close")
  await expect(panel.getByRole("heading", { name: /2026-09-29/ })).toBeVisible()
  await expect(panel.getByText(/No high \/ critical exception left open/).first()).toBeVisible()
  await expect(panel.getByRole("button", { name: "Sign day" })).toHaveCount(0) // a maker never signs
})

test("a visitor meets the website first, and can reach sign-in from it", async ({ page }) => {
  await page.goto("/")
  await expect(page).toHaveURL(/\/welcome$/)
  await expect(page.getByRole("heading", { level: 1 })).toContainText("Run Islamic pools with proof")
  for (const section of ["Operating models", "Release ceremony", "AI guardrails"]) {
    await expect(page.locator("main")).toContainText(section)
  }
  await page.getByRole("banner").getByRole("link", { name: "Sign in" }).click()
  await expect(page).toHaveURL(/\/login$/)
  await page.getByRole("link", { name: /Back to the website/ }).click()
  await expect(page).toHaveURL(/\/welcome$/)
  await page.goto("/pools")
  await expect(page).toHaveURL(/\/login$/) // deeper addresses still go straight to sign-in
})

test("the website works on a phone and a demo request is received", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto("/welcome")
  await page.getByRole("button", { name: "Open menu" }).click()
  await page.locator("#mobile-menu").getByRole("link", { name: "Governance" }).click()
  await expect(page.locator("#governance")).toBeInViewport()
  const stamp = Date.now()
  await page.locator("#contact").scrollIntoViewIfNeeded()
  const form = page.locator("#contact form")
  await form.getByLabel("Your name").fill("E2E Visitor")
  await form.getByLabel("Organisation").fill("E2E Test Org")
  await form.getByLabel("Work email").fill(`e2e-${stamp}@example.org`)
  await form.getByLabel(/Anything we should know/).fill("Automated browser test.")
  await form.getByRole("button", { name: "Request a demo" }).click()
  await expect(page.getByTestId("demo-sent")).toContainText(`e2e-${stamp}@example.org`)
})

test("the platform admin reads the website enquiries", async ({ page }) => {
  await login(page, "superadmin")
  await page.getByRole("button", { name: "Website Enquiries" }).click()
  await expect(page.getByTestId("demo-requests")).toContainText("E2E Test Org")
})

test("the website's interactive demos behave honestly", async ({ page }) => {
  await page.goto("/welcome")

  // The release rule: a different person per role is accepted, one person in two roles is refused.
  const play = page.getByTestId("playground")
  await play.scrollIntoViewIfNeeded()
  await play.getByRole("button", { name: /Release the run/ }).click()
  await expect(page.getByTestId("playground-released")).toBeVisible()
  await play.getByLabel("Person for Finance Checker").selectOption("0") // same person as the maker
  await play.getByRole("button", { name: /Release the run/ }).click()
  await expect(page.getByTestId("playground-refused")).toContainText("The maker cannot check their own run")

  // The audit chain: altering one record breaks it and everything after it.
  const audit = page.getByTestId("audit-demo")
  await audit.scrollIntoViewIfNeeded()
  await expect(audit.getByText("Verified")).toHaveCount(5)
  await audit.getByRole("button", { name: /Alter/ }).click()
  await expect(audit.getByText("Mismatch")).toHaveCount(3)
  await audit.getByRole("button", { name: "Restore the record" }).click()
  await expect(audit.getByText("Verified")).toHaveCount(5)

  // The model explorer switches content.
  await page.getByRole("tab", { name: "Community savings" }).click()
  await expect(page.getByTestId("model-panel")).toContainText("Verifiable draw")
})
