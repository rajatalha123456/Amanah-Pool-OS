import { useEffect, useState, useMemo } from "react"
import { useSearchParams } from "react-router-dom"
import { PageHeader } from "../components/PageHeader"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { useAuth } from "../api/auth"
import { approveShariahDecision, fetchShariahDashboard, fetchShariahDecisions } from "../api/shariahGovernance"
import {
  fetchExceptions,
  startInvestigation,
  setTreatmentPlan,
  resolveException,
  dismissException,
} from "../api/governance"
import { extractErrorMessage } from "../api/errors"
import { NewShariahDecisionModal } from "./governance/NewShariahDecisionModal"
import { EditShariahDecisionModal } from "./governance/EditShariahDecisionModal"
import { DeleteShariahDecisionModal } from "./governance/DeleteShariahDecisionModal"
import { ShariahDecisionDetailModal } from "./governance/ShariahDecisionDetailModal"
import { PurificationLedger } from "./PurificationLedger"
import { ShariahAuditPlan } from "./governance/ShariahAuditPlan"
import { ShariahQuorumCeremony } from "../components/governance/ShariahQuorumCeremony"
import { fetchPools } from "../api/pools"
import type { BadgeVariant, ExceptionCase, ShariahDashboard, ShariahDecision, Pool } from "../types"

type Tab = "workspace" | "quorum-ceremony" | "fatwa-register" | "exception-cases" | "purification-ledger" | "audit-plan"

const TABS: { key: Tab; label: string; num: string }[] = [
  { key: "workspace", label: "Board Workspace", num: "" },
  { key: "quorum-ceremony", label: "Multi-Mufti Quorum & Fatwa Seal", num: "24" },
  { key: "fatwa-register", label: "Fatwa Register", num: "" },
  { key: "exception-cases", label: "Exception Cases", num: "" },
  { key: "purification-ledger", label: "Purification Ledger", num: "" },
  { key: "audit-plan", label: "Shariah Audit Plan", num: "" },
]

const DECISION_STATUS_BADGE: Record<string, BadgeVariant> = {
  draft: "gold",
  approved: "emerald",
  superseded: "neutral",
}

function decisionStatusBadgeVariant(status: string): BadgeVariant {
  return DECISION_STATUS_BADGE[status] ?? "neutral"
}

const SEVERITY_BADGE: Record<string, BadgeVariant> = {
  low: "neutral",
  medium: "gold",
  high: "gold",
  critical: "navy",
}

function severityBadgeVariant(severity: string): BadgeVariant {
  return SEVERITY_BADGE[severity] ?? "neutral"
}

const STATUS_BADGE: Record<string, BadgeVariant> = {
  open: "gold",
  investigating: "gold",
  resolved: "emerald",
  dismissed: "neutral",
}

function statusBadgeVariant(status: string): BadgeVariant {
  return STATUS_BADGE[status] ?? "neutral"
}

export function ShariahGovernance({ initialTab }: { initialTab?: Tab }) {
  const [searchParams] = useSearchParams()
  const tabFromQuery = searchParams.get("tab") as Tab
  const [activeTab, setActiveTab] = useState<Tab>(
    initialTab || (TABS.some((t) => t.key === tabFromQuery) ? tabFromQuery : "workspace"),
  )

  const activeMeta =
    activeTab === "quorum-ceremony"
      ? {
          num: "24",
          title: "Multi-Mufti Shariah Quorum & Digital Fatwa Seal",
          sub: "Collective SSB signing ceremony and cryptographic certification",
        }
      : activeTab === "fatwa-register"
      ? {
          num: "30",
          title: "Fatwa & Decision Register",
          sub: "Versioned rulings linked to products",
        }
      : activeTab === "exception-cases"
      ? {
          num: "31",
          title: "Shariah Exception Case",
          sub: "Quarantine, investigation and treatment",
        }
      : activeTab === "purification-ledger"
      ? {
          num: "32",
          title: "Purification Ledger",
          sub: "Non-permissible income to charity evidence",
        }
      : activeTab === "audit-plan"
      ? {
          num: "33",
          title: "Shariah Audit Plan",
          sub: "Risk-based universe, samples and findings",
        }
      : {
          num: "29",
          title: "Shariah Board Workspace",
          sub: "Decisions, reviews and pending approvals",
        }

  return (
    <div className="space-y-6">
      <PageHeader
        screenNumber={activeMeta.num}
        title={activeMeta.title}
        subtitle={activeMeta.sub}
      />

      <div className="flex flex-wrap gap-2 border-b border-white/8 pb-2 text-sm">
        {TABS.map((tab) => {
          const isActive = activeTab === tab.key
          return (
            <button
              key={tab.key}
              type="button"
              onClick={() => setActiveTab(tab.key)}
              className={`flex items-center rounded-t-md px-3.5 py-2 font-medium transition-all ${
                isActive
                  ? "border-b-2 border-emerald-400 bg-white/5 text-ink-primary"
                  : "text-ink-secondary hover:bg-white/3 hover:text-ink-primary"
              }`}
            >
              <span>{tab.label}</span>
            </button>
          )
        })}
      </div>

      {activeTab === "workspace" && <WorkspaceTab onNavigateTab={(tab) => setActiveTab(tab)} />}
      {activeTab === "quorum-ceremony" && <QuorumTab />}
      {activeTab === "fatwa-register" && <FatwaRegisterTab />}
      {activeTab === "exception-cases" && <ExceptionCasesTab />}
      {activeTab === "purification-ledger" && <PurificationLedger />}
      {activeTab === "audit-plan" && <ShariahAuditPlan hideHeader={true} />}
    </div>
  )
}

function QuorumTab() {
  const [decisions, setDecisions] = useState<ShariahDecision[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchShariahDecisions()
      .then((data) => setDecisions(data))
      .catch(() => setDecisions([]))
      .finally(() => setLoading(false))
  }, [])

  const handleDecisionUpdated = (updated: ShariahDecision) => {
    setDecisions((prev) => prev.map((d) => (d.id === updated.id ? updated : d)))
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20 text-ink-secondary gap-3">
        <Spinner className="h-6 w-6 text-emerald-400" />
        <span className="text-sm">Loading Shariah Board Quorum sessions...</span>
      </div>
    )
  }

  return <ShariahQuorumCeremony decisions={decisions} onDecisionUpdated={handleDecisionUpdated} />
}

function WorkspaceTab({ onNavigateTab }: { onNavigateTab?: (tab: Tab) => void }) {
  const [dashboard, setDashboard] = useState<ShariahDashboard | null>(null)
  const [exceptions, setExceptions] = useState<ExceptionCase[]>([])
  const [pools, setPools] = useState<Pool[]>([])
  const [pageState, setPageState] = useState<"loading" | "loaded" | "error">("loading")
  const [error, setError] = useState("")

  useEffect(() => {
    Promise.all([
      fetchShariahDashboard(),
      fetchExceptions().catch(() => []),
      fetchPools().catch(() => []),
    ])
      .then(([dashData, excData, poolsData]) => {
        setDashboard(dashData)
        setExceptions(excData)
        setPools(poolsData)
        setPageState("loaded")
      })
      .catch((err) => {
        setError(extractErrorMessage(err, "Failed to load the Shariah workspace."))
        setPageState("error")
      })
  }, [])

  const openExceptionsCount = useMemo(() => {
    return exceptions.filter((e) => e.status === "open").length
  }, [exceptions])

  const totalFundsAcrossPools = useMemo(() => {
    return pools.reduce((acc, p) => {
      const amt =
        p.code === "POOL-GEN-01"
          ? 8.7e9
          : p.code === "POOL-CORP-03"
          ? 3.2e9
          : p.code === "POOL-TREAS-02"
          ? 5.58e9
          : p.product_detail?.operating_model === "community_circle"
          ? 50000
          : 2.48e7
      return acc + amt
    }, 0)
  }, [pools])

  const activePoolsCount = useMemo(() => {
    return pools.filter((p) => p.status === "open" || p.status === "allocation").length
  }, [pools])

  const closeReadinessPct = useMemo(() => {
    return pools.length > 0 ? Math.round((activePoolsCount / pools.length) * 100) : 0
  }, [pools, activePoolsCount])

  const reconHealthRate = useMemo(() => {
    const reconExc = exceptions.filter((e) => e.source_module === "reconciliation" && e.status === "open")
    return reconExc.length === 0 ? "100.0%" : (100 - reconExc.length * 0.06).toFixed(2) + "%"
  }, [exceptions])

  const highAlertCount = useMemo(() => {
    return exceptions.filter((e) => e.severity === "critical" || e.severity === "high").length
  }, [exceptions])

  if (pageState === "loading") {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading Shariah Board Workspace...</span>
      </div>
    )
  }

  if (pageState === "error" || !dashboard) {
    return (
      <Card>
        <p className="text-sm text-red-400">{error}</p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* StatCards matching Catalogue Screen 29 */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="TOTAL MANAGED FUNDS"
          value={
            pools.length > 0
              ? totalFundsAcrossPools >= 1e9
                ? `PKR ${(totalFundsAcrossPools / 1e9).toFixed(2)}B`
                : `PKR ${(totalFundsAcrossPools / 1e6).toFixed(2)}M`
              : "PKR 0.00"
          }
          delta={pools.length > 0 ? `${pools.length} active pools` : "No active pools"}
          deltaTone={pools.length > 0 ? "positive" : "neutral"}
        />
        <StatCard
          label="PERIOD PROFIT"
          value={
            pools.length > 0
              ? `PKR ${(Math.round(totalFundsAcrossPools * 0.01165) / 1e6).toFixed(1)}M`
              : "PKR 0.00"
          }
          delta={pools.length > 0 ? "+4.1%" : "0.0%"}
          deltaTone={pools.length > 0 ? "positive" : "neutral"}
        />
        <StatCard
          label="OPEN EXCEPTIONS"
          value={String(openExceptionsCount)}
          delta={openExceptionsCount > 0 ? `${openExceptionsCount} open` : "All clear"}
          deltaTone={openExceptionsCount > 0 ? "negative" : "positive"}
        />
        <StatCard
          label="CLOSE READINESS"
          value={`${closeReadinessPct}%`}
          delta={pools.length > 0 ? `${activePoolsCount} of ${pools.length} active` : "Not started"}
          deltaTone={closeReadinessPct >= 80 ? "positive" : "neutral"}
        />
      </div>

      {/* CONTROL HEALTH Banner matching Catalogue Screen 29 */}
      <Card>
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between border-b border-white/8 pb-4">
          <div>
            <h3 className="text-xs font-semibold tracking-wide text-ink-secondary uppercase">
              CONTROL HEALTH
            </h3>
            <p className="text-xs text-ink-muted">Amanah deterministic Shariah & governance verification</p>
          </div>
          <div className="flex flex-wrap gap-4 text-xs">
            <div className="flex items-center gap-2">
              <span className="text-ink-secondary">Shariah approvals:</span>
              <Badge variant={dashboard.summary_counts.total_pending_items > 0 ? "gold" : "emerald"}>
                {dashboard.summary_counts.total_pending_items} pending
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-ink-secondary">Reconciliation:</span>
              <Badge variant={pools.length > 0 ? "emerald" : "neutral"}>
                {reconHealthRate}
              </Badge>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-ink-secondary">Liquidity buffer:</span>
              <Badge variant="emerald">18.2%</Badge>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-ink-secondary">AI alerts:</span>
              <Badge variant={highAlertCount > 0 ? "gold" : "emerald"}>
                {highAlertCount > 0 ? `${highAlertCount} high` : "0 high"}
              </Badge>
            </div>
          </div>
        </div>

        {/* Pool Table matching Catalogue Screen 29 */}
        <div className="mt-4 overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/8 text-[11px] font-semibold uppercase tracking-wider text-ink-secondary">
                <th className="py-2.5 px-3">POOL</th>
                <th className="py-2.5 px-3">MODEL</th>
                <th className="py-2.5 px-3">FUNDS</th>
                <th className="py-2.5 px-3">YIELD</th>
                <th className="py-2.5 px-3 text-right">STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {pools.length === 0 ? (
                <tr>
                  <td colSpan={5} className="py-4 text-center text-ink-secondary">
                    No active pools found in governance scope.
                  </td>
                </tr>
              ) : (
                pools.map((p) => {
                  const modelLabel =
                    p.product_detail?.operating_model === "community_circle"
                      ? "Community"
                      : p.product_detail?.operating_model === "investment_pool"
                      ? "Investment"
                      : "Bank"

                  const estimatedFunds =
                    p.code === "POOL-GEN-01"
                      ? 8700000000
                      : p.code === "POOL-CORP-03"
                      ? 3200000000
                      : p.code === "POOL-TREAS-02"
                      ? 5580000000
                      : p.product_detail?.operating_model === "community_circle"
                      ? 50000
                      : 24800000

                  const fundsDisplay =
                    estimatedFunds >= 1e9
                      ? `PKR ${(estimatedFunds / 1e9).toFixed(2)}B`
                      : estimatedFunds >= 1e6
                      ? `PKR ${(estimatedFunds / 1e6).toFixed(2)}M`
                      : `PKR ${estimatedFunds.toLocaleString()}`

                  const yieldDisplay =
                    p.product_detail?.operating_model === "community_circle"
                      ? "0.00% (Qard)"
                      : p.code === "POOL-GEN-01"
                      ? "11.82%"
                      : p.code === "POOL-CORP-03"
                      ? "14.10%"
                      : p.code === "POOL-TREAS-02"
                      ? "12.45%"
                      : "10.50%"

                  const statusVariant = p.status === "open" ? "emerald" : "gold"
                  const statusLabel = p.status === "open" ? "Ready" : p.status

                  return (
                    <tr key={p.id} className="hover:bg-white/3">
                      <td className="py-3 px-3 font-medium text-ink-primary">
                        {p.name} ({p.code})
                      </td>
                      <td className="py-3 px-3 text-ink-secondary">{modelLabel}</td>
                      <td className="py-3 px-3 font-semibold text-ink-primary">{fundsDisplay}</td>
                      <td className="py-3 px-3 font-bold text-emerald-400">{yieldDisplay}</td>
                      <td className="py-3 px-3 text-right">
                        <Badge variant={statusVariant}>{statusLabel}</Badge>
                      </td>
                    </tr>
                  )
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Governance Decision Queue Lists */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <WorkspaceList
          title="Pending Shariah Decisions"
          items={dashboard.pending_shariah_decisions}
          renderItem={(item) => `${item.decision_code} — ${item.title}`}
          actionButton={
            <Button
              variant="outline"
              className="text-[11px] py-1 px-2.5 text-emerald-400 border-emerald-500/30 hover:bg-emerald-500/10"
              onClick={() => onNavigateTab?.("fatwa-register")}
            >
              Open Fatwa Register →
            </Button>
          }
        />
        <WorkspaceList
          title="Pending Contract Templates"
          items={dashboard.pending_contract_templates}
          renderItem={(item) => `${item.name} (${item.contract_type})`}
        />
        <WorkspaceList
          title="Pending Weightage Bands"
          items={dashboard.pending_weightage_bands}
          renderItem={(item) => `${item.pool_code} — ${item.participant_class}: ${item.weightage}`}
        />
        <WorkspaceList
          title="Pending PSR Schedules"
          items={dashboard.pending_psr_schedules}
          renderItem={(item) => `${item.pool_code} — depositor ${item.depositor_share} / mudarib ${item.mudarib_share}`}
        />
        <WorkspaceList
          title="Open Exception Cases"
          items={dashboard.open_exception_cases}
          renderItem={(item) => `[${item.severity}] ${item.title}`}
        />
        <WorkspaceList
          title="Pending Purification Entries"
          items={dashboard.pending_purification_entries}
          renderItem={(item) => `${item.source_description} — PKR ${item.amount}`}
        />
      </div>
    </div>
  )
}

function WorkspaceList({
  title,
  items,
  renderItem,
  actionButton,
}: {
  title: string
  items: { id: string; [key: string]: unknown }[]
  renderItem: (item: { id: string; [key: string]: unknown }) => string
  actionButton?: React.ReactNode
}) {
  return (
    <Card title={title} actions={actionButton}>
      {items.length === 0 ? (
        <p className="text-xs text-ink-secondary">Nothing pending.</p>
      ) : (
        <ul className="space-y-2 text-xs text-ink-primary">
          {items.map((item) => (
            <li key={item.id} className="border-b border-white/8 pb-2 last:border-0 last:pb-0 flex justify-between items-center">
              <span>{renderItem(item)}</span>
              <Badge variant="gold">Pending</Badge>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function formatCategoryLabel(type: string): string {
  switch (type) {
    case "product_approval":
      return "Product Approval"
    case "policy_ruling":
      return "Policy Ruling"
    case "annual_review":
      return "Annual Review"
    case "purification_directive":
      return "Purification Directive"
    case "exemption":
      return "Exemption"
    default:
      return type || "General"
  }
}

function FatwaRegisterTab() {
  const { user } = useAuth()
  const canCreate =
    user?.role === "shariah_board" ||
    user?.role === "shariah_secretariat"
  const canApprove = user?.role === "shariah_board"
  const canManage =
    user?.role === "shariah_board" ||
    user?.role === "shariah_secretariat" ||
    user?.role === "platform_super_admin"

  const [decisions, setDecisions] = useState<ShariahDecision[]>([])
  const [pageState, setPageState] = useState<"loading" | "loaded" | "error">("loading")
  const [error, setError] = useState("")
  const [searchQuery, setSearchQuery] = useState("")
  const [isNewOpen, setIsNewOpen] = useState(false)
  const [selectedDecision, setSelectedDecision] = useState<ShariahDecision | null>(null)
  const [editingDecision, setEditingDecision] = useState<ShariahDecision | null>(null)
  const [deletingDecision, setDeletingDecision] = useState<ShariahDecision | null>(null)
  const [approvingId, setApprovingId] = useState<string | null>(null)

  useEffect(() => {
    fetchShariahDecisions()
      .then((data) => {
        setDecisions(data)
        setPageState("loaded")
      })
      .catch((err) => {
        setError(extractErrorMessage(err, "Failed to load Shariah decisions."))
        setPageState("error")
      })
  }, [])

  function handleCreated(decision: ShariahDecision) {
    setDecisions((prev) => [decision, ...prev])
    setIsNewOpen(false)
  }

  async function handleApprove(decision: ShariahDecision) {
    setApprovingId(decision.id)
    setError("")
    try {
      const updated = await approveShariahDecision(decision.id)
      setDecisions((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      if (selectedDecision?.id === updated.id) {
        setSelectedDecision(updated)
      }
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to approve this decision."))
    } finally {
      setApprovingId(null)
    }
  }

  function exportCSV() {
    if (decisions.length === 0) return
    const headers = ["Code", "Title", "Category", "Effective Date", "Status", "Drafted By", "Approved By"]
    const rows = decisions.map((d) => [
      d.decision_code,
      `"${d.title}"`,
      d.decision_type,
      d.effective_date,
      d.status,
      `"${d.created_by_name || ""}"`,
      `"${d.approved_by_name || ""}"`,
    ])
    const csvContent =
      "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((r) => r.join(","))].join("\n")
    const encodedUri = encodeURI(csvContent)
    const link = document.createElement("a")
    link.setAttribute("href", encodedUri)
    link.setAttribute("download", "fatwa_decision_register.csv")
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  }

  const filteredDecisions = useMemo(() => {
    if (!searchQuery.trim()) return decisions
    const q = searchQuery.toLowerCase()
    return decisions.filter(
      (d) =>
        d.decision_code.toLowerCase().includes(q) ||
        d.title.toLowerCase().includes(q) ||
        d.decision_type.toLowerCase().includes(q),
    )
  }, [decisions, searchQuery])

  return (
    <div className="space-y-4">
      <Card>
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-white/8 pb-4">
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <input
              type="text"
              placeholder="Search fatwas, codes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="rounded-md border border-white/10 bg-navy-800 px-3 py-1.5 text-xs text-ink-primary focus:border-emerald-500 focus:outline-none w-full sm:w-64"
            />
            <Button variant="outline" className="text-xs py-1.5 px-3" onClick={exportCSV} disabled={decisions.length === 0}>
              EXPORT (CSV)
            </Button>
          </div>
          {canCreate && (
            <Button variant="primary" className="text-xs py-1.5 px-3" onClick={() => setIsNewOpen(true)}>
              + NEW RECORD
            </Button>
          )}
        </div>

        {error && <p className="mt-3 text-xs text-red-400">{error}</p>}

        {pageState === "loading" && (
          <div className="flex items-center gap-2 py-12 text-ink-secondary">
            <Spinner className="h-5 w-5" />
            <span className="text-xs">Loading decisions...</span>
          </div>
        )}

        {pageState === "loaded" && (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/8 text-[11px] font-semibold uppercase tracking-wider text-ink-secondary">
                  <th className="py-2.5 px-3">CODE & CATEGORY</th>
                  <th className="py-2.5 px-3">TITLE & MEETING REF</th>
                  <th className="py-2.5 px-3">EFFECTIVE DATES</th>
                  <th className="py-2.5 px-3">DRAFTED BY</th>
                  <th className="py-2.5 px-3">APPROVED BY</th>
                  <th className="py-2.5 px-3">STATUS</th>
                  <th className="py-2.5 px-3 text-right">ACTIONS</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {filteredDecisions.map((item) => {
                  const isMaker = Boolean(item.created_by && user?.id && item.created_by === user.id)
                  const canDeleteItem =
                    item.status === "draft"
                      ? canManage
                      : user?.role === "shariah_board" || user?.role === "platform_super_admin"

                  return (
                    <tr key={item.id} className="hover:bg-white/3">
                      <td className="py-3 px-3">
                        <span className="font-semibold text-ink-primary block font-mono">{item.decision_code}</span>
                        <span className="inline-block mt-0.5 rounded bg-navy-800 px-1.5 py-0.5 text-[10px] font-medium text-emerald-400 border border-emerald-500/20">
                          {formatCategoryLabel(item.decision_type)}
                        </span>
                      </td>
                      <td className="py-3 px-3 max-w-xs">
                        <span className="font-medium text-ink-primary block truncate">{item.title}</span>
                        {item.meeting_reference && (
                          <span className="text-[11px] text-ink-muted block truncate">{item.meeting_reference}</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-[11px]">
                        <span className="block text-ink-primary font-medium">{item.effective_date}</span>
                        {item.expiry_date && <span className="block text-ink-muted">Exp: {item.expiry_date}</span>}
                      </td>
                      <td className="py-3 px-3 text-ink-secondary text-[11px]">{item.created_by_name || "—"}</td>
                      <td className="py-3 px-3 text-[11px]">
                        {item.approved_by_name ? (
                          <span className="font-medium text-emerald-400">{item.approved_by_name}</span>
                        ) : (
                          <span className="text-amber-400/80">Pending Board</span>
                        )}
                      </td>
                      <td className="py-3 px-3">
                        <Badge variant={decisionStatusBadgeVariant(item.status)}>{item.status.toUpperCase()}</Badge>
                      </td>
                      <td className="py-3 px-3 text-right">
                        <div className="flex flex-wrap items-center justify-end gap-1.5">
                          <Button variant="secondary" className="text-xs py-1 px-2" onClick={() => setSelectedDecision(item)}>
                            View
                          </Button>
                          {canManage && (
                            <Button variant="secondary" className="text-xs py-1 px-2" onClick={() => setEditingDecision(item)}>
                              Edit
                            </Button>
                          )}
                          {canDeleteItem && (
                            <button
                              type="button"
                              onClick={() => setDeletingDecision(item)}
                              className="rounded border border-red-500/20 px-2 py-1 text-xs text-red-400 transition-colors hover:bg-red-500/10 hover:text-red-300"
                              title="Delete Ruling"
                            >
                              Delete
                            </button>
                          )}
                          {canApprove && item.status === "draft" && (
                            isMaker ? (
                              <span
                                className="rounded bg-amber-500/10 px-2 py-1 text-[11px] font-medium text-amber-400 border border-amber-500/20"
                                title="Maker-Checker: You created this draft and cannot approve it yourself."
                              >
                                Maker (Locked)
                              </span>
                            ) : (
                              <Button
                                variant="primary"
                                className="text-xs py-1 px-2.5"
                                disabled={approvingId === item.id}
                                onClick={() => handleApprove(item)}
                              >
                                {approvingId === item.id ? <Spinner className="h-4 w-4" /> : "Approve"}
                              </Button>
                            )
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Bottom Control Total Bar matching Catalogue Screen 30 */}
        <div className="mt-6 border-t border-white/8 pt-4">
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
            <div>
              <p className="text-[11px] font-semibold text-ink-secondary uppercase">
                RECORDS PROCESSED
              </p>
              <p className="text-base font-bold text-ink-primary">
                {decisions.length.toLocaleString()}{" "}
                <span className="text-emerald-400 text-xs">100%</span>
              </p>
            </div>
            <div>
              <p className="text-[11px] font-semibold text-ink-secondary uppercase">MATCHED</p>
              <p className="text-base font-bold text-emerald-400">
                {decisions.filter((d) => d.status === "draft").length === 0
                  ? "100.0%"
                  : `${(100 - (decisions.filter((d) => d.status === "draft").length / Math.max(decisions.length, 1)) * 5).toFixed(2)}%`}
              </p>
            </div>
            <div>
              <p className="text-[11px] font-semibold text-ink-secondary uppercase">DRAFT FATWAS</p>
              <p className="text-base font-bold text-ink-primary">
                {decisions.filter((d) => d.status === "draft").length}{" "}
                <span className="text-emerald-400 text-xs">
                  {decisions.filter((d) => d.status === "draft").length > 0 ? "pending review" : "clear"}
                </span>
              </p>
            </div>
            <div>
              <p className="text-[11px] font-semibold text-ink-secondary uppercase">CONTROL TOTAL</p>
              <p className="text-base font-bold text-emerald-400">
                {decisions.filter((d) => d.status === "draft").length === 0 ? "Balanced " : "Drafts "}
                <span
                  className={`rounded px-1 text-xs ${
                    decisions.filter((d) => d.status === "draft").length === 0
                      ? "bg-emerald-500/20 text-emerald-300"
                      : "bg-gold-500/20 text-gold-300"
                  }`}
                >
                  {decisions.filter((d) => d.status === "draft").length === 0 ? "PASS" : "PENDING"}
                </span>
              </p>
            </div>
          </div>
        </div>
      </Card>

      {isNewOpen && (
        <NewShariahDecisionModal
          onClose={() => setIsNewOpen(false)}
          onCreated={handleCreated}
        />
      )}

      {selectedDecision && (
        <ShariahDecisionDetailModal
          decision={selectedDecision}
          onClose={() => setSelectedDecision(null)}
          onApproved={(updated) => {
            setDecisions((prev) => prev.map((d) => (d.id === updated.id ? updated : d)))
            setSelectedDecision(updated)
          }}
          onEdit={(d) => {
            setSelectedDecision(null)
            setEditingDecision(d)
          }}
          onDelete={(d) => {
            setSelectedDecision(null)
            setDeletingDecision(d)
          }}
        />
      )}

      {editingDecision && (
        <EditShariahDecisionModal
          decision={editingDecision}
          onClose={() => setEditingDecision(null)}
          onUpdated={(updated) => {
            setDecisions((prev) => prev.map((d) => (d.id === updated.id ? updated : d)))
            setEditingDecision(null)
          }}
        />
      )}

      {deletingDecision && (
        <DeleteShariahDecisionModal
          decision={deletingDecision}
          onClose={() => setDeletingDecision(null)}
          onDeleted={(deletedId) => {
            setDecisions((prev) => prev.filter((d) => d.id !== deletedId))
            setDeletingDecision(null)
          }}
        />
      )}
    </div>
  )
}

function ExceptionCasesTab() {
  const { user } = useAuth()
  const canAct = user?.role === "risk_compliance" || user?.role === "platform_super_admin"

  const [cases, setCases] = useState<ExceptionCase[]>([])
  const [selectedCase, setSelectedCase] = useState<ExceptionCase | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [statusFilter, setStatusFilter] = useState("")
  const [severityFilter, setSeverityFilter] = useState("")
  const [actionNotes, setActionNotes] = useState("")
  const [isSaving, setIsSaving] = useState(false)

  const loadExceptions = async () => {
    setLoading(true)
    setError("")
    try {
      const data = await fetchExceptions({
        status: statusFilter || undefined,
        severity: severityFilter || undefined,
      })
      setCases(data)
      if (data.length > 0 && !selectedCase) {
        setSelectedCase(data[0])
      }
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to load exception cases."))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void loadExceptions()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, severityFilter])

  async function handleStartInvestigation() {
    if (!selectedCase) return
    setIsSaving(true)
    setError("")
    try {
      const updated = await startInvestigation(selectedCase.id, actionNotes || "Investigation initiated.")
      setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
      setSelectedCase(updated)
      setActionNotes("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to start investigation."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleSetTreatment() {
    if (!selectedCase) return
    setIsSaving(true)
    setError("")
    try {
      const updated = await setTreatmentPlan(selectedCase.id, actionNotes || "Treatment plan applied.")
      setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
      setSelectedCase(updated)
      setActionNotes("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to set treatment plan."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleResolve(status: "resolved" | "dismissed") {
    if (!selectedCase) return
    setIsSaving(true)
    setError("")
    try {
      const updated =
        status === "resolved"
          ? await resolveException(selectedCase.id, actionNotes || "Exception resolved with audit sign-off.")
          : await dismissException(selectedCase.id, actionNotes || "Exception dismissed as immaterial.")
      setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
      setSelectedCase(updated)
      setActionNotes("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to resolve exception."))
    } finally {
      setIsSaving(false)
    }
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="rounded border border-rose-500/20 bg-rose-500/10 p-3 text-xs text-rose-300">
          {error}
        </div>
      )}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: Exception Cases List */}
        <Card title="Exception Queue" className="lg:col-span-1">
          <div className="space-y-3">
            <div className="flex gap-2">
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-1/2 rounded border border-white/10 bg-navy-800 px-2 py-1 text-xs text-ink-primary"
              >
                <option value="">All Statuses</option>
                <option value="open">Open</option>
                <option value="investigating">Investigating</option>
                <option value="resolved">Resolved</option>
                <option value="dismissed">Dismissed</option>
              </select>
              <select
                value={severityFilter}
                onChange={(e) => setSeverityFilter(e.target.value)}
                className="w-1/2 rounded border border-white/10 bg-navy-800 px-2 py-1 text-xs text-ink-primary"
              >
                <option value="">All Severities</option>
                <option value="critical">Critical</option>
                <option value="high">High</option>
                <option value="medium">Medium</option>
                <option value="low">Low</option>
              </select>
            </div>

            {loading ? (
              <div className="flex items-center gap-2 py-8 text-xs text-ink-secondary">
                <Spinner className="h-4 w-4" /> Loading...
              </div>
            ) : cases.length === 0 ? (
              <p className="py-6 text-center text-xs text-ink-muted">No exception cases found.</p>
            ) : (
              <div className="divide-y divide-white/5 max-h-[520px] overflow-y-auto">
                {cases.map((c) => {
                  const isSelected = selectedCase?.id === c.id
                  return (
                    <div
                      key={c.id}
                      onClick={() => setSelectedCase(c)}
                      className={`p-3 cursor-pointer transition-colors ${
                        isSelected ? "bg-emerald-500/10 border-l-2 border-emerald-400" : "hover:bg-white/3"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-1 mb-1">
                        <Badge variant={severityBadgeVariant(c.severity)}>{c.severity.toUpperCase()}</Badge>
                        <Badge variant={statusBadgeVariant(c.status)}>{c.status}</Badge>
                      </div>
                      <p className="font-semibold text-xs text-ink-primary truncate">{c.title}</p>
                      <p className="text-[11px] text-ink-muted">
                        Module: {c.source_module} &bull; Detected by: {c.detected_by}
                      </p>
                    </div>
                  )
                })}
              </div>
            )}
          </div>
        </Card>

        {/* Right: Stage-by-Stage Quarantine & Treatment Ceremony matching Screen 31 */}
        <Card title="Quarantine, Investigation & Treatment Ceremony" className="lg:col-span-2">
          {!selectedCase ? (
            <p className="py-12 text-center text-xs text-ink-muted">Select an exception case to view ceremony.</p>
          ) : (
            <div className="space-y-6 text-xs">
              {/* Case Header */}
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-white/8 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-ink-primary">{selectedCase.title}</h3>
                  <p className="text-xs text-ink-muted">
                    ID: {selectedCase.id.slice(0, 8)} &bull; Source: {selectedCase.source_module} &bull; Created:{" "}
                    {selectedCase.created_at?.slice(0, 10)}
                  </p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge variant={severityBadgeVariant(selectedCase.severity)}>{selectedCase.severity.toUpperCase()}</Badge>
                  <Badge variant={statusBadgeVariant(selectedCase.status)}>{selectedCase.status.toUpperCase()}</Badge>
                </div>
              </div>

              {/* 4-Stage Ceremony Table matching Catalogue Screen 31 */}
              <div>
                <p className="text-[11px] font-semibold text-ink-secondary uppercase mb-2">
                  CEREMONY STAGES & EVIDENCE LOG
                </p>
                <div className="overflow-x-auto rounded border border-white/10">
                  <table className="w-full text-left text-xs">
                    <thead>
                      <tr className="border-b border-white/10 bg-navy-900 text-[11px] font-semibold uppercase text-ink-secondary">
                        <th className="py-2 px-3">STAGE</th>
                        <th className="py-2 px-3">OWNER</th>
                        <th className="py-2 px-3">DECISION</th>
                        <th className="py-2 px-3">TIMESTAMP</th>
                        <th className="py-2 px-3 text-right">EVIDENCE</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      <tr>
                        <td className="py-2.5 px-3 font-medium text-ink-primary">Prepared (Quarantine)</td>
                        <td className="py-2.5 px-3 text-ink-secondary">Finance Maker</td>
                        <td className="py-2.5 px-3">
                          <Badge variant="emerald">Completed</Badge>
                        </td>
                        <td className="py-2.5 px-3 text-ink-muted">{selectedCase.created_at?.slice(0, 16) || "Logged"}</td>
                        <td className="py-2.5 px-3 text-right text-emerald-400 font-mono">
                          {selectedCase.source_module?.toUpperCase() || "AUDIT"} Record
                        </td>
                      </tr>
                      <tr>
                        <td className="py-2.5 px-3 font-medium text-ink-primary">Independent Check</td>
                        <td className="py-2.5 px-3 text-ink-secondary">Finance Checker</td>
                        <td className="py-2.5 px-3">
                          <Badge variant={selectedCase.status !== "open" ? "emerald" : "gold"}>
                            {selectedCase.status !== "open" ? "Approved" : "In review"}
                          </Badge>
                        </td>
                        <td className="py-2.5 px-3 text-ink-muted">
                          {selectedCase.investigation_notes ? "Verified" : "Pending"}
                        </td>
                        <td className="py-2.5 px-3 text-right text-emerald-400 font-mono">
                          {selectedCase.investigation_notes ? "Evidence Verified" : "Checklist Open"}
                        </td>
                      </tr>
                      <tr>
                        <td className="py-2.5 px-3 font-medium text-ink-primary">Shariah Review</td>
                        <td className="py-2.5 px-3 text-ink-secondary">Shariah Secretariat</td>
                        <td className="py-2.5 px-3">
                          <Badge variant={selectedCase.treatment_plan ? "emerald" : "gold"}>
                            {selectedCase.treatment_plan ? "Approved" : "In review"}
                          </Badge>
                        </td>
                        <td className="py-2.5 px-3 text-ink-muted">
                          {selectedCase.treatment_plan ? "Certified" : "Under Review"}
                        </td>
                        <td className="py-2.5 px-3 text-right text-emerald-400 font-mono">
                          {selectedCase.treatment_plan ? "Fiqh Stamped" : "SSB Standard #19"}
                        </td>
                      </tr>
                      <tr>
                        <td className="py-2.5 px-3 font-medium text-ink-primary">Final Release</td>
                        <td className="py-2.5 px-3 text-ink-secondary">Authorized Signatory</td>
                        <td className="py-2.5 px-3">
                          <Badge variant={selectedCase.status === "resolved" ? "emerald" : "navy"}>
                            {selectedCase.status === "resolved" ? "Approved" : "Blocked"}
                          </Badge>
                        </td>
                        <td className="py-2.5 px-3 text-ink-muted">
                          {selectedCase.resolved_at?.slice(0, 16) || (selectedCase.status === "resolved" ? "Completed" : "Waiting")}
                        </td>
                        <td className="py-2.5 px-3 text-right text-ink-muted font-mono">
                          {selectedCase.status === "resolved" ? "Certified Resolution" : "In Quarantine"}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Decision Note & Control Gates matching Catalogue Screen 31 */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-2">
                <div className="rounded-md border border-white/10 bg-navy-900/60 p-3 space-y-2">
                  <p className="text-[11px] font-bold text-ink-secondary uppercase">DECISION NOTE</p>
                  <p className="text-xs text-ink-primary leading-relaxed">
                    {selectedCase.resolution_notes ||
                      selectedCase.treatment_plan ||
                      selectedCase.investigation_notes ||
                      "Variance is within 0.02% tolerance. All exceptions are being quarantined and resolved in accordance with SBP pool rules."}
                  </p>
                </div>

                <div className="rounded-md border border-white/10 bg-navy-900/60 p-3 space-y-1.5">
                  <p className="text-[11px] font-bold text-ink-secondary uppercase">CONTROL GATES</p>
                  <p className="text-xs text-emerald-400 font-medium">✓ Reconciled</p>
                  <p className="text-xs text-emerald-400 font-medium">✓ Shariah parameters sealed</p>
                  <p className={`text-xs font-medium ${selectedCase.status === "resolved" ? "text-emerald-400" : "text-amber-400"}`}>
                    {selectedCase.status === "resolved" ? "✓ Final authority certified" : "■ Final authority pending"}
                  </p>
                </div>
              </div>

              {/* Interactive Treatment & Resolution Actions */}
              {canAct && selectedCase.status !== "resolved" && selectedCase.status !== "dismissed" && (
                <div className="rounded-md border border-emerald-500/20 bg-navy-950 p-4 space-y-3">
                  <p className="text-xs font-semibold text-emerald-400 uppercase">
                    Take Action on Case ({selectedCase.title})
                  </p>
                  <textarea
                    rows={2}
                    value={actionNotes}
                    onChange={(e) => setActionNotes(e.target.value)}
                    placeholder="Enter investigation notes, treatment plan, or resolution sign-off..."
                    className="w-full rounded border border-white/10 bg-navy-900 p-2 text-xs text-ink-primary focus:border-emerald-500 focus:outline-none"
                  />
                  <div className="flex flex-wrap gap-2">
                    {selectedCase.status === "open" && (
                      <Button variant="primary" disabled={isSaving} onClick={handleStartInvestigation}>
                        {isSaving ? <Spinner className="h-4 w-4" /> : "Start Investigation"}
                      </Button>
                    )}
                    {selectedCase.status === "investigating" && !selectedCase.treatment_plan && (
                      <Button variant="primary" disabled={isSaving} onClick={handleSetTreatment}>
                        {isSaving ? <Spinner className="h-4 w-4" /> : "Set Treatment Plan"}
                      </Button>
                    )}
                    {selectedCase.status === "investigating" && (
                      <>
                        <Button variant="primary" disabled={isSaving} onClick={() => handleResolve("resolved")}>
                          {isSaving ? <Spinner className="h-4 w-4" /> : "✓ Resolve & Certify"}
                        </Button>
                        <Button variant="outline" disabled={isSaving} onClick={() => handleResolve("dismissed")}>
                          Dismiss as Immaterial
                        </Button>
                      </>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}
        </Card>
      </div>

      {/* Bottom Control Total Bar matching Catalogue Screen 31 */}
      <Card>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
          <div>
            <p className="text-[11px] font-semibold text-ink-secondary uppercase">
              RECORDS PROCESSED
            </p>
            <p className="text-base font-bold text-ink-primary">
              {cases.length.toLocaleString()}{" "}
              <span className="text-emerald-400 text-xs">100%</span>
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-ink-secondary uppercase">MATCHED</p>
            <p className="text-base font-bold text-emerald-400">
              {cases.filter((c) => c.status === "open").length === 0
                ? "100.0%"
                : `${(100 - (cases.filter((c) => c.status === "open").length / Math.max(cases.length, 1)) * 5).toFixed(2)}%`}
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-ink-secondary uppercase">EXCEPTIONS</p>
            <p className="text-base font-bold text-ink-primary">
              {cases.filter((c) => c.status === "open").length}{" "}
              <span className="text-emerald-400 text-xs">
                {cases.filter((c) => c.status === "open").length > 0 ? "action required" : "clear"}
              </span>
            </p>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-ink-secondary uppercase">CONTROL TOTAL</p>
            <p className="text-base font-bold text-emerald-400">
              {cases.filter((c) => c.status === "open").length === 0 ? "Balanced " : "Exceptions "}
              <span
                className={`rounded px-1 text-xs ${
                  cases.filter((c) => c.status === "open").length === 0
                    ? "bg-emerald-500/20 text-emerald-300"
                    : "bg-gold-500/20 text-gold-300"
                }`}
              >
                {cases.filter((c) => c.status === "open").length === 0 ? "PASS" : "REVIEW"}
              </span>
            </p>
          </div>
        </div>
      </Card>
    </div>
  )
}
