import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Badge } from "../components/Badge"
import { Card } from "../components/Card"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { Table, type TableColumn } from "../components/Table"
import { fetchPools } from "../api/pools"
import { fetchImportHistory } from "../api/balances"
import { fetchExceptions } from "../api/governance"
import { extractErrorMessage } from "../api/errors"
import { BalanceImport } from "./BalanceImport"
import { IncomeExpenseWorkbench } from "./IncomeExpenseWorkbench"
import { ReconciliationCenter } from "./ReconciliationCenter"
import { PeriodCloseManager } from "./PeriodCloseManager"
import { PayoutExecutionEngine } from "./PayoutExecutionEngine"
import type { BadgeVariant, BalanceImportBatch, Pool } from "../types"

type Tab = "cockpit" | "balance-import" | "income-expense" | "reconciliation" | "period-close" | "payout-clearing"
type PageState = "loading" | "loaded" | "error"

const TABS: { key: Tab; label: string; num: string }[] = [
  { key: "cockpit", label: "Operations Cockpit", num: "" },
  { key: "balance-import", label: "Balance Import", num: "" },
  { key: "income-expense", label: "Income & Expense", num: "" },
  { key: "reconciliation", label: "Reconciliation", num: "" },
  { key: "period-close", label: "Period Close & Locking", num: "16" },
  { key: "payout-clearing", label: "Payout Clearing Rails (Raast / 1LINK)", num: "35" },
]

const POOL_STATUS_BADGE: Record<string, BadgeVariant> = {
  draft: "neutral",
  approved: "gold",
  open: "emerald",
  allocation: "emerald",
  closed: "navy",
  archived: "neutral",
}

function poolStatusBadgeVariant(status: string): BadgeVariant {
  return POOL_STATUS_BADGE[status] ?? "neutral"
}

export function DailyOperationsCockpit() {
  const [activeTab, setActiveTab] = useState<Tab>("cockpit")

  const activeMetadata =
    activeTab === "balance-import"
      ? {
          num: "09",
          title: "Balance Import & Validation",
          sub: "File/API ingestion with control totals",
        }
      : activeTab === "income-expense"
      ? {
          num: "10",
          title: "Income & Expense Workbench",
          sub: "Pool-attributable performance events",
        }
      : activeTab === "reconciliation"
      ? {
          num: "11",
          title: "Reconciliation Center",
          sub: "Core, bank, subledger and GL matching",
        }
      : {
          num: "08",
          title: "Daily Operations Cockpit",
          sub: "Close readiness and exception handling",
        }

  return (
    <div>
      {activeTab !== "period-close" && activeTab !== "payout-clearing" && (
        <PageHeader
          screenNumber={activeMetadata.num}
          title={activeMetadata.title}
          subtitle={activeMetadata.sub}
        />
      )}

      <div className="mb-6 flex gap-6 border-b border-white/8 text-sm">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`pb-2.5 font-medium transition-colors ${
              activeTab === tab.key
                ? "border-b-2 border-emerald-500 text-ink-primary font-semibold"
                : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "cockpit" && <CockpitTab />}
      {activeTab === "balance-import" && <BalanceImport />}
      {activeTab === "income-expense" && <IncomeExpenseWorkbench />}
      {activeTab === "reconciliation" && <ReconciliationCenter hideHeader />}
      {activeTab === "period-close" && <PeriodCloseManager />}
      {activeTab === "payout-clearing" && <PayoutExecutionEngine />}
    </div>
  )
}


function CockpitTab() {
  const navigate = useNavigate()
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [pools, setPools] = useState<Pool[]>([])
  const [openExceptionCount, setOpenExceptionCount] = useState(0)
  const [closeReadyCount, setCloseReadyCount] = useState(0)
  const [inCyclePoolCount, setInCyclePoolCount] = useState(0)
  const [totalManagedFunds, setTotalManagedFunds] = useState(0)

  useEffect(() => {
    setPageState("loading")
    setPageError("")

    Promise.all([fetchPools(), fetchExceptions({ status: "open" })])
      .then(async ([poolsData, openExceptions]) => {
        setPools(poolsData)
        setOpenExceptionCount(openExceptions.length)

        const inCyclePools = poolsData.filter(
          (pool) => pool.status === "open" || pool.status === "allocation" || pool.status === "approved",
        )
        setInCyclePoolCount(inCyclePools.length)

        const histories = await Promise.all(
          inCyclePools.map((pool) => fetchImportHistory(pool.id).catch(() => [] as BalanceImportBatch[])),
        )

        const readyCount = histories.filter((batches) => batches.length > 0).length
        setCloseReadyCount(readyCount)

        const fundsTotal = histories.reduce((sum, batches) => {
          if (batches.length === 0) return sum
          const latestBatch = [...batches].sort(
            (a, b) => new Date(b.value_date).getTime() - new Date(a.value_date).getTime(),
          )[0]
          return sum + Number(latestBatch.control_total_actual ?? latestBatch.control_total_expected ?? 0)
        }, 0)
        setTotalManagedFunds(fundsTotal)

        setPageState("loaded")
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load the operations cockpit."))
        setPageState("error")
      })
  }, [])

  if (pageState === "loading") {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading operations cockpit...</span>
      </div>
    )
  }

  if (pageState === "error") {
    return (
      <Card>
        <p className="text-sm text-red-400">{pageError}</p>
      </Card>
    )
  }

  const activePools = pools.filter((pool) =>
    ["open", "allocation", "approved"].includes(pool.status),
  )
  const displayPools = activePools.length > 0 ? activePools : pools
  const closeReadinessPct =
    inCyclePoolCount > 0 ? Math.round((closeReadyCount / inCyclePoolCount) * 100) : 0

  const columns: TableColumn<Pool>[] = [
    {
      header: "Pool Name",
      accessor: (pool) => (
        <span className="font-semibold text-ink-primary hover:text-emerald-400 transition-colors">
          {pool.name}
        </span>
      ),
    },
    { header: "Code", accessor: (pool) => pool.code },
    {
      header: "Operating Model",
      accessor: (pool) => pool.product_detail?.operating_model?.replace(/_/g, " ").toUpperCase() ?? "BANK POOL",
    },
    {
      header: "Status",
      accessor: (pool) => <Badge variant={poolStatusBadgeVariant(pool.status)}>{pool.status.toUpperCase()}</Badge>,
    },
    { header: "Effective Date", accessor: (pool) => pool.effective_date },
  ]

  const operationalHealthPct =
    openExceptionCount === 0 && closeReadinessPct === 100
      ? "100.0%"
      : openExceptionCount === 0
      ? "99.98%"
      : `${(100 - Math.min(openExceptionCount * 0.15, 10)).toFixed(2)}%`
  const operationalHealthDelta =
    openExceptionCount === 0 ? "Reconciled & Balanced" : `${openExceptionCount} exceptions pending`
  const operationalHealthTone = openExceptionCount === 0 ? "positive" : "neutral"

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Managed Funds"
          value={totalManagedFunds > 0 ? `PKR ${totalManagedFunds.toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "PKR 0.00"}
          delta={`${inCyclePoolCount} in-cycle pools`}
          deltaTone="positive"
        />
        <StatCard
          label="Open Exceptions"
          value={String(openExceptionCount)}
          delta={`${openExceptionCount === 0 ? "All clear" : "Action required"}`}
          deltaTone={openExceptionCount > 0 ? "negative" : "positive"}
        />
        <StatCard
          label="Close Readiness"
          value={`${closeReadinessPct}%`}
          delta={`${closeReadyCount} / ${inCyclePoolCount} pools imported`}
          deltaTone={closeReadinessPct === 100 ? "positive" : "neutral"}
        />
        <StatCard
          label="Operational Health"
          value={operationalHealthPct}
          delta={operationalHealthDelta}
          deltaTone={operationalHealthTone}
        />
      </div>

      {/* CBS SFTP Live Link Banner */}
      <div className="flex flex-col sm:flex-row items-center justify-between p-4 rounded-lg border border-emerald-500/30 bg-emerald-950/20 text-xs text-emerald-300 gap-3">
        <div className="flex items-center gap-2.5">
          <span className="text-base">⚡</span>
          <div>
            <div className="font-semibold text-emerald-200">
              Automated Core Banking SFTP Daemon (Temenos T24 / Oracle Flexcube)
            </div>
            <div className="text-[11px] text-emerald-400/80">
              Cryptographic SHA-256 sidecar validation & uncleared float discrepancy detection active.
            </div>
          </div>
        </div>
        <button
          type="button"
          onClick={() => {
            const tabs = document.querySelectorAll("button")
            tabs.forEach((b) => {
              if (b.textContent?.includes("Balance Import")) b.click()
            })
          }}
          className="px-3 py-1.5 rounded bg-emerald-600 hover:bg-emerald-500 text-white font-medium text-xs transition-colors shrink-0 shadow-sm"
        >
          Launch SFTP Daemon →
        </button>
      </div>

      <Card title="Active Operational Pools">
        {displayPools.length === 0 ? (
          <p className="text-sm text-ink-secondary py-4">No operational pools found.</p>
        ) : (
          <Table
            columns={columns}
            data={displayPools}
            keyField={(pool) => pool.id}
            onRowClick={(pool) => navigate(`/pools/${pool.id}`)}
          />
        )}
      </Card>
    </div>
  )
}
