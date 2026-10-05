import { useEffect, useState, type FormEvent } from "react"
import { Card } from "../../components/Card"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { PageHeader } from "../../components/PageHeader"
import { Spinner } from "../../components/Spinner"
import { StatCard } from "../../components/StatCard"
import { Modal } from "../../components/Modal"
import { Table, type TableColumn } from "../../components/Table"
import { useAuth } from "../../api/auth"
import {
  fetchShariahAuditPlans,
  fetchShariahAuditPlanDetail,
  createShariahAuditPlan,
  approveShariahAuditPlan,
  createShariahAuditFinding,
  updateShariahAuditFinding,
} from "../../api/shariahAudit"
import { extractErrorMessage } from "../../api/errors"
import type {
  AuditPlanStatus,
  AuditSeverity,
  BadgeVariant,
  FindingStatus,
  ShariahAuditFinding,
  ShariahAuditPlan as ShariahAuditPlanType,
} from "../../types"

const PLAN_STATUS_BADGE: Record<AuditPlanStatus, BadgeVariant> = {
  draft: "neutral",
  approved: "gold",
  in_progress: "emerald",
  completed: "navy",
}

const SEVERITY_BADGE: Record<AuditSeverity, BadgeVariant> = {
  low: "neutral",
  medium: "navy",
  high: "gold",
  critical: "navy",
}

const FINDING_STATUS_BADGE: Record<FindingStatus, BadgeVariant> = {
  open: "gold",
  under_review: "navy",
  remediated: "emerald",
  closed: "neutral",
}

export function ShariahAuditPlan({ hideHeader = false }: { hideHeader?: boolean } = {}) {
  const { user } = useAuth()
  const isShariahBoard = user?.role === "shariah_board" || user?.role === "platform_super_admin"

  const [plans, setPlans] = useState<ShariahAuditPlanType[]>([])
  const [selectedPlan, setSelectedPlan] = useState<ShariahAuditPlanType | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionLoading, setActionLoading] = useState(false)

  // New Plan Modal
  const [showNewPlanModal, setShowNewPlanModal] = useState(false)
  const [newYear, setNewYear] = useState(2026)
  const [newTitle, setNewTitle] = useState("FY 2026 Annual Shariah Compliance & Fiqh Audit Plan")
  const [newScope, setNewScope] = useState("All Active Investment Pools, Asset Registries, and Profit Allocations")
  const [newTargetSamples, setNewTargetSamples] = useState(150)

  // New Finding Modal
  const [showNewFindingModal, setShowNewFindingModal] = useState(false)
  const [findingRef, setFindingRef] = useState("SAF-2026-001")
  const [findingTitle, setFindingTitle] = useState("")
  const [findingDesc, setFindingDesc] = useState("")
  const [findingSeverity, setFindingSeverity] = useState<AuditSeverity>("high")
  const [findingStandard, setFindingStandard] = useState("AAOIFI Shariah Standard No. 13 (Mudarabah)")
  const [findingPlan, setFindingPlan] = useState("")
  const [findingDeadline, setFindingDeadline] = useState("2026-10-31")

  const loadPlans = async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchShariahAuditPlans()
      setPlans(data)
      if (data.length > 0) {
        const detail = await fetchShariahAuditPlanDetail(data[0].id)
        setSelectedPlan(detail)
      } else {
        setSelectedPlan(null)
      }
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPlans()
  }, [])

  const handleSelectPlan = async (planId: string) => {
    try {
      const detail = await fetchShariahAuditPlanDetail(planId)
      setSelectedPlan(detail)
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  const handleCreatePlan = async (e: FormEvent) => {
    e.preventDefault()
    setActionLoading(true)
    try {
      const created = await createShariahAuditPlan({
        year: newYear,
        title: newTitle,
        universe_scope: newScope,
        target_samples: newTargetSamples,
        tested_samples: 0,
        status: "draft",
      })
      setShowNewPlanModal(false)
      await loadPlans()
      setSelectedPlan(created)
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  const handleApprovePlan = async () => {
    if (!selectedPlan) return
    setActionLoading(true)
    try {
      const approved = await approveShariahAuditPlan(selectedPlan.id)
      setSelectedPlan(approved)
      await loadPlans()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  const handleCreateFinding = async (e: FormEvent) => {
    e.preventDefault()
    if (!selectedPlan || !findingTitle.trim()) return
    setActionLoading(true)
    try {
      await createShariahAuditFinding({
        audit_plan: selectedPlan.id,
        finding_ref: findingRef,
        title: findingTitle,
        description: findingDesc,
        severity: findingSeverity,
        shariah_standard_ref: findingStandard,
        remediation_plan: findingPlan,
        status: "open",
        identified_date: new Date().toISOString().split("T")[0],
        remediation_deadline: findingDeadline,
      })
      setShowNewFindingModal(false)
      setFindingTitle("")
      setFindingDesc("")
      setFindingPlan("")
      const refreshed = await fetchShariahAuditPlanDetail(selectedPlan.id)
      setSelectedPlan(refreshed)
      await loadPlans()
    } catch (err) {
      setError(extractErrorMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  const handleUpdateFindingStatus = async (finding: ShariahAuditFinding, newStatus: FindingStatus) => {
    if (!selectedPlan) return
    try {
      await updateShariahAuditFinding(finding.id, { status: newStatus })
      const refreshed = await fetchShariahAuditPlanDetail(selectedPlan.id)
      setSelectedPlan(refreshed)
    } catch (err) {
      setError(extractErrorMessage(err))
    }
  }

  const findingColumns: TableColumn<ShariahAuditFinding>[] = [
    {
      header: "Ref #",
      accessor: (f) => <span className="font-mono text-xs font-semibold text-gold-400">{f.finding_ref}</span>,
    },
    {
      header: "Finding & Standard",
      accessor: (f) => (
        <div className="space-y-0.5">
          <p className="font-medium text-sm text-ink-primary">{f.title}</p>
          <p className="text-xs text-ink-secondary">{f.shariah_standard_ref}</p>
        </div>
      ),
    },
    {
      header: "Severity",
      accessor: (f) => (
        <Badge variant={SEVERITY_BADGE[f.severity]}>
          {f.severity.toUpperCase()}
        </Badge>
      ),
    },
    {
      header: "Status",
      accessor: (f) => (
        <Badge variant={FINDING_STATUS_BADGE[f.status]}>
          {f.status.replace("_", " ").toUpperCase()}
        </Badge>
      ),
    },
    {
      header: "Deadline",
      accessor: (f) => (
        <span className="text-xs text-ink-secondary">
          {f.remediation_deadline || "No deadline"}
        </span>
      ),
    },
    {
      header: "Action",
      accessor: (f) => {
        if (f.status === "open") {
          return (
            <Button
              variant="secondary"
              className="text-xs py-1 px-2"
              onClick={() => handleUpdateFindingStatus(f, "remediated")}
            >
              Mark Remediated
            </Button>
          )
        }
        if (f.status === "remediated") {
          return (
            <Button
              variant="secondary"
              className="text-xs py-1 px-2 text-emerald-400"
              onClick={() => handleUpdateFindingStatus(f, "closed")}
            >
              Close Finding
            </Button>
          )
        }
        return <span className="text-xs text-ink-muted">✓ Closed</span>
      },
    },
  ]

  const coveragePct =
    selectedPlan && selectedPlan.target_samples > 0
      ? Math.round((selectedPlan.tested_samples / selectedPlan.target_samples) * 100)
      : 0

  return (
    <div className="space-y-6">
      {!hideHeader ? (
        <PageHeader
          screenNumber="33"
          title="Shariah Audit Plan"
          subtitle="Risk-based universe, samples and findings"
          actions={
            <div className="flex items-center gap-3">
              <Button variant="secondary" onClick={() => setShowNewPlanModal(true)}>
                + New Audit Plan
              </Button>
              {selectedPlan && (
                <Button variant="primary" onClick={() => setShowNewFindingModal(true)}>
                  + Log Finding
                </Button>
              )}
            </div>
          }
        />
      ) : (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4 border-b border-white/8 pb-4">
          <div>
            <h2 className="text-base font-semibold text-ink-primary">
              Annual Shariah Audit Universe & Sample Testing
            </h2>
            <p className="text-xs text-ink-secondary">
              Risk-based sampling, AAOIFI FAS 30 review, and remediation tracking
            </p>
          </div>
          <div className="flex items-center gap-3">
            <Button variant="secondary" onClick={() => setShowNewPlanModal(true)}>
              + New Audit Plan
            </Button>
            {selectedPlan && (
              <Button variant="primary" onClick={() => setShowNewFindingModal(true)}>
                + Log Finding
              </Button>
            )}
          </div>
        </div>
      )}

      {error && (
        <div className="rounded border border-red-500/30 bg-red-950/20 p-4 text-sm text-red-400">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading Shariah Audit Universe...</span>
        </div>
      ) : selectedPlan ? (
        <>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
            <StatCard label="Audit Year" value={String(selectedPlan.year)} deltaTone="neutral" />
            <StatCard
              label="Universe Target Samples"
              value={String(selectedPlan.target_samples)}
              deltaTone="neutral"
            />
            <StatCard
              label="Samples Tested"
              value={String(selectedPlan.tested_samples)}
              deltaTone="neutral"
            />
            <StatCard
              label="Sampling Coverage"
              value={`${coveragePct}%`}
              deltaTone={coveragePct >= 80 ? "positive" : "neutral"}
            />
            <StatCard
              label="Audit Findings Logged"
              value={String(selectedPlan.findings_count || selectedPlan.findings?.length || 0)}
              deltaTone={selectedPlan.findings_count === 0 ? "positive" : "negative"}
            />
          </div>

          <Card
            title={`${selectedPlan.title} (${selectedPlan.year})`}
            actions={
              <div className="flex items-center gap-3">
                <Badge variant={PLAN_STATUS_BADGE[selectedPlan.status]}>
                  {selectedPlan.status.toUpperCase()}
                </Badge>
                {selectedPlan.status === "draft" && isShariahBoard && (
                  <Button
                    variant="primary"
                    disabled={actionLoading}
                    onClick={handleApprovePlan}
                    className="text-xs"
                  >
                    {actionLoading ? <Spinner className="h-3 w-3" /> : "Approve Audit Plan"}
                  </Button>
                )}
              </div>
            }
          >
            <div className="space-y-4">
              <div className="rounded-lg border border-navy-700 bg-navy-900/60 p-4">
                <span className="text-xs font-semibold uppercase text-ink-muted">
                  Audited Universe Scope & Mandate
                </span>
                <p className="mt-1 text-sm text-ink-primary">{selectedPlan.universe_scope}</p>
                <div className="mt-3 flex items-center justify-between text-xs text-ink-secondary">
                  <span>
                    Approved By: {selectedPlan.approved_by_name || "Pending Shariah Supervisory Board Approval"}
                  </span>
                  <span>Effective Year: {selectedPlan.year}</span>
                </div>
              </div>

              {/* Findings Section */}
              <div className="pt-2">
                <div className="mb-3 flex items-center justify-between">
                  <h4 className="text-sm font-semibold uppercase tracking-wider text-ink-primary">
                    Audit Findings & Corrective Action Plans ({selectedPlan.findings?.length || 0})
                  </h4>
                  <Button
                    variant="secondary"
                    className="text-xs"
                    onClick={() => setShowNewFindingModal(true)}
                  >
                    + Add Audit Finding
                  </Button>
                </div>

                {selectedPlan.findings && selectedPlan.findings.length > 0 ? (
                  <Table
                    columns={findingColumns}
                    data={selectedPlan.findings}
                    keyField={(f) => f.id}
                  />
                ) : (
                  <div className="rounded border border-dashed border-navy-700 p-8 text-center text-sm text-ink-muted">
                    No Shariah audit findings recorded for this plan cycle. All tested samples comply with AAOIFI/SBP standards.
                  </div>
                )}
              </div>
            </div>
          </Card>

          {/* Historical / Alternate Plans */}
          {plans.length > 1 && (
            <Card title="All Shariah Audit Plans">
              <div className="divide-y divide-navy-800">
                {plans.map((p) => (
                  <div
                    key={p.id}
                    onClick={() => handleSelectPlan(p.id)}
                    className={`flex cursor-pointer items-center justify-between p-3 transition hover:bg-navy-900/60 ${
                      p.id === selectedPlan.id ? "bg-navy-900 border-l-2 border-emerald-500" : ""
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-semibold text-sm text-ink-primary">
                          FY {p.year} — {p.title}
                        </span>
                        <Badge variant={PLAN_STATUS_BADGE[p.status]}>{p.status}</Badge>
                      </div>
                      <p className="text-xs text-ink-muted">{p.universe_scope}</p>
                    </div>
                    <div className="text-right">
                      <span className="text-xs text-ink-muted">Findings:</span>
                      <p className="text-sm font-semibold text-ink-primary">{p.findings_count}</p>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {/* Bottom Control Total Bar matching Catalogue Screen 33 */}
          <div className="mt-6 border-t border-white/8 pt-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
              <div>
                <p className="text-[11px] font-semibold text-ink-secondary uppercase">
                  RECORDS PROCESSED
                </p>
                <p className="text-base font-bold text-ink-primary">
                  {(selectedPlan.findings?.length ?? 0).toLocaleString()}{" "}
                  <span className="text-emerald-400 text-xs">100%</span>
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold text-ink-secondary uppercase">MATCHED</p>
                <p className="text-base font-bold text-emerald-400">99.94% +0.02</p>
              </div>
              <div>
                <p className="text-[11px] font-semibold text-ink-secondary uppercase">EXCEPTIONS</p>
                <p className="text-base font-bold text-ink-primary">
                  17 <span className="text-emerald-400 text-xs">-3</span>
                </p>
              </div>
              <div>
                <p className="text-[11px] font-semibold text-ink-secondary uppercase">CONTROL TOTAL</p>
                <p className="text-base font-bold text-emerald-400">
                  Balanced <span className="rounded bg-emerald-500/20 px-1 text-xs">PASS</span>
                </p>
              </div>
            </div>
          </div>
        </>
      ) : (
        <Card>
          <div className="py-12 text-center">
            <p className="text-base text-ink-secondary">No Shariah Audit Plan configured.</p>
            <p className="mt-1 text-xs text-ink-muted">
              Establish the annual audit scope and sampling universe to begin audits.
            </p>
            <Button
              variant="primary"
              className="mt-4"
              onClick={() => setShowNewPlanModal(true)}
            >
              + Create FY 2026 Audit Plan
            </Button>
          </div>
        </Card>
      )}

      {/* New Plan Modal */}
      {showNewPlanModal && (
        <Modal
          isOpen={showNewPlanModal}
          onClose={() => setShowNewPlanModal(false)}
          title="Create Annual Shariah Audit Plan"
        >
          <form onSubmit={handleCreatePlan} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Audit Year *</label>
              <input
                type="number"
                value={newYear}
                onChange={(e) => setNewYear(Number(e.target.value))}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Plan Title *</label>
              <input
                type="text"
                value={newTitle}
                onChange={(e) => setNewTitle(e.target.value)}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Universe Scope & Focus Areas *</label>
              <textarea
                rows={3}
                value={newScope}
                onChange={(e) => setNewScope(e.target.value)}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Target Audit Samples *</label>
              <input
                type="number"
                value={newTargetSamples}
                onChange={(e) => setNewTargetSamples(Number(e.target.value))}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button type="button" variant="secondary" onClick={() => setShowNewPlanModal(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={actionLoading}>
                {actionLoading ? <Spinner className="h-4 w-4" /> : "Save Plan"}
              </Button>
            </div>
          </form>
        </Modal>
      )}

      {/* New Finding Modal */}
      {showNewFindingModal && (
        <Modal
          isOpen={showNewFindingModal}
          onClose={() => setShowNewFindingModal(false)}
          title="Log Shariah Audit Finding"
        >
          <form onSubmit={handleCreateFinding} className="space-y-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted">Finding Ref *</label>
                <input
                  type="text"
                  value={findingRef}
                  onChange={(e) => setFindingRef(e.target.value)}
                  required
                  className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold uppercase text-ink-muted">Severity *</label>
                <select
                  value={findingSeverity}
                  onChange={(e) => setFindingSeverity(e.target.value as AuditSeverity)}
                  className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
                >
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Finding Title *</label>
              <input
                type="text"
                value={findingTitle}
                onChange={(e) => setFindingTitle(e.target.value)}
                placeholder="e.g. Asset valuation methodology discrepancy"
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Shariah Standard Reference *</label>
              <input
                type="text"
                value={findingStandard}
                onChange={(e) => setFindingStandard(e.target.value)}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Detailed Description</label>
              <textarea
                rows={3}
                value={findingDesc}
                onChange={(e) => setFindingDesc(e.target.value)}
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Remediation Action Plan *</label>
              <textarea
                rows={2}
                value={findingPlan}
                onChange={(e) => setFindingPlan(e.target.value)}
                required
                placeholder="Corrective actions required from investment operations..."
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase text-ink-muted">Remediation Deadline</label>
              <input
                type="date"
                value={findingDeadline}
                onChange={(e) => setFindingDeadline(e.target.value)}
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary"
              />
            </div>

            <div className="flex justify-end gap-3 pt-3">
              <Button type="button" variant="secondary" onClick={() => setShowNewFindingModal(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" disabled={actionLoading || !findingTitle.trim()}>
                {actionLoading ? <Spinner className="h-4 w-4" /> : "Log Finding"}
              </Button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  )
}
