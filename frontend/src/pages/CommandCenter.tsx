import { useEffect, useState } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { PageHeader } from "../components/PageHeader"
import { StatCard } from "../components/StatCard"
import { Table, type TableColumn } from "../components/Table"
import { Spinner } from "../components/Spinner"
import { getHealthStatus } from "../api/health"
import { fetchPools } from "../api/pools"
import { fetchProducts } from "../api/products"
import type { BadgeVariant, Pool, Product } from "../types"

type ConnectionState = "loading" | "connected" | "error"
type DashboardState = "loading" | "loaded" | "error"

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

export function CommandCenter() {
  const [connectionState, setConnectionState] = useState<ConnectionState>("loading")
  const [healthStatus, setHealthStatus] = useState<string>("")
  const [connectionError, setConnectionError] = useState<string>("")

  const [dashboardState, setDashboardState] = useState<DashboardState>("loading")
  const [dashboardError, setDashboardError] = useState<string>("")
  const [pools, setPools] = useState<Pool[]>([])
  const [products, setProducts] = useState<Product[]>([])

  useEffect(() => {
    getHealthStatus()
      .then((data) => {
        setHealthStatus(data.status)
        setConnectionState("connected")
      })
      .catch((error) => {
        setConnectionError(error instanceof Error ? error.message : "Unknown error")
        setConnectionState("error")
      })
  }, [])

  useEffect(() => {
    Promise.all([fetchPools(), fetchProducts()])
      .then(([poolsData, productsData]) => {
        setPools(poolsData)
        setProducts(productsData)
        setDashboardState("loaded")
      })
      .catch(() => {
        setDashboardError("Failed to load data")
        setDashboardState("error")
      })
  }, [])

  const totalPools = pools.length
  const activePools = pools.filter((pool) => pool.status === "open").length
  const draftPools = pools.filter((pool) => pool.status === "draft").length
  const totalProducts = products.length

  const columns: TableColumn<Pool>[] = [
    { header: "Name", accessor: (pool) => pool.name },
    { header: "Code", accessor: (pool) => pool.code },
    {
      header: "Status",
      accessor: (pool) => (
        <Badge variant={poolStatusBadgeVariant(pool.status)}>{pool.status}</Badge>
      ),
    },
    { header: "Product", accessor: (pool) => pool.product_detail?.name ?? "—" },
    { header: "Effective Date", accessor: (pool) => pool.effective_date },
  ]

  return (
    <div>
      <PageHeader
        title="Executive Command Center"
        subtitle="Enterprise visibility across all pool models"
      />

      <Card title="Backend Connection" className="mb-6">
        {connectionState === "loading" && (
          <p className="text-sm text-ink-secondary">Checking backend connection...</p>
        )}
        {connectionState === "connected" && (
          <div className="flex items-center gap-2">
            <Badge variant="emerald">Connected</Badge>
            <span className="text-sm text-ink-secondary">
              GET /health/ responded with status: "{healthStatus}"
            </span>
          </div>
        )}
        {connectionState === "error" && (
          <div className="flex items-center gap-2">
            <Badge variant="gold">Disconnected</Badge>
            <span className="text-sm text-ink-secondary">{connectionError}</span>
          </div>
        )}
      </Card>

      {dashboardState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading pools and products...</span>
        </div>
      )}

      {dashboardState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{dashboardError}</p>
        </Card>
      )}

      {dashboardState === "loaded" && (
        <>
          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Total Pools" value={String(totalPools)} deltaTone="neutral" />
            <StatCard label="Active Pools" value={String(activePools)} deltaTone="neutral" />
            <StatCard label="Draft Pools" value={String(draftPools)} deltaTone="neutral" />
            <StatCard label="Total Products" value={String(totalProducts)} deltaTone="neutral" />
          </div>

          <Card title="Pools">
            {pools.length === 0 ? (
              <p className="text-sm text-ink-secondary">No pools yet</p>
            ) : (
              <Table columns={columns} data={pools} keyField={(pool) => pool.id} />
            )}
          </Card>
        </>
      )}
    </div>
  )
}
