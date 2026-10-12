import { expect, type Page } from "@playwright/test"

export const PASSWORD = "Amanah@2026!"

export async function login(page: Page, role: string) {
  await page.goto("/login")
  await page.locator('input[type="email"]').fill(role.includes("@") ? role : `${role}@novulabsdemo.test`)
  await page.locator('input[type="password"]').fill(PASSWORD)
  await page.locator('button[type="submit"]').click()
  await expect(page).not.toHaveURL(/login/)
}
