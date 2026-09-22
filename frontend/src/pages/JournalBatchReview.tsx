import { useEffect, useState } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { fetchPools } from "../api/pools"
import { fetchJournalBatches } from "../api/accounting"
import type { BadgeVariant, JournalBatch, JournalEntry, Pool } from "../types"

type PageState = "loading" | "loaded" | "error"
type ExpandedBatches = Record<string, boolean>

const STATUS_BADGE: Record<string, BadgeVariant> = {
  posted: "emerald",
}

function statusBadgeVariant(status: string): BadgeVariant {
  return STATUS_BADGE[status] ?? "neutral"
}

export function JournalBatchReview() {
  const [pools, setPools] = useState<Pool[]>([])
  const [isLoadingPools, setIsLoadingPools] = useState(true)
  const [selectedPoolId, setSelectedPoolId] = useState("")

  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [batches, setBatches] = useState<JournalBatch[]>([])
  const [expandedBatches, setExpandedBatches] = useState<ExpandedBatches>({})

  useEffect(() => {
    fetchPools()
      .then((data) => {
        setPools(data)
        if (data.length > 0) {
          setSelectedPoolId(data[0].id)
        }
      })
      .catch(() => setPageError("Failed to load pools"))
      .finally(() => setIsLoadingPools(false))
  }, [])

  useEffect(() => {
    if (!selectedPoolId) return
    setPageState("loading")
    fetchJournalBatches(selectedPoolId)
      .then((data) => {
        setBatches(data)
        setPageState("loaded")
      })
      .catch(() => {
        setPageError("Failed to load journal batches")
        setPageState("error")
      })
  }, [selectedPoolId])

  function toggleBatchExpand(batchId: string) {
    setExpandedBatches((prev) => ({
      ...prev,
      [batchId]: !prev[batchId],
    }))
  }

  const entryColumns: TableColumn<JournalEntry>[] = [
    { header: "Account", accessor: (entry) => entry.account_name },
    {
      header: "Type",
      accessor: (entry) => (
        <Badge variant={entry.entry_type === "debit" ? "gold" : "emerald"}>
          {entry.entry_type}
        </Badge>
      ),
    },
    { header: "Amount", accessor: (entry) => entry.amount },
  ]

  if (pageState === "loading") {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading journal batches...</span>
      </div>
    )
  }

  return (
    <div>
      <Card title="Filter by Pool" className="mb-6">
        {isLoadingPools ? (
          <div className="flex items-center gap-2 text-sm text-ink-secondary">
            <Spinner className="h-4 w-4" />
            Loading pools...
          </div>
        ) : pools.length === 0 ? (
          <p className="text-sm text-gold-400">No pools available.</p>
        ) : (
          <select
            value={selectedPoolId}
            onChange={(e) => setSelectedPoolId(e.target.value)}
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          >
            {pools.map((pool) => (
              <option key={pool.id} value={pool.id}>
                {pool.name} ({pool.code})
              </option>
            ))}
          </select>
        )}
      </Card>

      <Card title="Posted Journal Batches">
        {pageState === "error" ? (
          <p className="text-sm text-red-400">{pageError}</p>
        ) : batches.length === 0 ? (
          <p className="text-sm text-ink-secondary">No journal batches found for this pool.</p>
        ) : (
          <div className="space-y-4">
            {batches.map((batch) => {
            const isExpanded = expandedBatches[batch.id]
            const isBalanced = batch.total_debit === batch.total_credit

            return (
              <div key={batch.id} className="border border-white/8 rounded-lg p-4">
                <button
                  onClick={() => toggleBatchExpand(batch.id)}
                  className="w-full text-left flex items-center justify-between hover:bg-white/5 p-2 -m-2 rounded"
                >
                  <div className="flex-1">
                    <div className="flex items-center gap-3">
                      <div>
                        <p className="text-sm font-semibold text-ink-primary">
                          {batch.batch_date}
                        </p>
                        <p className="text-xs text-ink-secondary">
                          Allocation Run: {batch.allocation_run}
                        </p>
                      </div>
                      <Badge variant={statusBadgeVariant(batch.status)}>
                        {batch.status}
                      </Badge>
                      {isBalanced && (
                        <span className="text-xs font-medium text-emerald-400">
                          Balanced ✓
                        </span>
                      )}
                    </div>
                  </div>
                  <div className="text-xs text-ink-secondary">
                    {isExpanded ? "▼" : "▶"}
                  </div>
                </button>

                {isExpanded && (
                  <div className="mt-4 space-y-3 border-t border-white/8 pt-4">
                    <div className="grid grid-cols-3 gap-4 text-sm">
                      <div>
                        <p className="text-xs font-semibold uppercase text-ink-secondary">
                          Total Debit
                        </p>
                        <p className="text-ink-primary">{batch.total_debit}</p>
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase text-ink-secondary">
                          Total Credit
                        </p>
                        <p className="text-ink-primary">{batch.total_credit}</p>
                      </div>
                      <div>
                        <p className="text-xs font-semibold uppercase text-ink-secondary">
                          Posted By
                        </p>
                        <p className="text-ink-primary">{batch.posted_by || "—"}</p>
                      </div>
                    </div>

                    <div className="mt-4">
                      <h4 className="text-sm font-semibold text-ink-primary mb-3">
                        Entries ({batch.entries.length})
                      </h4>
                      <Table
                        columns={entryColumns}
                        data={batch.entries}
                        keyField={(entry) => entry.id}
                      />
                    </div>
                  </div>
                )}
              </div>
            )
            })}
          </div>
        )}
      </Card>
    </div>
  )
}
