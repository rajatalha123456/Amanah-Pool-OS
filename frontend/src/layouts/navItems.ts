import type { NavItem } from "../types"

export const navItems: (NavItem & { labelKey: string })[] = [
  { label: "Command Center", labelKey: "nav.commandCenter", path: "/" },
  { label: "Products & Pools", labelKey: "nav.productsPools", path: "/products-pools" },
  { label: "Daily Operations", labelKey: "nav.dailyOperations", path: "/daily-operations" },
  { label: "Allocation Engine", labelKey: "nav.allocationEngine", path: "/allocation-engine" },
  { label: "Investments", labelKey: "nav.investments", path: "/investments" },
  { label: "Community Circles", labelKey: "nav.communityCircles", path: "/community-circles" },
  { label: "Shariah Governance", labelKey: "nav.shariahGovernance", path: "/shariah-governance" },
  { label: "Risk & Compliance", labelKey: "nav.riskCompliance", path: "/risk-compliance" },
  { label: "Finance & Ledger", labelKey: "nav.financeLedger", path: "/finance-ledger" },
  { label: "AI & Analytics", labelKey: "nav.aiAnalytics", path: "/ai-analytics" },
  { label: "Reports", labelKey: "nav.reports", path: "/reports" },
  { label: "Administration", labelKey: "nav.administration", path: "/administration" },
]
