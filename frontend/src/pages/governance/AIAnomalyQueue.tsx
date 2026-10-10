import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Badge } from "../../components/Badge"
import { Spinner } from "../../components/Spinner"
import { Table, type TableColumn } from "../../components/Table"
import { fetchExceptions } from "../../api/governance"
import { fetchPools } from "../../api/pools"
import { extractErrorMessage } from "../../api/errors"
import { FraudCollusionGraphView } from "../../components/governance/FraudCollusionGraphView"
import type { BadgeVariant, ExceptionCase, Pool } from "../../types"

type PageState = "loading" | "loaded" | "error"

const SEVERITY_BADGE: Record<string, BadgeVariant> = {
  low: "neutral",
  medium: "gold",
  high: "gold",
  critical: "navy",
}

function severityBadgeVariant(severity: string): BadgeVariant {
  return SEVERITY_BADGE[severity] ?? "neutral"
}

const SEVERITY_RANK: Record<string, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
}

function severityRank(severity: string): number {
  return SEVERITY_RANK[severity] ?? 99
}

const SOURCE_MODULE_LABEL: Record<string, string> = {
  accounting: "Reconciliation",
  allocation: "Allocation",
  balance_import: "Balance Import",
  pool_lifecycle: "Pool Lifecycle",
  asset_assignment: "Asset Assignment",
  other: "Other",
}

const SOURCE_MODULE_BADGE: Record<string, BadgeVariant> = {
  accounting: "gold",
  allocation: "emerald",
  balance_import: "navy",
  pool_lifecycle: "navy",
  asset_assignment: "navy",
  other: "neutral",
}

function sourceModuleLabel(sourceModule: string): string {
  return SOURCE_MODULE_LABEL[sourceModule] ?? sourceModule
}

function sourceModuleBadgeVariant(sourceModule: string): BadgeVariant {
  return SOURCE_MODULE_BADGE[sourceModule] ?? "neutral"
}

export function AIAnomalyQueue() {
  const navigate = useNavigate()
  const [activeView, setActiveView] = useState<"queue" | "graph">("queue")
  const [cases, setCases] = useState<ExceptionCase[]>([])
  const [pools, setPools] = useState<Pool[]>([])
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")

  useEffect(() => {
    setPageState("loading")
    setPageError("")
    Promise.all([fetchExceptions({ detected_by: "system" }), fetchPools()])
      .then(([exceptions, poolList]) => {
        setCases(exceptions)
        setPools(poolList)
        setPageState("loaded")
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load AI-detected anomalies."))
        setPageState("error")
      })
  }, [])

  const poolNameById = new Map(pools.map((pool) => [pool.id, pool.name]))

  const sortedCases = [...cases].sort((a, b) => severityRank(a.severity) - severityRank(b.severity))

  const columns: TableColumn<ExceptionCase>[] = [
    { header: "Title", accessor: (c) => c.title },
    {
      header: "Source",
      accessor: (c) => <Badge variant={sourceModuleBadgeVariant(c.source_module)}>{sourceModuleLabel(c.source_module)}</Badge>,
    },
    {
      header: "Severity",
      accessor: (c) => <Badge variant={severityBadgeVariant(c.severity)}>{c.severity}</Badge>,
    },
    { header: "Pool", accessor: (c) => (c.pool ? poolNameById.get(c.pool) ?? c.pool : "—") },
    { header: "Detected At", accessor: (c) => new Date(c.created_at).toLocaleString() },
  ]

  return (
    <div className="space-y-4">
      {/* Sub-view switcher */}
      <div className="flex border-b border-ink/10 gap-2 mb-4">
        <button
          type="button"
          onClick={() => setActiveView("queue")}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors flex items-center gap-2 ${
            activeView === "queue"
              ? "bg-surface-subtle text-emerald-400 border-b-2 border-emerald-500"
              : "text-ink-secondary hover:text-ink"
          }`}
        >
          <span>📋 System Anomaly Cases</span>
          <Badge variant="neutral">{cases.length}</Badge>
        </button>
        <button
          type="button"
          onClick={() => setActiveView("graph")}
          className={`px-4 py-2 text-xs font-semibold rounded-t-lg transition-colors flex items-center gap-2 ${
            activeView === "graph"
              ? "bg-surface-subtle text-emerald-400 border-b-2 border-emerald-500"
              : "text-ink-secondary hover:text-ink"
          }`}
        >
          <span>🕸️ AI Fraud & Collusion Syndicate Graph</span>
          <Badge variant="gold">SBP AML</Badge>
        </button>
      </div>

      {activeView === "graph" ? (
        <FraudCollusionGraphView />
      ) : (
        <div>
          <p className="mb-4 text-sm text-ink-secondary">
            Anomalies automatically detected by the allocation engine, reconciliation checks, and other
            system-level monitors — sorted by severity, most critical first. Manually-raised cases are
            excluded here; see the Risk &amp; Compliance Exception Queue for the full list.
          </p>

          {pageState === "loading" && (
            <div className="flex justify-center py-10">
              <Spinner className="h-6 w-6 text-emerald-500" />
            </div>
          )}

          {pageState === "error" && <p className="text-sm text-red-400">{pageError}</p>}

          {pageState === "loaded" && sortedCases.length === 0 && (
            <p className="text-sm text-ink-secondary">No system-detected anomalies right now.</p>
          )}

          {pageState === "loaded" && sortedCases.length > 0 && (
            <Table
              columns={columns}
              data={sortedCases}
              keyField={(c) => c.id}
              onRowClick={(c) => navigate(`/exceptions/${c.id}`)}
            />
          )}
        </div>
      )}
    </div>
  )
}
