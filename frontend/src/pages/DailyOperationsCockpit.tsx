import { useEffect, useState } from "react"
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
import type { BadgeVariant, BalanceImportBatch, Pool } from "../types"

type Tab = "cockpit" | "balance-import"
type PageState = "loading" | "loaded" | "error"

const TABS: { key: Tab; label: string }[] = [
  { key: "cockpit", label: "Cockpit" },
  { key: "balance-import", label: "Balance Import" },
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

  return (
    <div>
      <PageHeader
        title="Daily Operations"
        subtitle="Cross-pool operational overview and balance import"
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

      {activeTab === "cockpit" && <CockpitTab />}
      {activeTab === "balance-import" && <BalanceImport />}
    </div>
  )
}

function CockpitTab() {
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

        // No single aggregation endpoint exists for "funds across all
        // pools" or "which pools have imported balances this cycle", so
        // both are derived client-side from the existing per-pool
        // balance-imports endpoint — bounded by the number of in-cycle
        // (open/allocation) pools, which is small in practice.
        const inCyclePools = poolsData.filter(
          (pool) => pool.status === "open" || pool.status === "allocation",
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
          return sum + Number(latestBatch.control_total_actual ?? 0)
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

  const inProgressPools = pools.filter((pool) => pool.status === "allocation")
  const closeReadinessPct =
    inCyclePoolCount > 0 ? Math.round((closeReadyCount / inCyclePoolCount) * 100) : 0

  const columns: TableColumn<Pool>[] = [
    { header: "Name", accessor: (pool) => pool.name },
    { header: "Code", accessor: (pool) => pool.code },
    {
      header: "Status",
      accessor: (pool) => <Badge variant={poolStatusBadgeVariant(pool.status)}>{pool.status}</Badge>,
    },
    { header: "Product", accessor: (pool) => pool.product_detail?.name ?? "—" },
    { header: "Effective Date", accessor: (pool) => pool.effective_date },
  ]

  return (
    <div>
      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard
          label="Total Managed Funds"
          value={totalManagedFunds.toLocaleString()}
          deltaTone="neutral"
        />
        <StatCard
          label="Open Exceptions"
          value={String(openExceptionCount)}
          deltaTone={openExceptionCount > 0 ? "negative" : "positive"}
        />
        <StatCard
          label="Close Readiness"
          value={`${closeReadinessPct}%`}
          delta={`${closeReadyCount} / ${inCyclePoolCount} pools imported`}
          deltaTone={closeReadinessPct === 100 ? "positive" : "neutral"}
        />
      </div>

      <Card title="Pools In Progress (allocation cycle)">
        {inProgressPools.length === 0 ? (
          <p className="text-sm text-ink-secondary">No pools are currently mid-cycle.</p>
        ) : (
          <Table columns={columns} data={inProgressPools} keyField={(pool) => pool.id} />
        )}
      </Card>
    </div>
  )
}
