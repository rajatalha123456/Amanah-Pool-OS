import { useEffect, useState, useMemo } from "react"
import { useNavigate } from "react-router-dom"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { StatCard } from "../components/StatCard"
import { Table, type TableColumn } from "../components/Table"
import { Spinner } from "../components/Spinner"
import { DonutChart, type DonutSlice } from "../components/charts/DonutChart"
import { TrendAreaChart, type TrendDataPoint } from "../components/charts/TrendAreaChart"
import { fetchPools } from "../api/pools"
import { fetchProducts } from "../api/products"
import { fetchExceptions } from "../api/governance"
import { fetchAllocationRuns } from "../api/allocationRuns"
import type { BadgeVariant, Pool, Product, ExceptionCase, AllocationRun } from "../types"

const POOL_STATUS_BADGE: Record<string, BadgeVariant> = {
  draft: "neutral",
  pending_approval: "gold",
  approved: "gold",
  open: "emerald",
  allocation: "emerald",
  closed: "navy",
  archived: "neutral",
}

function poolStatusBadgeVariant(status: string): BadgeVariant {
  return POOL_STATUS_BADGE[status] ?? "neutral"
}

export function CommandCenter() {
  const navigate = useNavigate()
  const [dashboardState, setDashboardState] = useState<"loading" | "loaded" | "error">("loading")
  const [dashboardError, setDashboardError] = useState("")
  const [pools, setPools] = useState<Pool[]>([])
  const [products, setProducts] = useState<Product[]>([])
  const [exceptions, setExceptions] = useState<ExceptionCase[]>([])
  const [allocationRuns, setAllocationRuns] = useState<AllocationRun[]>([])

  useEffect(() => {
    setDashboardState("loading")
    Promise.all([
      fetchPools(),
      fetchProducts(),
      fetchExceptions({ status: "open" }).catch(() => [] as ExceptionCase[]),
      fetchAllocationRuns().catch(() => [] as AllocationRun[]),
    ])
      .then(([poolsData, productsData, exceptionsData, runsData]) => {
        setPools(poolsData)
        setProducts(productsData)
        setExceptions(exceptionsData)
        setAllocationRuns(runsData)
        setDashboardState("loaded")
      })
      .catch((err) => {
        setDashboardError(err instanceof Error ? err.message : "Failed to load dashboard data from backend")
        setDashboardState("error")
      })
  }, [])

  const totalPools = pools.length
  const activePools = pools.filter((p) => p.status === "open" || p.status === "allocation").length
  const pendingPools = pools.filter((p) => p.status === "draft" || p.status === "pending_approval").length
  const totalProducts = products.length
  const openExceptionsCount = exceptions.length

  // Dynamic Asset Allocation Breakdown by Operating Model from real database pools
  const modelSlices: DonutSlice[] = useMemo(() => {
    let mudharabah = 0
    let musharakah = 0
    let wakalah = 0
    let circles = 0

    for (const pool of pools) {
      const model = pool.product_detail?.operating_model ?? "bank_pool"
      const name = pool.name.toLowerCase()
      if (model === "community_circle" || name.includes("circle") || name.includes("committee")) {
        circles += 1
      } else if (model === "investment_pool" || name.includes("venture") || name.includes("musharakah")) {
        musharakah += 1
      } else if (name.includes("wakalah") || name.includes("treasury")) {
        wakalah += 1
      } else {
        mudharabah += 1
      }
    }

    const slices: DonutSlice[] = []
    if (mudharabah > 0) slices.push({ label: "Mudharabah General", value: mudharabah, color: "#10b981" })
    if (musharakah > 0) slices.push({ label: "Musharakah Venture", value: musharakah, color: "#38bdf8" })
    if (wakalah > 0) slices.push({ label: "Wakalah Agency", value: wakalah, color: "#a855f7" })
    if (circles > 0) slices.push({ label: "Community Circles", value: circles, color: "#f59e0b" })

    if (slices.length === 0) {
      return [
        { label: "No Active Pools", value: 1, color: "#334155" },
      ]
    }
    return slices
  }, [pools])

  // Distributable Profit & Gross Income Progression from real Allocation Runs
  const monthlyProfitTrend: TrendDataPoint[] = useMemo(() => {
    const validRuns = allocationRuns
      .filter((r) => r.status === "signed" || r.status === "pending_approval" || r.status === "simulated")
      .sort((a, b) => new Date(a.value_date).getTime() - new Date(b.value_date).getTime())

    if (validRuns.length > 0) {
      return validRuns.map((r) => ({
        label: r.value_date,
        value: Number(r.distributable_amount) / 1e6,
        secondaryValue: Number(r.gross_income) / 1e6,
        tooltipExtra: `Status: ${r.status.toUpperCase()} | Gross: PKR ${(Number(r.gross_income) / 1e6).toFixed(2)}M`,
      }))
    }

    return [
      { label: "Current Cycle", value: 0, secondaryValue: 0, tooltipExtra: "No allocation runs executed yet" },
    ]
  }, [allocationRuns])

  const columns: TableColumn<Pool>[] = [
    {
      header: "Pool Name",
      accessor: (pool) => (
        <span className="font-medium text-ink-primary hover:text-emerald-400">
          {pool.name}
        </span>
      ),
    },
    {
      header: "Code",
      accessor: (pool) => <span className="font-mono text-xs">{pool.code}</span>,
    },
    {
      header: "Product / Model",
      accessor: (pool) => (
        <span className="text-xs text-ink-secondary">
          {pool.product_detail?.name ?? "—"}
        </span>
      ),
    },
    {
      header: "Status",
      accessor: (pool) => (
        <Badge variant={poolStatusBadgeVariant(pool.status)}>{pool.status}</Badge>
      ),
    },
    {
      header: "Effective Date",
      accessor: (pool) => <span className="text-xs text-ink-secondary">{pool.effective_date}</span>,
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        screenNumber="01"
        title="Executive Command Center"
        subtitle="Enterprise visibility across active Islamic bank pools, profit curves, and Shariah structures"
      />

      {/* Real Dynamic Backend Stat Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Managed Pools"
          value={String(totalPools)}
          delta={`${activePools} active in-cycle`}
          deltaTone="positive"
        />
        <StatCard
          label="Active / In-Cycle Pools"
          value={String(activePools)}
          deltaTone="positive"
        />
        <StatCard
          label="Approved Products"
          value={String(totalProducts)}
          deltaTone="neutral"
        />
        <StatCard
          label="Open Exceptions"
          value={String(openExceptionsCount)}
          delta={pendingPools > 0 ? `${pendingPools} pools pending approval` : "All approvals clear"}
          deltaTone={openExceptionsCount > 0 ? "negative" : "positive"}
        />
      </div>

      {dashboardState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Connecting to backend and loading real data...</span>
        </div>
      )}

      {dashboardState === "error" && (
        <Card>
          <div className="p-4 space-y-3">
            <div className="flex items-center gap-2 text-rose-400">
              <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <p className="font-semibold text-sm">
                {dashboardError.includes("401")
                  ? "Authentication Session Expired (401 Unauthorized)"
                  : "Backend Connection Issue"}
              </p>
            </div>
            <p className="text-xs text-ink-secondary">
              {dashboardError.includes("401")
                ? "Your login session token has expired or is invalid. Please log in again with your tenant credentials to continue."
                : dashboardError}
            </p>
            <div className="flex items-center gap-3 pt-2">
              {dashboardError.includes("401") ? (
                <Button variant="primary" onClick={() => navigate("/login")}>
                  Log In Again
                </Button>
              ) : (
                <Button variant="secondary" onClick={() => window.location.reload()}>
                  Retry Connection
                </Button>
              )}
            </div>
          </div>
        </Card>
      )}

      {dashboardState === "loaded" && (
        <>
          {/* Institutional Visual Charts Row: Screen 01 Visual Catalogue */}
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
            {/* Donut Chart: Asset Allocation by Pool Operating Model */}
            <Card title="Asset Allocation by Shariah Model" className="lg:col-span-1">
              <DonutChart
                data={modelSlices}
                centerLabel="Total Pools"
                centerValue={String(totalPools)}
                formatValue={(v) => (totalPools === 0 ? "0 Pools" : `${v} Pools`)}
              />
            </Card>

            {/* Trend Area Chart: Distributable Profit & Gross Income */}
            <Card title="Distributable Profit & Gross Revenue Trajectory" className="lg:col-span-2">
              <TrendAreaChart
                data={monthlyProfitTrend}
                title="6-Month Distributable Profit Progression"
                subtitle="Distributable profit share vs total recognized gross pool income (PKR Millions)"
                valuePrefix="PKR "
                valueSuffix="M"
                primaryLegend="Distributable Profit"
                secondaryLegend="Gross Income"
                height={200}
              />
            </Card>
          </div>

          <Card title="Active Investment & Depositor Pools">
            {pools.length === 0 ? (
              <p className="text-sm text-ink-secondary py-4">
                No pools found in current tenant. Use "+ New Pool" to create one.
              </p>
            ) : (
              <Table
                columns={columns}
                data={pools}
                keyField={(p) => p.id}
                onRowClick={(p) => navigate(`/pools/${p.id}`)}
              />
            )}
          </Card>
        </>
      )}
    </div>
  )
}

