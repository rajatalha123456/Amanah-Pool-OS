import type { NavItem } from "../types"

/**
 * Which roles see which area (BRD section 3). This only decides what is *shown*; the API enforces the same rules
 * and refuses anything else, so a hidden screen cannot be reached by typing its address.
 * The Platform Super Admin sees administration only: it "cannot view tenant financial data by default".
 */
const OPERATIONS = ["pool_manager", "finance_maker", "finance_checker", "risk_compliance", "auditor"]
const GOVERNANCE = ["shariah_board", "shariah_secretariat"]
const ALL_TENANT_STAFF = [
  "product_manager", "pool_manager", "finance_maker", "finance_checker", "shariah_secretariat", "shariah_board",
  "risk_compliance", "authorized_signatory", "auditor",
]

export type RoleNavItem = NavItem & { labelKey: string; roles: string[]; also?: string[] }

export const navItems: RoleNavItem[] = [
  { label: "Command Center", labelKey: "nav.commandCenter", path: "/", roles: ALL_TENANT_STAFF },
  { label: "Products & Pools", labelKey: "nav.productsPools", path: "/products-pools", roles: ALL_TENANT_STAFF, also: ["/pools"] },
  { label: "Participants", labelKey: "nav.participants", path: "/participants", roles: [...OPERATIONS, "shariah_board"] },
  { label: "Daily Operations", labelKey: "nav.dailyOperations", path: "/daily-operations", roles: OPERATIONS },
  {
    label: "Allocation Engine", labelKey: "nav.allocationEngine", path: "/allocation-engine",
    also: ["/allocation-runs", "/allocation", "/allocation-simulator", "/hiba-simulator", "/mudarib-fee-optimization"],
    roles: [...OPERATIONS, ...GOVERNANCE, "authorized_signatory"],
  },
  { label: "Investments", labelKey: "nav.investments", path: "/investments", roles: [...OPERATIONS, "shariah_board", "authorized_signatory"] },
  {
    label: "Community Circles", labelKey: "nav.communityCircles", path: "/community-circles",
    also: ["/circles", "/draw-room", "/circle-draw", "/rotation-room", "/payout-ceremony", "/payout-release", "/ceremony", "/circle-payout"],
    roles: [...OPERATIONS, ...GOVERNANCE],
  },
  {
    label: "Shariah Governance", labelKey: "nav.shariahGovernance", path: "/shariah-governance",
    roles: [...GOVERNANCE, "risk_compliance", "auditor", "pool_manager", "product_manager", "authorized_signatory"],
  },
  { label: "Risk & Compliance", labelKey: "nav.riskCompliance", path: "/risk-compliance", roles: OPERATIONS },
  {
    label: "Finance & Ledger", labelKey: "nav.financeLedger", path: "/finance-ledger",
    roles: ["finance_maker", "finance_checker", "authorized_signatory", "risk_compliance", "auditor", "pool_manager"],
  },
  {
    label: "AI & Analytics", labelKey: "nav.aiAnalytics", path: "/ai-analytics",
    roles: [...GOVERNANCE, "product_manager", "risk_compliance"],
  },
  {
    label: "Reports", labelKey: "nav.reports", path: "/reports",
    roles: ["auditor", "risk_compliance", "pool_manager", "finance_checker", "shariah_board", "authorized_signatory"],
  },
  {
    label: "Governance Config", labelKey: "nav.governanceConfig", path: "/governance-config",
    roles: ["platform_super_admin", "risk_compliance", "finance_maker", "finance_checker", "authorized_signatory", "pool_manager", "auditor"],
  },
  { label: "Administration", labelKey: "nav.administration", path: "/administration", roles: ["platform_super_admin"] },
]

export function navItemsFor(role: string | undefined) {
  return navItems.filter((item) => !role || item.roles.includes(role))
}

/** The first screen a role should land on. */
export function homePathFor(role: string | undefined) {
  return role === "platform_super_admin" ? "/administration" : "/"
}

/** False when the role has no business on this screen (the API would refuse it anyway). */
export function roleMayOpen(role: string | undefined, pathname: string) {
  if (!role) return true
  for (const item of navItems) {
    const paths = [item.path, ...(item.also ?? [])].filter((p) => p !== "/")
    if (paths.some((p) => pathname === p || pathname.startsWith(p + "/"))) return item.roles.includes(role)
  }
  return true
}
