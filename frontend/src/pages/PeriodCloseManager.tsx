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
  autoVerifyPeriodGates,
  signOffPeriodRole,
  executeLockCeremony,
  fetchSbpFilingPackage,
  type SbpFilingPackage,
} from "../api/periodClose"
import { extractErrorMessage } from "../api/errors"
import type { BadgeVariant, PeriodCloseChecklist, PeriodCloseStatus, Pool } from "../types"

const STATUS_BADGE: Record<PeriodCloseStatus, BadgeVariant> = {
  open: "neutral",
  in_review: "gold",
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
  const [verifyingGates, setVerifyingGates] = useState(false)

  // Sign-off modal state
  const [signOffModalRole, setSignOffModalRole] = useState<"pool_manager" | "shariah_reviewer" | "cfo_checker" | null>(null)
  const [signOffNotes, setSignOffNotes] = useState("")
  const [fatwaRef, setFatwaRef] = useState("FATWA-2026-M09-001")

  // Lock Ceremony Modal state
  const [showLockModal, setShowLockModal] = useState(false)
  const [lockNote, setLockNote] = useState("Statutory 5-Gate pre-close verification completed. Cycle permanently locked under SBP PR rules.")

  // SBP Filing Certificate Modal state
  const [showSbpCertModal, setShowSbpCertModal] = useState(false)
  const [sbpPackage, setSbpPackage] = useState<SbpFilingPackage | null>(null)
  const [loadingSbpCert, setLoadingSbpCert] = useState(false)
  const [copySuccess, setCopySuccess] = useState(false)

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

  // Run Real-Time 5-Gate Verification
  const handleAutoVerifyGates = async () => {
    if (!activeChecklist) return
    setVerifyingGates(true)
    setActionError(null)
    try {
      await autoVerifyPeriodGates(activeChecklist.id)
      const refreshed = await fetchPeriodCloseChecklistDetail(activeChecklist.id)
      setActiveChecklist(refreshed)
      await loadData(selectedPoolId)
    } catch (err) {
      setActionError(extractErrorMessage(err, "Failed to execute automated gate verification."))
    } finally {
      setVerifyingGates(false)
    }
  }

  // Toggle individual gate manually if permitted
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

  // Execute Digital Role Sign-Off
  const handleConfirmRoleSignOff = async () => {
    if (!activeChecklist || !signOffModalRole) return
    setActionLoading(true)
    setActionError(null)
    try {
      await signOffPeriodRole(
        activeChecklist.id,
        signOffModalRole,
        signOffNotes,
        signOffModalRole === "shariah_reviewer" ? fatwaRef : "",
      )
      setSignOffModalRole(null)
      setSignOffNotes("")
      const refreshed = await fetchPeriodCloseChecklistDetail(activeChecklist.id)
      setActiveChecklist(refreshed)
      await loadData(selectedPoolId)
    } catch (err) {
      setActionError(extractErrorMessage(err, "Digital role sign-off failed."))
    } finally {
      setActionLoading(false)
    }
  }

  // Execute Cryptographic SHA-256 Locking Ceremony
  const handleConfirmLockCeremony = async () => {
    if (!activeChecklist) return
    setActionLoading(true)
    setActionError(null)
    try {
      const lockRes = await executeLockCeremony(activeChecklist.id, lockNote)
      setShowLockModal(false)
      const refreshed = await fetchPeriodCloseChecklistDetail(activeChecklist.id)
      setActiveChecklist(refreshed)
      setSbpPackage(lockRes.sbp_package)
      setShowSbpCertModal(true)
      await loadData(selectedPoolId)
    } catch (err) {
      setActionError(extractErrorMessage(err, "Cryptographic locking ceremony failed."))
    } finally {
      setActionLoading(false)
    }
  }

  // Fetch SBP Filing Package
  const handleOpenSbpCertificate = async () => {
    if (!activeChecklist) return
    setLoadingSbpCert(true)
    setShowSbpCertModal(true)
    try {
      const pkg = await fetchSbpFilingPackage(activeChecklist.id)
      setSbpPackage(pkg)
    } catch (err) {
      setActionError(extractErrorMessage(err, "Failed to load SBP regulatory filing package."))
    } finally {
      setLoadingSbpCert(false)
    }
  }

  // Create new Period Close Record
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

  // Sign-off status extraction
  const signoffs = (activeChecklist?.checklist_data as Record<string, any>)?.multi_role_signoffs || {}
  const pmSigned = Boolean(signoffs.pool_manager?.signed)
  const shariahSigned = Boolean(signoffs.shariah_reviewer?.signed)
  const cfoSigned = Boolean(signoffs.cfo_checker?.signed)

  // Gate telemetry details
  const gateTelemetry = (activeChecklist?.checklist_data as Record<string, any>)?.gate_telemetry || {}

  // Cryptographic Seal
  const cryptoSeal =
    (activeChecklist?.checklist_data as Record<string, any>)?.cryptographic_seal ||
    activeChecklist?.lock_hash ||
    null

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <PageHeader
        screenNumber="16"
        title="Period Close Manager & SBP Statutory Seal"
        subtitle="5-Gate Pre-Close Verification, Multi-Role Shariah & CFO Sign-Off, and SHA-256 Immutable Audit Seal"
        actions={
          <div className="flex items-center gap-3">
            <select
              value={selectedPoolId}
              onChange={(e) => {
                setSelectedPoolId(e.target.value)
                if (e.target.value) navigate(`/period-close/${e.target.value}`)
              }}
              className="rounded border border-white/15 bg-navy-900 px-3 py-1.5 text-xs text-ink-primary focus:border-emerald-500 focus:outline-none"
            >
              <option value="">All Investment Pools</option>
              {pools.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} — {p.name}
                </option>
              ))}
            </select>

            {activeChecklist && (
              <Button
                variant="secondary"
                className="text-xs flex items-center gap-1.5 border-emerald-500/30 text-emerald-400"
                onClick={handleAutoVerifyGates}
                disabled={verifyingGates || activeChecklist.status === "locked"}
              >
                <span>{verifyingGates ? "Verifying..." : "⚡ Verify All Gates Live"}</span>
              </Button>
            )}

            <Button variant="primary" onClick={() => setShowCreateModal(true)} className="text-xs">
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
          {/* Top KPI Stat Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard
              label="Cycle Accounting Period"
              value={`${activeChecklist.period_start} to ${activeChecklist.period_end}`}
              deltaTone="neutral"
            />
            <StatCard
              label="Current Close Status"
              value={activeChecklist.status.toUpperCase()}
              deltaTone={activeChecklist.status === "locked" ? "positive" : activeChecklist.status === "certified" ? "positive" : "neutral"}
              delta={activeChecklist.status === "locked" ? "Immutable Ledger" : "Pending Action"}
            />
            <StatCard
              label="Multi-Role Signatures"
              value={`${[pmSigned, shariahSigned, cfoSigned].filter(Boolean).length} of 3 Signed`}
              deltaTone={pmSigned && shariahSigned && cfoSigned ? "positive" : "negative"}
              delta={pmSigned && shariahSigned && cfoSigned ? "Ready for Lock" : "Dual Maker/Checker"}
            />
            <StatCard
              label="Cryptographic Seal"
              value={cryptoSeal ? "SHA-256 Sealed" : "Unsealed (Draft)"}
              deltaTone={cryptoSeal ? "positive" : "neutral"}
              delta={cryptoSeal ? "Tamper-Proof" : "Awaiting Lock"}
            />
          </div>

          {/* Cryptographic Seal Banner if locked */}
          {cryptoSeal && (
            <div className="rounded-lg border border-emerald-500/40 bg-emerald-950/20 p-4 shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="text-lg">🔒</span>
                  <span className="text-xs uppercase tracking-wider text-emerald-400 font-bold">
                    State Bank of Pakistan (SBP) Cryptographic SHA-256 Ledger Seal
                  </span>
                  <Badge variant="emerald">PERMANENTLY LOCKED</Badge>
                </div>
                <p className="font-mono text-xs text-ink-primary break-all bg-navy-950/80 px-2 py-1 rounded border border-white/5">
                  {cryptoSeal}
                </p>
                <div className="text-[11px] text-ink-muted flex items-center gap-3">
                  <span>Standard: SBP IBD Circular 03/2012</span>
                  <span>•</span>
                  <span>AAOIFI FAS-30 Compliant</span>
                  <span>•</span>
                  <span>Retroactive Adjustments Blocked</span>
                </div>
              </div>

              <Button
                variant="secondary"
                className="whitespace-nowrap text-xs border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10"
                onClick={handleOpenSbpCertificate}
              >
                📄 View SBP Filing Package
              </Button>
            </div>
          )}

          {/* 5-Gate Checklist Card */}
          <Card
            title="Pre-Close Verification Checklist (The 5 Mandatory Statutory Gates)"
            actions={
              <div className="flex items-center gap-2">
                <Badge variant={STATUS_BADGE[activeChecklist.status]}>
                  {activeChecklist.status.toUpperCase()}
                </Badge>
                {activeChecklist.status !== "locked" && (
                  <Button
                    variant="secondary"
                    className="text-xs py-1 px-2 text-ink-secondary"
                    onClick={handleAutoVerifyGates}
                    disabled={verifyingGates}
                  >
                    {verifyingGates ? "Checking..." : "🔄 Re-Verify Gates"}
                  </Button>
                )}
              </div>
            }
          >
            <div className="space-y-4">
              <p className="text-xs text-ink-secondary">
                In compliance with AAOIFI Shariah Governance Standards and SBP Prudential Regulations, all five
                verification gates must be fully confirmed by operations and checker roles before certifying or locking this period.
              </p>

              <div className="divide-y divide-white/5 rounded-lg border border-white/10 bg-navy-900/50">
                {CHECKLIST_GATES.map((gate) => {
                  const isChecked = Boolean(
                    activeChecklist.checklist_data?.[gate.key] ?? activeChecklist.checklist_items?.[gate.key]
                  )
                  const isLockedOrCertified = activeChecklist.status === "locked"
                  const tel = gateTelemetry[gate.key]

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
                            className={`font-medium text-sm flex items-center gap-2 ${
                              isChecked ? "text-emerald-300" : "text-ink-primary"
                            }`}
                          >
                            {gate.label}
                            {isChecked && <span className="text-xs text-emerald-400">✓ VERIFIED</span>}
                          </span>
                          <span className="text-xs text-ink-muted">{gate.screenRef}</span>
                        </div>
                        <p className="mt-0.5 text-xs text-ink-secondary">{gate.description}</p>
                        {tel && (
                          <div className="mt-1.5 text-[11px] font-mono text-ink-muted bg-white/5 px-2 py-0.5 rounded inline-block">
                            Telemetry: {tel.details}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          </Card>

          {/* Multi-Role Dual Maker/Checker Sign-Off Board */}
          <Card title="Multi-Role Statutory Sign-Off Ceremony (Maker / Checker / Shariah)">
            <p className="text-xs text-ink-secondary mb-4">
              SBP Prudential Regulations require tripartite attestation from Pool Operations, the Resident Shariah Board Member, and the Chief Financial Officer before committing a period close.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Role 1: Pool Operations Maker */}
              <div className={`p-4 rounded-lg border ${pmSigned ? "border-emerald-500/40 bg-emerald-950/15" : "border-white/10 bg-navy-900"} space-y-3`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">🛠️</span>
                    <span className="font-bold text-xs uppercase tracking-wider text-ink-primary">
                      Pool Operations Maker
                    </span>
                  </div>
                  {pmSigned ? <Badge variant="emerald">SIGNED</Badge> : <Badge variant="neutral">PENDING</Badge>}
                </div>
                <div className="text-xs text-ink-muted">
                  Attests to daily balance accuracy, CBS reconciliation, and weightage curve lock.
                </div>
                {pmSigned ? (
                  <div className="text-[11px] bg-navy-950 p-2 rounded border border-white/5 space-y-1">
                    <div className="font-semibold text-emerald-400">✓ {signoffs.pool_manager?.user_name}</div>
                    <div className="text-ink-muted">{new Date(signoffs.pool_manager?.signed_at).toLocaleString()}</div>
                    {signoffs.pool_manager?.notes && <div className="italic text-ink-secondary">"{signoffs.pool_manager.notes}"</div>}
                  </div>
                ) : (
                  <Button
                    variant="secondary"
                    className="w-full text-xs border-emerald-500/30 text-emerald-300"
                    disabled={activeChecklist.status === "locked" || !allGatesChecked}
                    onClick={() => {
                      setSignOffModalRole("pool_manager")
                      setSignOffNotes("Pool manager attestation: all daily balances and CBS files reconciled.")
                    }}
                  >
                    Execute Maker Sign-Off
                  </Button>
                )}
              </div>

              {/* Role 2: Resident Shariah Board Member */}
              <div className={`p-4 rounded-lg border ${shariahSigned ? "border-emerald-500/40 bg-emerald-950/15" : "border-white/10 bg-navy-900"} space-y-3`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">📜</span>
                    <span className="font-bold text-xs uppercase tracking-wider text-ink-primary">
                      Shariah Board Member
                    </span>
                  </div>
                  {shariahSigned ? <Badge variant="emerald">STAMPED</Badge> : <Badge variant="gold">REQUIRED</Badge>}
                </div>
                <div className="text-xs text-ink-muted">
                  Certifies Shariah standard adherence, non-halal purification deductions, and profit distribution.
                </div>
                {shariahSigned ? (
                  <div className="text-[11px] bg-navy-950 p-2 rounded border border-white/5 space-y-1">
                    <div className="font-semibold text-emerald-400">✓ {signoffs.shariah_reviewer?.user_name}</div>
                    <div className="text-sky-400 font-mono text-[10px]">Fatwa Ref: {signoffs.shariah_reviewer?.fatwa_ref}</div>
                    <div className="text-ink-muted">{new Date(signoffs.shariah_reviewer?.signed_at).toLocaleString()}</div>
                  </div>
                ) : (
                  <Button
                    variant="secondary"
                    className="w-full text-xs border-gold-500/30 text-gold-300"
                    disabled={activeChecklist.status === "locked" || !allGatesChecked}
                    onClick={() => {
                      setSignOffModalRole("shariah_reviewer")
                      setSignOffNotes("Fatwa certification: profit calculation executed in compliance with AAOIFI FAS-30.")
                    }}
                  >
                    Stamp Shariah Board Fatwa
                  </Button>
                )}
              </div>

              {/* Role 3: Chief Financial Officer / Checker */}
              <div className={`p-4 rounded-lg border ${cfoSigned ? "border-emerald-500/40 bg-emerald-950/15" : "border-white/10 bg-navy-900"} space-y-3`}>
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">💼</span>
                    <span className="font-bold text-xs uppercase tracking-wider text-ink-primary">
                      Chief Financial Officer
                    </span>
                  </div>
                  {cfoSigned ? <Badge variant="emerald">CERTIFIED</Badge> : <Badge variant="neutral">FINAL CHECK</Badge>}
                </div>
                <div className="text-xs text-ink-muted">
                  Final financial checker approval, Mudarib share retention verification, and GL batch commitment.
                </div>
                {cfoSigned ? (
                  <div className="text-[11px] bg-navy-950 p-2 rounded border border-white/5 space-y-1">
                    <div className="font-semibold text-emerald-400">✓ {signoffs.cfo_checker?.user_name}</div>
                    <div className="text-ink-muted">{new Date(signoffs.cfo_checker?.signed_at).toLocaleString()}</div>
                    {signoffs.cfo_checker?.notes && <div className="italic text-ink-secondary">"{signoffs.cfo_checker.notes}"</div>}
                  </div>
                ) : (
                  <Button
                    variant="secondary"
                    className="w-full text-xs border-emerald-500/30 text-emerald-300"
                    disabled={activeChecklist.status === "locked" || !allGatesChecked}
                    onClick={() => {
                      setSignOffModalRole("cfo_checker")
                      setSignOffNotes("CFO dual-approval executed: GL batches reconciled, reserve transfers certified.")
                    }}
                  >
                    Execute CFO Certification
                  </Button>
                )}
              </div>
            </div>

            {/* Lock Ceremony Action Card */}
            <div className="mt-6 p-4 rounded-lg bg-navy-950 border border-white/10 flex flex-col md:flex-row items-center justify-between gap-4">
              <div className="text-xs">
                {activeChecklist.status === "open" && (
                  <span className="text-ink-secondary">Complete all 5 gates and obtain dual signatures to enable final locking.</span>
                )}
                {activeChecklist.status === "in_review" && (
                  <span className="text-amber-300">Maker sign-off complete. Awaiting Shariah and CFO checker signatures.</span>
                )}
                {activeChecklist.status === "certified" && (
                  <span className="text-emerald-300 font-semibold">
                    ✓ Period is fully certified by all statutory roles. Ready for irreversible SHA-256 cryptographic locking ceremony.
                  </span>
                )}
                {activeChecklist.status === "locked" && (
                  <span className="text-emerald-400">
                    Cycle locked with immutable audit seal. Retroactive changes strictly prevented by SBP Prudential Regulations.
                  </span>
                )}
              </div>

              <div className="flex items-center gap-3">
                {activeChecklist.status !== "locked" ? (
                  <Button
                    variant="primary"
                    disabled={!allGatesChecked || actionLoading}
                    onClick={() => setShowLockModal(true)}
                    className="bg-emerald-600 hover:bg-emerald-500 text-xs text-white"
                  >
                    🔒 Execute Cryptographic Lock Ceremony
                  </Button>
                ) : (
                  <Button
                    variant="secondary"
                    onClick={handleOpenSbpCertificate}
                    className="text-xs border-emerald-500/30 text-emerald-300"
                  >
                    📄 View SBP Filing Certificate
                  </Button>
                )}
              </div>
            </div>
          </Card>

          {/* Past Period Closes Table */}
          {checklists.length > 1 && (
            <Card title="Past Period Closes & Audit History">
              <div className="divide-y divide-white/5">
                {checklists.map((cl) => (
                  <div
                    key={cl.id}
                    onClick={() => setActiveChecklist(cl)}
                    className={`flex cursor-pointer items-center justify-between p-3 transition hover:bg-white/5 ${
                      cl.id === activeChecklist.id ? "bg-white/5 border-l-2 border-emerald-500" : ""
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-ink-primary">
                          {cl.period_start} → {cl.period_end}
                        </span>
                        <Badge variant={STATUS_BADGE[cl.status]}>{cl.status.toUpperCase()}</Badge>
                      </div>
                      <p className="text-xs text-ink-muted">Pool: {cl.pool_code || cl.pool}</p>
                    </div>
                    {cl.lock_hash && (
                      <span className="font-mono text-xs text-emerald-400">
                        {cl.lock_hash.slice(0, 16)}...
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

      {/* Role Sign-Off Modal */}
      {signOffModalRole && (
        <Modal
          isOpen={Boolean(signOffModalRole)}
          onClose={() => setSignOffModalRole(null)}
          title={`Digital Sign-Off: ${signOffModalRole.replace("_", " ").toUpperCase()}`}
        >
          <div className="space-y-4 text-xs">
            <p className="text-ink-secondary">
              By submitting this digital signature, you formally attest to the validity of the accounting entries, Shariah governance requirements, and Prudential Regulations for this cycle.
            </p>

            {signOffModalRole === "shariah_reviewer" && (
              <div>
                <label className="block text-ink-muted font-semibold uppercase mb-1">
                  Fatwa Approval Reference Number *
                </label>
                <input
                  type="text"
                  value={fatwaRef}
                  onChange={(e) => setFatwaRef(e.target.value)}
                  className="w-full rounded border border-white/15 bg-navy-950 px-3 py-2 text-ink-primary font-mono"
                  placeholder="e.g. FATWA-2026-M09-001"
                  required
                />
              </div>
            )}

            <div>
              <label className="block text-ink-muted font-semibold uppercase mb-1">
                Attestation & Decision Note
              </label>
              <textarea
                rows={3}
                value={signOffNotes}
                onChange={(e) => setSignOffNotes(e.target.value)}
                className="w-full rounded border border-white/15 bg-navy-950 px-3 py-2 text-ink-primary"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button variant="secondary" onClick={() => setSignOffModalRole(null)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleConfirmRoleSignOff} disabled={actionLoading}>
                {actionLoading ? <Spinner className="h-4 w-4" /> : "Commit Digital Signature"}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* Cryptographic Lock Ceremony Confirmation Modal */}
      {showLockModal && (
        <Modal
          isOpen={showLockModal}
          onClose={() => setShowLockModal(false)}
          title="Execute SBP Statutory Cryptographic Lock Ceremony"
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 bg-red-950/20 border border-red-500/30 rounded text-red-200">
              <div className="font-bold">⚠️ Warning: Irreversible Action</div>
              <div className="mt-1 text-[11px]">
                Once cryptographically locked with SHA-256 seal, this period can NEVER be reopened or altered. All balance imports, GL entries, and profit allocations will be permanently frozen.
              </div>
            </div>

            <div>
              <label className="block text-ink-muted font-semibold uppercase mb-1">
                ALCO Closing Memorandum Note
              </label>
              <textarea
                rows={3}
                value={lockNote}
                onChange={(e) => setLockNote(e.target.value)}
                className="w-full rounded border border-white/15 bg-navy-950 px-3 py-2 text-ink-primary"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button variant="secondary" onClick={() => setShowLockModal(false)}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleConfirmLockCeremony}
                disabled={actionLoading}
                className="bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                {actionLoading ? <Spinner className="h-4 w-4" /> : "Confirm & Apply Cryptographic Seal"}
              </Button>
            </div>
          </div>
        </Modal>
      )}

      {/* SBP Regulatory Filing Package & Certificate Modal */}
      {showSbpCertModal && (
        <Modal
          isOpen={showSbpCertModal}
          onClose={() => setShowSbpCertModal(false)}
          title="State Bank of Pakistan (SBP) Statutory Filing Certificate"
        >
          <div className="space-y-4 text-xs">
            {loadingSbpCert ? (
              <div className="flex items-center justify-center py-12">
                <Spinner className="h-6 w-6 text-emerald-400" />
              </div>
            ) : sbpPackage ? (
              <>
                <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-500/30 text-emerald-200 space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-emerald-300">{sbpPackage.certificate_id}</span>
                    <Badge variant="emerald">SBP IBD 03/2012 COMPLIANT</Badge>
                  </div>
                  <div className="text-[11px] font-mono break-all text-emerald-300/80">
                    Seal: {sbpPackage.cryptographic_seal}
                  </div>
                </div>

                <div className="p-3 bg-navy-950 rounded border border-white/10 space-y-2">
                  <div className="font-semibold text-ink-primary">Audited Cycle Financials:</div>
                  <div className="grid grid-cols-2 gap-2 text-[11px]">
                    <div>Gross Income: <span className="font-mono text-ink-primary font-bold">PKR {sbpPackage.financial_summary.gross_income_pkr.toLocaleString()}</span></div>
                    <div>Distributable Profit: <span className="font-mono text-emerald-400 font-bold">PKR {sbpPackage.financial_summary.distributable_profit_pkr.toLocaleString()}</span></div>
                    <div>Mudarib Share: <span className="font-mono text-ink-primary font-bold">PKR {sbpPackage.financial_summary.mudarib_fee_pkr.toLocaleString()}</span></div>
                    <div>Depositor Share: <span className="font-mono text-emerald-400 font-bold">PKR {sbpPackage.financial_summary.net_depositor_profit_pkr.toLocaleString()}</span></div>
                  </div>
                </div>

                {sbpPackage.signatories && (
                  <div className="p-3 bg-navy-950 rounded border border-white/10 space-y-1 text-[11px]">
                    <div className="font-semibold text-ink-primary">Statutory Signatories:</div>
                    <div className="text-ink-secondary">• Pool Manager: {sbpPackage.signatories.pool_manager}</div>
                    <div className="text-ink-secondary">• Shariah Board: {sbpPackage.signatories.shariah_reviewer}</div>
                    <div className="text-ink-secondary">• CFO / Checker: {sbpPackage.signatories.cfo_checker}</div>
                  </div>
                )}

                {sbpPackage.legal_statement && (
                  <p className="text-[10px] text-ink-muted italic border-t border-white/5 pt-2">
                    {sbpPackage.legal_statement}
                  </p>
                )}

                <div className="flex items-center justify-between pt-3 border-t border-white/10">
                  <Button
                    variant="secondary"
                    onClick={() => {
                      navigator.clipboard.writeText(JSON.stringify(sbpPackage, null, 2))
                      setCopySuccess(true)
                      setTimeout(() => setCopySuccess(false), 2000)
                    }}
                    className="text-xs"
                  >
                    {copySuccess ? "✓ Copied JSON" : "📋 Copy SBP Package JSON"}
                  </Button>
                  <Button variant="primary" onClick={() => setShowSbpCertModal(false)}>
                    Close
                  </Button>
                </div>
              </>
            ) : null}
          </div>
        </Modal>
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
                className="mt-1 w-full rounded border border-white/15 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
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
                  className="mt-1 w-full rounded border border-white/15 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted">Period End *</label>
                <input
                  type="date"
                  value={newPeriodEnd}
                  onChange={(e) => setNewPeriodEnd(e.target.value)}
                  required
                  className="mt-1 w-full rounded border border-white/15 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
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
                className="mt-1 w-full rounded border border-white/15 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
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
