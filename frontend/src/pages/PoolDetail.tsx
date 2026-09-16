import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import {
  closePool,
  fetchPoolDetail,
  fetchPoolVersions,
  openPool,
  submitPoolForApproval,
} from "../api/pools"
import { extractErrorMessage } from "../api/errors"
import type { BadgeVariant, Pool, PoolVersion } from "../types"

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

export function PoolDetail() {
  const { id } = useParams<{ id: string }>()

  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [pool, setPool] = useState<Pool | null>(null)
  const [versions, setVersions] = useState<PoolVersion[]>([])

  const [actionError, setActionError] = useState("")
  const [isActionPending, setIsActionPending] = useState(false)

  function loadData() {
    if (!id) return
    setPageState("loading")
    Promise.all([fetchPoolDetail(id), fetchPoolVersions(id)])
      .then(([poolData, versionData]) => {
        setPool(poolData)
        setVersions(versionData)
        setPageState("loaded")
      })
      .catch(() => {
        setPageError("Failed to load data")
        setPageState("error")
      })
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function runAction(action: (id: string) => Promise<Pool>, fallbackMessage: string) {
    if (!id) return
    setActionError("")
    setIsActionPending(true)
    try {
      await action(id)
      loadData()
    } catch (err) {
      setActionError(extractErrorMessage(err, fallbackMessage))
    } finally {
      setIsActionPending(false)
    }
  }

  const versionColumns: TableColumn<PoolVersion>[] = [
    { header: "Version", accessor: (version) => version.version_number },
    { header: "Created At", accessor: (version) => version.created_at },
    {
      header: "Snapshot Summary",
      accessor: (version) =>
        `${version.snapshot.product.name} (${version.snapshot.product.status}) — ${version.snapshot.contract_template.name} v${version.snapshot.contract_template.version}`,
    },
  ]

  if (pageState === "loading") {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading pool...</span>
      </div>
    )
  }

  if (pageState === "error" || !pool) {
    return (
      <Card>
        <p className="text-sm text-red-400">{pageError || "Pool not found"}</p>
      </Card>
    )
  }

  return (
    <div>
      <PageHeader
        title={pool.name}
        subtitle={pool.code}
        actions={<Badge variant={poolStatusBadgeVariant(pool.status)}>{pool.status}</Badge>}
      />

      {actionError && <p className="mb-4 text-sm text-red-400">{actionError}</p>}

      <div className="mb-6 grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card title="Product">
          <p className="text-sm text-ink-primary">{pool.product_detail?.name ?? "—"}</p>
          <p className="mt-1 text-sm text-ink-secondary">
            Contract: {pool.product_detail?.contract_template?.name ?? "—"} (
            {pool.product_detail?.contract_template?.contract_type ?? "—"})
          </p>
        </Card>

        <Card title="Pool Info">
          <p className="text-sm text-ink-secondary">Effective Date: {pool.effective_date}</p>
          {pool.closed_date && (
            <p className="mt-1 text-sm text-ink-secondary">Closed Date: {pool.closed_date}</p>
          )}
          <p className="mt-1 text-sm text-ink-secondary">Status: {pool.status}</p>
        </Card>
      </div>

      <Card title="Actions" className="mb-6">
        {pool.status === "draft" && (
          <Button
            variant="primary"
            disabled={isActionPending}
            onClick={() => runAction(submitPoolForApproval, "Unable to submit pool for approval.")}
          >
            {isActionPending ? <Spinner className="h-4 w-4" /> : "Submit for Approval"}
          </Button>
        )}
        {pool.status === "approved" && (
          <Button
            variant="primary"
            disabled={isActionPending}
            onClick={() => runAction(openPool, "Unable to open pool.")}
          >
            {isActionPending ? <Spinner className="h-4 w-4" /> : "Open Pool"}
          </Button>
        )}
        {(pool.status === "open" || pool.status === "allocation") && (
          <Button
            variant="primary"
            disabled={isActionPending}
            onClick={() => runAction(closePool, "Unable to close pool.")}
          >
            {isActionPending ? <Spinner className="h-4 w-4" /> : "Close Pool"}
          </Button>
        )}
        {(pool.status === "closed" || pool.status === "archived") && (
          <p className="text-sm text-ink-secondary">Pool is closed</p>
        )}
      </Card>

      <Card title="Version History">
        {versions.length === 0 ? (
          <p className="text-sm text-ink-secondary">No versions yet</p>
        ) : (
          <Table columns={versionColumns} data={versions} keyField={(version) => version.id} />
        )}
      </Card>
    </div>
  )
}
