import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { fetchPools } from "../api/pools"
import type { BadgeVariant, Pool } from "../types"

type PageState = "loading" | "loaded" | "error"

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

export function PoolCatalogue() {
  const navigate = useNavigate()
  const location = useLocation()
  const successMessage = (location.state as { successMessage?: string } | null)?.successMessage

  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [pools, setPools] = useState<Pool[]>([])

  useEffect(() => {
    fetchPools()
      .then((data) => {
        setPools(data)
        setPageState("loaded")
      })
      .catch(() => {
        setPageError("Failed to load data")
        setPageState("error")
      })
  }, [])

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
      <PageHeader
        title="Pool Catalogue"
        subtitle="All pools across bank, investment and community models"
        actions={
          <Link to="/pools/new">
            <Button variant="primary">+ New Pool</Button>
          </Link>
        }
      />

      <div className="mb-4 flex gap-4 border-b border-white/8 text-sm">
        <Link to="/products-pools" className="px-1 pb-2 text-ink-secondary hover:text-ink-primary">
          Products
        </Link>
        <span className="border-b-2 border-emerald-500 px-1 pb-2 font-medium text-ink-primary">
          Pools
        </span>
        <Link to="/contract-templates" className="px-1 pb-2 text-ink-secondary hover:text-ink-primary">
          Contract Templates
        </Link>
      </div>

      {successMessage && <p className="mb-4 text-sm text-emerald-400">{successMessage}</p>}

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading pools...</span>
        </div>
      )}

      {pageState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{pageError}</p>
        </Card>
      )}

      {pageState === "loaded" && (
        <Card>
          {pools.length === 0 ? (
            <p className="text-sm text-ink-secondary">No pools yet</p>
          ) : (
            <Table
              columns={columns}
              data={pools}
              keyField={(pool) => pool.id}
              onRowClick={(pool) => navigate(`/pools/${pool.id}`)}
            />
          )}
        </Card>
      )}
    </div>
  )
}
