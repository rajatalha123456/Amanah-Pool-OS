import { useEffect, useState, type FormEvent } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { Modal } from "../components/Modal"
import { fetchPools } from "../api/pools"
import {
  fetchPeriodCloseChecklists,
  fetchPeriodCloseChecklistDetail,
  createPeriodCloseChecklist,
  updatePeriodCloseChecklist,
  certifyPeriodClose,
  lockPeriodClose,
} from "../api/periodClose"
import { extractErrorMessage } from "../api/errors"
import type { BadgeVariant, PeriodCloseChecklist, PeriodCloseStatus, Pool } from "../types"

const STATUS_BADGE: Record<PeriodCloseStatus, BadgeVariant> = {
  open: "neutral",
  pending_review: "gold",
  certified: "emerald",
  locked: "navy",
}

const CHECKLIST_GATES = [
  {
    key: "reconciled",
    label: "Gate 1: CBS & General Ledger Reconciled",
    description: "Core banking sub-ledger and GL control accounts matched with zero unaccounted variance.",
    screenRef: "Reconciliation Center",
  },
  {
    key: "shariah_parameters_sealed",
    label: "Gate 2: Shariah Parameters Sealed",
    description: "Weightage curves, PSR matrices, and Mudarib sharing ratios validated and locked for cycle.",
    screenRef: "Weightages & PSR",
  },
  {
    key: "exceptions_cleared",
    label: "Gate 3: Operational Exceptions Cleared",
    description: "All critical Shariah non-compliance, KYC blocks, and operational exception tickets resolved.",
    screenRef: "Exceptions Management",
  },
  {
    key: "allocation_signed",
    label: "Gate 4: Profit Allocation Run Signed",
    description: "Maker calculation checked, Shariah sign-off stamped, and Finance Head dual-approval executed.",
    screenRef: "Allocation Run Detail",
  },
  {
    key: "journals_posted",
    label: "Gate 5: GL Journal Batches Fully Posted",
    description: "All automated balanced journals posted to the core GL engine with verified debit/credit totals.",
    screenRef: "General Ledger Batch",
  },
]

export function PeriodCloseManager() {
  const { poolId } = useParams<{ poolId?: string }>()
  const navigate = useNavigate()

  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState<string>(poolId || "")
  const [checklists, setChecklists] = useState<PeriodCloseChecklist[]>([])
  const [activeChecklist, setActiveChecklist] = useState<PeriodCloseChecklist | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  // New Period Close Modal
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newPeriodStart, setNewPeriodStart] = useState("2026-09-01")
  const [newPeriodEnd, setNewPeriodEnd] = useState("2026-09-30")
  const [newNotes, setNewNotes] = useState("")

  const loadData = async (targetPoolId?: string) => {
    setLoading(true)
    setError(null)
    setActionError(null)
    try {
      const [poolsData, clData] = await Promise.all([
        fetchPools(),
        fetchPeriodCloseChecklists(targetPoolId || undefined),
      ])
      setPools(poolsData)
      setChecklists(clData)
      if (clData.length > 0) {
        const detail = await fetchPeriodCloseChecklistDetail(clData[0].id)
        setActiveChecklist(detail)
      } else {
        setActiveChecklist(null)
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

  const handleToggleGate = async (gateKey: string) => {
    if (!activeChecklist) return
    if (activeChecklist.status === "certified" || activeChecklist.status === "locked") return

    const currentItems = activeChecklist.checklist_data || activeChecklist.checklist_items || {}
    const updatedItems = {
      ...currentItems,
      [gateKey]: !currentItems[gateKey],
    }

    try {
      const updated = await updatePeriodCloseChecklist(activeChecklist.id, {
        checklist_data: updatedItems,
      })
      setActiveChecklist(updated)
      await loadData(selectedPoolId)
    } catch (err) {
      setActionError(extractErrorMessage(err))
    }
  }

  const handleCertify = async () => {
    if (!activeChecklist) return
    setActionLoading(true)
    setActionError(null)
    try {
      const certified = await certifyPeriodClose(activeChecklist.id)
      setActiveChecklist(certified)
      await loadData(selectedPoolId)
    } catch (err) {
      setActionError(extractErrorMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  const handleLock = async () => {
    if (!activeChecklist) return
    setActionLoading(true)
    setActionError(null)
    try {
      const locked = await lockPeriodClose(activeChecklist.id)
      setActiveChecklist(locked)
      await loadData(selectedPoolId)
    } catch (err) {
      setActionError(extractErrorMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  const handleCreateChecklist = async (e: FormEvent) => {
    e.preventDefault()
    if (!selectedPoolId && pools.length === 0) return
    const poolToUse = selectedPoolId || pools[0].id
    setActionLoading(true)
    setActionError(null)
    try {
      const created = await createPeriodCloseChecklist({
        pool: poolToUse,
        period_start: newPeriodStart,
        period_end: newPeriodEnd,
        notes: newNotes,
      })
      setShowCreateModal(false)
      await loadData(selectedPoolId)
      setActiveChecklist(created)
    } catch (err) {
      setActionError(extractErrorMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  const allGatesChecked =
    activeChecklist &&
    CHECKLIST_GATES.every((g) => {
      const gates = activeChecklist.checklist_data || activeChecklist.checklist_items || {}
      return Boolean(gates[g.key])
    })

  return (
    <div className="space-y-6">
      <PageHeader
        screenNumber="16"
        title="Period Close Manager"
        subtitle="5-Gate Pre-Close Verification, Checker Certification, and Cryptographic Locking"
        actions={
          <div className="flex items-center gap-3">
            <select
              value={selectedPoolId}
              onChange={(e) => {
                setSelectedPoolId(e.target.value)
                if (e.target.value) navigate(`/period-close/${e.target.value}`)
              }}
              className="rounded border border-navy-700 bg-navy-900 px-3 py-1.5 text-xs text-ink-primary focus:border-emerald-500 focus:outline-none"
            >
              <option value="">All Investment Pools</option>
              {pools.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} — {p.name}
                </option>
              ))}
            </select>
            <Button variant="primary" onClick={() => setShowCreateModal(true)}>
              + New Period Close
            </Button>
          </div>
        }
      />

      {error && (
        <div className="rounded border border-red-500/30 bg-red-950/20 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {actionError && (
        <div className="rounded border border-red-500/30 bg-red-950/20 p-4 text-sm text-red-400">
          {actionError}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading period close records...</span>
        </div>
      ) : activeChecklist ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Period Range"
              value={`${activeChecklist.period_start} to ${activeChecklist.period_end}`}
              deltaTone="neutral"
            />
            <StatCard
              label="Current Close Status"
              value={activeChecklist.status.toUpperCase()}
              deltaTone={activeChecklist.status === "locked" ? "positive" : "neutral"}
            />
            <StatCard
              label="Certification"
              value={activeChecklist.certified_by_name ? "Certified" : "Pending Checker"}
              deltaTone={activeChecklist.certified_by_name ? "positive" : "negative"}
            />
            <StatCard
              label="Immutable Seal"
              value={activeChecklist.lock_hash ? "Cryptographically Sealed" : "Unsealed"}
              deltaTone={activeChecklist.lock_hash ? "positive" : "neutral"}
            />
          </div>

          {/* Cryptographic Seal Hash Bar if locked */}
          {activeChecklist.lock_hash && (
            <div className="rounded-lg border border-emerald-500/40 bg-emerald-950/20 p-4">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs uppercase tracking-wider text-emerald-400 font-semibold">
                    🔒 SHA-256 Immutable Audit Seal
                  </span>
                  <p className="mt-1 font-mono text-xs text-ink-primary break-all">
                    {activeChecklist.lock_hash}
                  </p>
                </div>
                <Badge variant="emerald">LOCKED & SEALED</Badge>
              </div>
            </div>
          )}

          {/* 5-Gate Checklist Card */}
          <Card
            title="Pre-Close Verification Checklist (The 5 Mandatory Gates)"
            actions={
              <Badge variant={STATUS_BADGE[activeChecklist.status]}>
                {activeChecklist.status.toUpperCase()}
              </Badge>
            }
          >
            <div className="space-y-4">
              <p className="text-xs text-ink-secondary">
                In compliance with AAOIFI Governance Standards and SBP Prudential Regulations, all five
                verification gates must be fully confirmed by operations and checker roles before certifying or locking this period.
              </p>

              <div className="divide-y divide-navy-800 rounded-lg border border-navy-700 bg-navy-900/50">
                {CHECKLIST_GATES.map((gate) => {
                  const isChecked = Boolean(
                    activeChecklist.checklist_data?.[gate.key] ?? activeChecklist.checklist_items?.[gate.key]
                  )
                  const isLockedOrCertified = activeChecklist.status === "locked"

                  return (
                    <div
                      key={gate.key}
                      className={`flex items-start gap-3 p-4 transition ${
                        isChecked ? "bg-emerald-950/10" : ""
                      }`}
                    >
                      <input
                        type="checkbox"
                        checked={isChecked}
                        disabled={isLockedOrCertified}
                        onChange={() => handleToggleGate(gate.key)}
                        className="mt-1 h-5 w-5 rounded border-navy-700 text-emerald-600 focus:ring-emerald-500 cursor-pointer disabled:cursor-not-allowed"
                      />
                      <div className="flex-1">
                        <div className="flex items-center justify-between">
                          <span
                            className={`font-medium text-sm ${
                              isChecked ? "text-emerald-300" : "text-ink-primary"
                            }`}
                          >
                            {gate.label}
                          </span>
                          <span className="text-xs text-ink-muted">{gate.screenRef}</span>
                        </div>
                        <p className="mt-0.5 text-xs text-ink-secondary">{gate.description}</p>
                      </div>
                    </div>
                  )
                })}
              </div>

              {/* Action Buttons: Certify & Lock */}
              <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 rounded-lg border border-navy-700 bg-navy-900 p-4">
                <div className="text-xs text-ink-secondary">
                  {activeChecklist.status === "open" && (
                    <span>Check all 5 gates to enable Maker-Checker Certification.</span>
                  )}
                  {activeChecklist.status === "certified" && (
                    <span className="text-emerald-300">
                      ✓ Certified by {activeChecklist.certified_by_name || "Finance Checker"}. Ready for final SHA-256 seal locking.
                    </span>
                  )}
                  {activeChecklist.status === "locked" && (
                    <span className="text-ink-muted">
                      Period is locked. All postings and adjustments for this cycle are frozen.
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  {activeChecklist.status === "open" && (
                    <Button
                      variant="primary"
                      disabled={!allGatesChecked || actionLoading}
                      onClick={handleCertify}
                    >
                      {actionLoading ? <Spinner className="h-4 w-4" /> : "Certify Period"}
                    </Button>
                  )}

                  {activeChecklist.status === "certified" && (
                    <Button
                      variant="primary"
                      disabled={actionLoading}
                      onClick={handleLock}
                    >
                      {actionLoading ? (
                        <Spinner className="h-4 w-4" />
                      ) : (
                        "Lock Period (Generate SHA-256 Seal)"
                      )}
                    </Button>
                  )}
                </div>
              </div>
            </div>
          </Card>

          {/* Historical Periods */}
          {checklists.length > 1 && (
            <Card title="Past Period Closes">
              <div className="divide-y divide-navy-800">
                {checklists.map((cl) => (
                  <div
                    key={cl.id}
                    onClick={() => setActiveChecklist(cl)}
                    className={`flex cursor-pointer items-center justify-between p-3 transition hover:bg-navy-900/60 ${
                      cl.id === activeChecklist.id ? "bg-navy-900 border-l-2 border-emerald-500" : ""
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-ink-primary">
                          {cl.period_start} → {cl.period_end}
                        </span>
                        <Badge variant={STATUS_BADGE[cl.status]}>{cl.status}</Badge>
                      </div>
                      <p className="text-xs text-ink-muted">Pool: {cl.pool_code || cl.pool}</p>
                    </div>
                    {cl.lock_hash && (
                      <span className="font-mono text-xs text-emerald-400">
                        {cl.lock_hash.slice(0, 12)}...
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </Card>
          )}
        </>
      ) : (
        <Card>
          <div className="py-12 text-center">
            <p className="text-base text-ink-secondary">
              No period close checklist found for this pool.
            </p>
            <p className="mt-1 text-xs text-ink-muted">
              Initiate a period close checklist to begin the 5-gate attestation workflow.
            </p>
            <Button
              variant="primary"
              className="mt-4"
              onClick={() => setShowCreateModal(true)}
            >
              + Create Period Close Checklist
            </Button>
          </div>
        </Card>
      )}

      {/* Create Period Close Modal */}
      {showCreateModal && (
        <Modal
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          title="Create New Period Close Checklist"
        >
          <form onSubmit={handleCreateChecklist} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Target Pool *</label>
              <select
                value={selectedPoolId}
                onChange={(e) => setSelectedPoolId(e.target.value)}
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

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted">Period Start *</label>
                <input
                  type="date"
                  value={newPeriodStart}
                  onChange={(e) => setNewPeriodStart(e.target.value)}
                  required
                  className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted">Period End *</label>
                <input
                  type="date"
                  value={newPeriodEnd}
                  onChange={(e) => setNewPeriodEnd(e.target.value)}
                  required
                  className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Notes</label>
              <textarea
                rows={2}
                value={newNotes}
                onChange={(e) => setNewNotes(e.target.value)}
                placeholder="e.g. Q3 2026 Monthly cycle close"
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button type="button" variant="secondary" onClick={() => setShowCreateModal(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={actionLoading}>
                {actionLoading ? <Spinner className="h-4 w-4" /> : "Initiate Close"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
