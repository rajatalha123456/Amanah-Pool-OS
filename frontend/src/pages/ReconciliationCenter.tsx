import { useEffect, useState, type FormEvent } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { Modal } from "../components/Modal"
import { Table, type TableColumn } from "../components/Table"
import { fetchPools } from "../api/pools"
import {
  fetchReconciliationBatches,
  fetchReconciliationBatchDetail,
  createReconciliationBatch,
  autoMatchBatch,
  clearVariance,
} from "../api/reconciliation"
import { extractErrorMessage } from "../api/errors"
import type { BadgeVariant, Pool, ReconciliationBatch, ReconciliationItem } from "../types"

const STATUS_BADGE: Record<string, BadgeVariant> = {
  pending: "gold",
  matched: "emerald",
  variance_flagged: "gold",
  discrepancy: "gold",
  cleared: "emerald",
  resolved: "emerald",
}

interface ReconciliationCenterProps {
  hideHeader?: boolean
}

export function ReconciliationCenter({ hideHeader = false }: ReconciliationCenterProps = {}) {
  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState<string>("")
  const [batches, setBatches] = useState<ReconciliationBatch[]>([])
  const [selectedBatch, setSelectedBatch] = useState<ReconciliationBatch | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // Modals
  const [showNewBatchModal, setShowNewBatchModal] = useState(false)
  const [newBatchPool, setNewBatchPool] = useState("")
  const [newBatchDate, setNewBatchDate] = useState(new Date().toISOString().split("T")[0])
  const [newBatchSource, setNewBatchSource] = useState("Core Banking CBS / GL")
  const [newBatchNotes, setNewBatchNotes] = useState("")
  const [isCreatingBatch, setIsCreatingBatch] = useState(false)

  // Clear variance modal
  const [clearItemTarget, setClearItemTarget] = useState<ReconciliationItem | null>(null)
  const [clearReason, setClearReason] = useState("")
  const [isClearing, setIsClearing] = useState(false)
  const [isAutoMatching, setIsAutoMatching] = useState(false)

  const loadData = async (poolId?: string) => {
    setLoading(true)
    setError(null)
    try {
      const [poolsData, batchesData] = await Promise.all([
        fetchPools(),
        fetchReconciliationBatches(poolId || undefined),
      ])
      setPools(poolsData)
      if (!newBatchPool && poolsData.length > 0) {
        setNewBatchPool(poolsData[0].id)
      }
      setBatches(batchesData)
      if (batchesData.length > 0) {
        const detail = await fetchReconciliationBatchDetail(batchesData[0].id)
        setSelectedBatch(detail)
      } else {
        setSelectedBatch(null)
      }
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData(selectedPoolId)
  }, [selectedPoolId])

  const handleSelectBatch = async (batchId: string) => {
    try {
      setSuccessMessage(null)
      const detail = await fetchReconciliationBatchDetail(batchId)
      setSelectedBatch(detail)
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  const handleCreateBatch = async (e: FormEvent) => {
    e.preventDefault()
    if (!newBatchPool) return
    setIsCreatingBatch(true)
    setError(null)
    setSuccessMessage(null)
    try {
      const created = await createReconciliationBatch({
        pool: newBatchPool,
        reconciliation_date: newBatchDate,
        source_system: newBatchSource,
        notes: newBatchNotes,
      })
      setShowNewBatchModal(false)
      setSuccessMessage("Reconciliation batch initiated successfully.")
      await loadData(selectedPoolId)
      setSelectedBatch(created)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setIsCreatingBatch(false)
    }
  }

  const handleAutoMatch = async () => {
    if (!selectedBatch) return
    setIsAutoMatching(true)
    setError(null)
    setSuccessMessage(null)
    try {
      const updated = await autoMatchBatch(selectedBatch.id)
      setSelectedBatch(updated)
      setSuccessMessage("Automated matching completed. All aligned records matched.")
      await loadData(selectedPoolId)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setIsAutoMatching(false)
    }
  }

  const handleClearVariance = async (e: FormEvent) => {
    e.preventDefault()
    if (!selectedBatch || !clearReason.trim()) return
    setIsClearing(true)
    setError(null)
    setSuccessMessage(null)
    try {
      const refreshed = await clearVariance(selectedBatch.id, clearItemTarget?.id, clearReason.trim())
      setClearItemTarget(null)
      setClearReason("")
      setSelectedBatch(refreshed)
      setSuccessMessage("Variance investigated, cleared, and documented for audit.")
      await loadData(selectedPoolId)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setIsClearing(false)
    }
  }

  const itemColumns: TableColumn<ReconciliationItem>[] = [
    {
      header: "Account / Ref",
      accessor: (item) => item.account_reference || item.source_reference || "—",
    },
    {
      header: "CBS Amount (PKR)",
      accessor: (item) =>
        Number(item.cbs_amount ?? item.cbs_balance ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      header: "GL Amount (PKR)",
      accessor: (item) =>
        Number(item.gl_amount ?? item.gl_balance ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      header: "Variance",
      accessor: (item) => {
        const v = Number(item.variance ?? 0)
        return (
          <span className={v !== 0 ? "font-semibold text-amber-400" : "text-emerald-400"}>
            {v.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </span>
        )
      },
    },
    {
      header: "Status",
      accessor: (item) => (
        <Badge variant={STATUS_BADGE[item.status] ?? "neutral"}>
          {item.status.toUpperCase()}
        </Badge>
      ),
    },
    {
      header: "Notes / Justification",
      accessor: (item) => (
        <span className="text-xs text-ink-secondary">
          {item.resolution_notes || item.variance_reason || "—"}
        </span>
      ),
    },
    {
      header: "Action",
      accessor: (item) => {
        if (item.status === "discrepancy" || item.status === "variance_flagged") {
          return (
            <Button
              variant="secondary"
              className="text-xs py-1 px-2"
              onClick={() => setClearItemTarget(item)}
            >
              Clear Variance
            </Button>
          )
        }
        return <span className="text-xs text-emerald-400">✓ Reconciled</span>
      },
    },
  ]

  const totalVariance = Number(
    selectedBatch?.variance_amount ?? selectedBatch?.total_variance ?? 0,
  )

  return (
    <div className="space-y-6">
      {!hideHeader ? (
        <PageHeader
          screenNumber="11"
          title="Reconciliation Center"
          subtitle="Core, bank, subledger and GL matching"
          actions={
            <div className="flex items-center gap-3">
              <select
                value={selectedPoolId}
                onChange={(e) => setSelectedPoolId(e.target.value)}
                className="rounded border border-navy-700 bg-navy-900 px-3 py-1.5 text-xs text-ink-primary focus:border-emerald-500 focus:outline-none"
              >
                <option value="">All Investment Pools</option>
                {pools.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} — {p.name}
                  </option>
                ))}
              </select>
              <Button variant="primary" onClick={() => setShowNewBatchModal(true)}>
                + New Reconciliation Batch
              </Button>
            </div>
          }
        />
      ) : (
        <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/8 bg-navy-900/60 p-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-semibold uppercase tracking-wider text-ink-secondary">Target Pool:</span>
            <select
              value={selectedPoolId}
              onChange={(e) => setSelectedPoolId(e.target.value)}
              className="rounded border border-navy-700 bg-navy-900 px-3 py-1.5 text-xs text-ink-primary focus:border-emerald-500 focus:outline-none"
            >
              <option value="">All Investment Pools</option>
              {pools.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} — {p.name}
                </option>
              ))}
            </select>
          </div>
          <Button variant="primary" onClick={() => setShowNewBatchModal(true)}>
            + New Reconciliation Batch
          </Button>
        </div>
      )}

      {error && (
        <div className="rounded border border-red-500/30 bg-red-950/20 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {successMessage && (
        <div className="rounded border border-emerald-500/30 bg-emerald-950/20 p-4 text-sm text-emerald-400">
          {successMessage}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading reconciliation records...</span>
        </div>
      ) : selectedBatch ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard
              label="Source System"
              value={selectedBatch.source_system || "Core Banking CBS / GL"}
              deltaTone="neutral"
            />
            <StatCard
              label="Total Records"
              value={String(selectedBatch.total_records ?? selectedBatch.items?.length ?? 0)}
              deltaTone="neutral"
            />
            <StatCard
              label="Matched Records"
              value={String(selectedBatch.matched_records ?? selectedBatch.matched_items_count ?? 0)}
              deltaTone="positive"
            />
            <StatCard
              label="Exceptions Flagged"
              value={String(selectedBatch.exception_count ?? selectedBatch.unmatched_items_count ?? 0)}
              deltaTone={(selectedBatch.exception_count ?? 0) === 0 ? "positive" : "negative"}
            />
            <StatCard
              label="Net Variance"
              value={`PKR ${totalVariance.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
              delta={selectedBatch.control_total_status || "BalancedPASS"}
              deltaTone={totalVariance === 0 ? "positive" : "negative"}
            />
          </div>

          <Card
            title={`Batch Alignment: ${selectedBatch.reconciliation_date || selectedBatch.batch_date || ""} — ${selectedBatch.pool_name || selectedBatch.pool_code || selectedBatch.pool}`}
            actions={
              <div className="flex items-center gap-3">
                <Badge variant={STATUS_BADGE[selectedBatch.status] ?? "neutral"}>
                  {selectedBatch.status.toUpperCase()}
                </Badge>
                {selectedBatch.status !== "matched" && selectedBatch.status !== "cleared" && (
                  <Button
                    variant="secondary"
                    disabled={isAutoMatching}
                    onClick={handleAutoMatch}
                    className="text-xs"
                  >
                    {isAutoMatching ? <Spinner className="h-3 w-3" /> : "Run Automated Matching"}
                  </Button>
                )}
              </div>
            }
          >
            <div className="space-y-4">
              <div className="flex items-center justify-between text-xs text-ink-secondary">
                <span>
                  Source: {selectedBatch.source_system || "Core Banking CBS / GL"}
                </span>
                <span>
                  Control Status:{" "}
                  <strong className={totalVariance === 0 ? "text-emerald-400" : "text-amber-400"}>
                    {selectedBatch.control_total_status || "BalancedPASS"}
                  </strong>
                </span>
              </div>

              {selectedBatch.notes && (
                <div className="rounded border border-white/6 bg-navy-900/40 p-3 text-xs text-ink-secondary">
                  <strong>Notes:</strong> {selectedBatch.notes}
                </div>
              )}

              {selectedBatch.items && selectedBatch.items.length > 0 ? (
                <Table
                  columns={itemColumns}
                  data={selectedBatch.items}
                  keyField={(item) => item.id}
                />
              ) : (
                <div className="rounded border border-dashed border-navy-700 p-8 text-center text-sm text-ink-muted">
                  No individual line discrepancies logged for this batch. Automated matching verifies aggregate balances.
                </div>
              )}
            </div>
          </Card>

          {/* Historical Batches */}
          {batches.length > 1 && (
            <Card title="Past Reconciliation Batches">
              <div className="divide-y divide-navy-800">
                {batches.map((b) => (
                  <div
                    key={b.id}
                    onClick={() => handleSelectBatch(b.id)}
                    className={`flex cursor-pointer items-center justify-between p-3 transition hover:bg-navy-900/60 ${
                      b.id === selectedBatch.id ? "bg-navy-900 border-l-2 border-emerald-500" : ""
                    }`}
                  >
                    <div className="space-y-1">
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-ink-primary">
                          {b.reconciliation_date || b.batch_date}
                        </span>
                        <Badge variant={STATUS_BADGE[b.status] ?? "neutral"}>{b.status}</Badge>
                      </div>
                      <p className="text-xs text-ink-secondary">
                        Records: {b.total_records ?? 0} | Matched: {b.matched_records ?? 0} | Exceptions: {b.exception_count ?? 0}
                      </p>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-ink-muted">Variance:</span>
                      <p
                        className={`text-sm font-semibold ${
                          Number(b.variance_amount ?? b.total_variance ?? 0) === 0
                            ? "text-emerald-400"
                            : "text-amber-400"
                        }`}
                      >
                        PKR {Number(b.variance_amount ?? b.total_variance ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <div className="py-12 text-center">
            <p className="text-base text-ink-secondary">No reconciliation batches recorded for this selection.</p>
            <p className="mt-1 text-xs text-ink-muted">
              Create a batch or run daily operations to feed CBS and GL balances.
            </p>
            <Button
              variant="primary"
              className="mt-4"
              onClick={() => setShowNewBatchModal(true)}
            >
              + Create First Reconciliation Batch
            </Button>
          </div>
        </Card>
      )}

      {/* New Batch Modal */}
      {showNewBatchModal && (
        <Modal
          isOpen={showNewBatchModal}
          onClose={() => setShowNewBatchModal(false)}
          title="Create New Reconciliation Batch"
        >
          <form onSubmit={handleCreateBatch} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Target Pool *</label>
              <select
                value={newBatchPool}
                onChange={(e) => setNewBatchPool(e.target.value)}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              >
                {pools.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.code} — {p.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Reconciliation Date *</label>
              <input
                type="date"
                value={newBatchDate}
                onChange={(e) => setNewBatchDate(e.target.value)}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Source System</label>
              <input
                type="text"
                value={newBatchSource}
                onChange={(e) => setNewBatchSource(e.target.value)}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Reconciliation Notes</label>
              <textarea
                rows={2}
                value={newBatchNotes}
                onChange={(e) => setNewBatchNotes(e.target.value)}
                placeholder="e.g. End of day reconciliation batch after CBS cut-off"
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button type="button" variant="secondary" onClick={() => setShowNewBatchModal(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={isCreatingBatch}>
                {isCreatingBatch ? <Spinner className="h-4 w-4" /> : "Save Batch"}
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* Clear Variance Modal */}
      {clearItemTarget && (
        <Modal
          isOpen={Boolean(clearItemTarget)}
          onClose={() => setClearItemTarget(null)}
          title={`Clear Discrepancy — Ref: ${clearItemTarget.account_reference || clearItemTarget.source_reference}`}
        >
          <form onSubmit={handleClearVariance} className="space-y-4">
            <div className="rounded border border-amber-500/30 bg-amber-950/20 p-3 text-xs text-amber-200">
              Variance amount: <strong>PKR {Number(clearItemTarget.variance).toLocaleString()}</strong>.
              Clearing requires a formal justification recorded for Shariah and statutory audit.
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Audit Justification & Reason *</label>
              <textarea
                rows={3}
                value={clearReason}
                onChange={(e) => setClearReason(e.target.value)}
                required
                placeholder="e.g. Float clearing timing difference confirmed with treasury operations; settled next business day."
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={() => setClearItemTarget(null)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={isClearing || !clearReason.trim()}>
                {isClearing ? <Spinner className="h-4 w-4" /> : "Authorize Clearance"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
