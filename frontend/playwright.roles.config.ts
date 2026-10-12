import { defineConfig } from "@playwright/test"
import base from "./playwright.config"

/** The role sweep: every role opens every screen and tab in its menu; no API call may be refused. (~12 minutes) */
export default defineConfig({ ...base, testIgnore: [], testMatch: ["**/role-sweep.spec.ts"] })
