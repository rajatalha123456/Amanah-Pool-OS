import { useEffect, useState } from "react"
import { PageHeader } from "../components/PageHeader"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { approveShariahDecision, fetchShariahDashboard, fetchShariahDecisions } from "../api/shariahGovernance"
import { extractErrorMessage } from "../api/errors"
import { NewShariahDecisionModal } from "./governance/NewShariahDecisionModal"
import { PurificationLedger } from "./PurificationLedger"
import type { BadgeVariant, ShariahDashboard, ShariahDecision } from "../types"

type Tab = "workspace" | "fatwa-register" | "purification-ledger"

const TABS: { key: Tab; label: string }[] = [
  { key: "workspace", label: "Workspace" },
  { key: "fatwa-register", label: "Fatwa Register" },
  { key: "purification-ledger", label: "Purification Ledger" },
]

const DECISION_STATUS_BADGE: Record<string, BadgeVariant> = {
  draft: "gold",
  approved: "emerald",
  superseded: "neutral",
}

function decisionStatusBadgeVariant(status: string): BadgeVariant {
  return DECISION_STATUS_BADGE[status] ?? "neutral"
}

export function ShariahGovernance() {
  const [activeTab, setActiveTab] = useState<Tab>("workspace")

  return (
    <div>
      <PageHeader
        title="Shariah Governance"
        subtitle="Board workspace, fatwa register, and purification ledger"
      />

      <div className="mb-6 flex gap-4 border-b border-white/8 text-sm">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`px-1 pb-2 font-medium transition-colors ${
              activeTab === tab.key
                ? "border-b-2 border-emerald-500 text-ink-primary"
                : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "workspace" && <WorkspaceTab />}
      {activeTab === "fatwa-register" && <FatwaRegisterTab />}
      {activeTab === "purification-ledger" && <PurificationLedger />}
    </div>
  )
}

function WorkspaceTab() {
  const [dashboard, setDashboard] = useState<ShariahDashboard | null>(null)
  const [pageState, setPageState] = useState<"loading" | "loaded" | "error">("loading")
  const [error, setError] = useState("")

  useEffect(() => {
    fetchShariahDashboard()
      .then((data) => {
        setDashboard(data)
        setPageState("loaded")
      })
      .catch((err) => {
        setError(extractErrorMessage(err, "Failed to load the Shariah workspace."))
        setPageState("error")
      })
  }, [])

  if (pageState === "loading") {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading workspace...</span>
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
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Total Pending Items" value={String(dashboard.summary_counts.total_pending_items)} deltaTone="neutral" />
        <StatCard
          label="Critical Exceptions"
          value={String(dashboard.summary_counts.critical_exceptions)}
          deltaTone={dashboard.summary_counts.critical_exceptions > 0 ? "negative" : "positive"}
        />
        <StatCard label="Pending Decisions" value={String(dashboard.pending_shariah_decisions.length)} deltaTone="neutral" />
        <StatCard label="Pending Purification" value={String(dashboard.pending_purification_entries.length)} deltaTone="neutral" />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <WorkspaceList
          title="Pending Shariah Decisions"
          items={dashboard.pending_shariah_decisions}
          renderItem={(item) => `${item.decision_code} — ${item.title}`}
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
          renderItem={(item) => `${item.source_description} — ${item.amount}`}
        />
        <WorkspaceList
          title="Pending Pool Approvals"
          items={dashboard.pending_pool_approvals}
          renderItem={(item) => `${item.code} — ${item.name}`}
        />
      </div>
    </div>
  )
}

function WorkspaceList({
  title,
  items,
  renderItem,
}: {
  title: string
  items: { id: string; [key: string]: unknown }[]
  renderItem: (item: { id: string; [key: string]: unknown }) => string
}) {
  return (
    <Card title={title}>
      {items.length === 0 ? (
        <p className="text-sm text-ink-secondary">Nothing pending.</p>
      ) : (
        <ul className="space-y-2 text-sm text-ink-primary">
          {items.map((item) => (
            <li key={item.id} className="border-b border-white/8 pb-2 last:border-0 last:pb-0">
              {renderItem(item)}
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function FatwaRegisterTab() {
  const { user } = useAuth()
  const canCreate = user?.role === "shariah_board" || user?.role === "shariah_secretariat"
  const canApprove = user?.role === "shariah_board" || user?.role === "shariah_secretariat"

  const [decisions, setDecisions] = useState<ShariahDecision[]>([])
  const [pageState, setPageState] = useState<"loading" | "loaded" | "error">("loading")
  const [error, setError] = useState("")
  const [isNewOpen, setIsNewOpen] = useState(false)
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
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to approve this decision."))
    } finally {
      setApprovingId(null)
    }
  }

  const columns: TableColumn<ShariahDecision>[] = [
    { header: "Decision Code", accessor: (item) => item.decision_code },
    { header: "Title", accessor: (item) => item.title },
    {
      header: "Status",
      accessor: (item) => <Badge variant={decisionStatusBadgeVariant(item.status)}>{item.status}</Badge>,
    },
    { header: "Effective Date", accessor: (item) => item.effective_date },
    {
      header: "Action",
      accessor: (item) =>
        canApprove && item.status === "draft" ? (
          <Button variant="primary" disabled={approvingId === item.id} onClick={() => handleApprove(item)}>
            {approvingId === item.id ? <Spinner className="h-4 w-4" /> : "Approve"}
          </Button>
        ) : null,
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        {canCreate && <Button variant="primary" onClick={() => setIsNewOpen(true)}>+ New Decision</Button>}
      </div>

      {error && <p className="text-sm text-red-400">{error}</p>}

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading decisions...</span>
        </div>
      )}

      {pageState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{error}</p>
        </Card>
      )}

      {pageState === "loaded" && (
        <Card>
          {decisions.length === 0 ? (
            <p className="text-sm text-ink-secondary">No Shariah decisions yet.</p>
          ) : (
            <Table columns={columns} data={decisions} keyField={(item) => item.id} />
          )}
        </Card>
      )}

      {isNewOpen && <NewShariahDecisionModal onClose={() => setIsNewOpen(false)} onCreated={handleCreated} />}
    </div>
  )
}
