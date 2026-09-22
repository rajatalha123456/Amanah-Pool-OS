import { useEffect, useState, type FormEvent } from "react"
import { useParams } from "react-router-dom"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Modal } from "../components/Modal"
import { StatCard } from "../components/StatCard"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import {
  approveRun,
  fetchAllocationRunDetail,
  rejectRun,
  shariahSignOffRun,
  submitRunForChecking,
  generateStatements,
  fetchStatements,
} from "../api/allocationRuns"
import { extractErrorMessage } from "../api/errors"
import type { BadgeVariant, AllocationLine, AllocationRun, JournalEntry, DepositorStatement } from "../types"

type PageState = "loading" | "loaded" | "error"

const STATUS_BADGE: Record<string, BadgeVariant> = {
  simulated: "neutral",
  pending_approval: "gold",
  shariah_review: "gold",
  signed: "emerald",
  rejected: "navy",
}

function statusBadgeVariant(status: string): BadgeVariant {
  return STATUS_BADGE[status] ?? "neutral"
}

type StageDecision = "completed" | "approved" | "in_review" | "blocked" | "pending"

const STAGE_DECISION_BADGE: Record<StageDecision, BadgeVariant> = {
  completed: "emerald",
  approved: "emerald",
  in_review: "gold",
  blocked: "navy",
  pending: "neutral",
}

const STAGE_DECISION_LABEL: Record<StageDecision, string> = {
  completed: "Completed",
  approved: "Approved",
  in_review: "In Review",
  blocked: "Blocked",
  pending: "Pending",
}

interface TimelineStage {
  key: string
  label: string
  owner: string | null
  decision: StageDecision
  timestamp: string | null
}

function userLabel(userId: number | null): string {
  return userId !== null ? `User #${userId}` : "—"
}

function buildTimelineStages(run: AllocationRun): TimelineStage[] {
  const isRejected = run.status === "rejected"

  const prepared: TimelineStage = {
    key: "prepared",
    label: "Prepared",
    owner: userLabel(run.created_by),
    decision: "completed",
    timestamp: run.created_at,
  }

  const independentCheck: TimelineStage = {
    key: "independent-check",
    label: "Independent Check",
    owner: run.status === "simulated" ? null : userLabel(run.checked_by ?? null),
    decision:
      run.status === "simulated"
        ? "pending"
        : isRejected
          ? "blocked"
          : run.status === "pending_approval"
            ? "in_review"
            : "approved",
    timestamp: run.status === "simulated" ? null : run.checked_at,
  }

  const shariahReviewApplicable = run.shariah_review_required
  const shariahReviewDecision: StageDecision = !shariahReviewApplicable
    ? "pending"
    : isRejected
      ? "blocked"
      : run.shariah_signed_off_by !== null
        ? "approved"
        : run.status === "pending_approval"
          ? "in_review"
          : "pending"
  const shariahReview: TimelineStage = {
    key: "shariah-review",
    label: "Shariah Review",
    owner: shariahReviewApplicable && run.shariah_signed_off_by !== null ? userLabel(run.shariah_signed_off_by) : null,
    decision: shariahReviewDecision,
    timestamp: run.shariah_signed_off_at,
  }

  const finalReleaseDecision: StageDecision =
    run.status === "signed" ? "completed" : isRejected ? "blocked" : "pending"
  const finalRelease: TimelineStage = {
    key: "final-release",
    label: "Final Release",
    owner: run.status === "signed" ? userLabel(run.checked_by) : null,
    decision: finalReleaseDecision,
    timestamp: run.status === "signed" ? run.checked_at : null,
  }

  return [prepared, independentCheck, shariahReview, finalRelease]
}

export function AllocationRunDetail() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const canReject = user?.role === "finance_checker"
  const canSignOff = user?.role === "shariah_secretariat"

  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [run, setRun] = useState<AllocationRun | null>(null)

  const [actionError, setActionError] = useState("")
  const [isActionPending, setIsActionPending] = useState(false)
  const [showRejectModal, setShowRejectModal] = useState(false)
  const [showSignOffModal, setShowSignOffModal] = useState(false)

  const [statements, setStatements] = useState<DepositorStatement[]>([])
  const [isLoadingStatements, setIsLoadingStatements] = useState(false)

  function loadData() {
    if (!id) return
    setPageState("loading")
    fetchAllocationRunDetail(id)
      .then((data) => {
        setRun(data)
        setPageState("loaded")
        if (data.status === "signed") {
          fetchStatements(id)
            .then((stmts) => setStatements(stmts))
            .catch(() => setStatements([]))
        }
      })
      .catch(() => {
        setPageError("Failed to load allocation run")
        setPageState("error")
      })
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  async function runAction(action: (id: string) => Promise<AllocationRun>, fallbackMessage: string) {
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

  const lineColumns: TableColumn<AllocationLine>[] = [
    { header: "Participant Class", accessor: (line) => line.participant_class },
    { header: "Daily Funds", accessor: (line) => line.daily_funds },
    { header: "Weightage", accessor: (line) => line.weightage },
    { header: "Weighted Funds", accessor: (line) => line.weighted_funds },
    { header: "Allocated Amount", accessor: (line) => line.allocated_amount },
  ]

  const entryColumns: TableColumn<JournalEntry>[] = [
    { header: "Account", accessor: (entry) => entry.account_name },
    { header: "Type", accessor: (entry) => entry.entry_type },
    { header: "Amount", accessor: (entry) => entry.amount },
  ]

  if (pageState === "loading") {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading allocation run...</span>
      </div>
    )
  }

  if (pageState === "error" || !run || !id) {
    return (
      <Card>
        <p className="text-sm text-red-400">{pageError || "Allocation run not found"}</p>
      </Card>
    )
  }

  return (
    <div>
      <PageHeader
        title={`Allocation Run — ${run.value_date}`}
        subtitle={run.pool}
        actions={<Badge variant={statusBadgeVariant(run.status)}>{run.status}</Badge>}
      />

      {actionError && <p className="mb-4 text-sm text-red-400">{actionError}</p>}

      <Card title="Approval Timeline" className="mb-6">
        <ApprovalTimeline stages={buildTimelineStages(run)} />
      </Card>

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Distributable" value={run.distributable_amount} deltaTone="neutral" />
        <StatCard label="Total Weighted Funds" value={run.total_weighted_funds} deltaTone="neutral" />
        <StatCard label="Depositor Share" value={run.depositor_pool_share} deltaTone="neutral" />
        <StatCard label="Mudarib Share" value={run.mudarib_share} deltaTone="neutral" />
      </div>

      <Card title="Allocation by Participant Class" className="mb-6">
        <Table columns={lineColumns} data={run.lines} keyField={(line) => line.participant_class} />
      </Card>

      <Card title="Actions" className="mb-6">
        {run.status === "simulated" && (
          <Button
            variant="primary"
            disabled={isActionPending}
            onClick={() => runAction(submitRunForChecking, "Unable to submit for checking.")}
          >
            {isActionPending ? <Spinner className="h-4 w-4" /> : "Submit for Checking"}
          </Button>
        )}

        {run.status === "pending_approval" && run.shariah_review_required && (
            <div className="space-y-3">
            <p className="text-sm text-gold-400">
              Waiting for Shariah Secretariat sign-off before this run can be approved.
            </p>
              <div className="flex gap-3">
                {canSignOff && (
                  <Button
                    variant="primary"
                    disabled={isActionPending}
                    onClick={() => setShowSignOffModal(true)}
                  >
                    Shariah Sign-Off
                  </Button>
                )}
                {canReject && (
                  <Button
                    variant="secondary"
                    disabled={isActionPending}
                    onClick={() => setShowRejectModal(true)}
                  >
                    Reject
                  </Button>
                )}
              </div>
          </div>
        )}

        {run.status === "pending_approval" && !run.shariah_review_required && canReject && (
          <div className="flex gap-3">
            <Button
              variant="primary"
              disabled={isActionPending}
              onClick={() => runAction(approveRun, "Unable to approve.")}
            >
              {isActionPending ? <Spinner className="h-4 w-4" /> : "Approve"}
            </Button>
            <Button
              variant="secondary"
              disabled={isActionPending}
              onClick={() => setShowRejectModal(true)}
            >
              Reject
            </Button>
          </div>
        )}

        {run.status === "shariah_review" && canReject && (
          <div className="flex gap-3">
            <Button
              variant="primary"
              disabled={isActionPending}
              onClick={() => runAction(approveRun, "Unable to approve.")}
            >
              {isActionPending ? <Spinner className="h-4 w-4" /> : "Approve"}
            </Button>
            <Button
              variant="secondary"
              disabled={isActionPending}
              onClick={() => setShowRejectModal(true)}
            >
              Reject
            </Button>
          </div>
        )}

        {run.status === "signed" && (
          <p className="text-sm text-ink-secondary">Run has been approved and posted.</p>
        )}

        {run.status === "rejected" && (
          <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
            <p className="text-xs font-semibold uppercase text-ink-secondary">Rejection Reason</p>
            <p className="mt-2 text-sm text-ink-primary">{run.rejection_reason}</p>
          </div>
        )}
      </Card>

      {run.status === "signed" && run.journal_batch && (
        <Card title="Journal Batch" className="mb-6">
          <div className="mb-4 grid grid-cols-1 gap-2 sm:grid-cols-3">
            <div>
              <p className="text-xs font-semibold uppercase text-ink-secondary">Batch Date</p>
              <p className="text-sm text-ink-primary">{run.journal_batch.batch_date}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-ink-secondary">Total Debit</p>
              <p className="text-sm text-ink-primary">{run.journal_batch.total_debit}</p>
            </div>
            <div>
              <p className="text-xs font-semibold uppercase text-ink-secondary">Total Credit</p>
              <p className="text-sm text-ink-primary">{run.journal_batch.total_credit}</p>
            </div>
          </div>

          <div className="mt-6">
            <h3 className="mb-4 text-sm font-semibold text-ink-primary">Entries</h3>
            <Table
              columns={entryColumns}
              data={run.journal_batch.entries}
              keyField={(entry) => entry.id}
            />
          </div>
        </Card>
      )}

      {run.status === "signed" && (
        <Card title="Depositor Statements" className="mb-6">
          <div className="flex items-center justify-between mb-6">
            <p className="text-sm text-ink-secondary">
              {statements.length > 0
                ? `${statements.length} statement(s) generated`
                : "No statements generated yet"}
            </p>
            <Button
              variant="primary"
              disabled={isLoadingStatements || isActionPending}
              onClick={async () => {
                setIsLoadingStatements(true)
                try {
                  await generateStatements(id!)
                  const newStatements = await fetchStatements(id!)
                  setStatements(newStatements)
                } catch (err) {
                  setActionError(extractErrorMessage(err, "Unable to generate statements."))
                } finally {
                  setIsLoadingStatements(false)
                }
              }}
            >
              {isLoadingStatements ? <Spinner className="h-4 w-4" /> : "Generate Statements"}
            </Button>
          </div>

          {statements.length > 0 && (
            <div className="space-y-3">
              {statements.map((stmt) => (
                <div key={stmt.id} className="border border-white/8 rounded p-4 hover:bg-white/5">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="text-sm font-semibold text-ink-primary">{stmt.participant_class}</p>
                      <p className="text-xs text-ink-secondary">
                        Period: {stmt.period_start} to {stmt.period_end}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm text-emerald-400 font-medium">
                        {stmt.closing_balance}
                      </p>
                      <p className="text-xs text-ink-secondary">Closing Balance</p>
                    </div>
                  </div>
                </div>
              ))}
              <a
                href={`/statements/${id}`}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-block mt-4 px-4 py-2 text-sm font-medium text-emerald-400 border border-emerald-400/30 rounded hover:bg-white/5"
              >
                View & Print Statements
              </a>
            </div>
          )}
        </Card>
      )}

      {showRejectModal && (
        <RejectModal
          id={id}
          isSubmitting={isActionPending}
          onClose={() => setShowRejectModal(false)}
          onRejected={() => {
            setShowRejectModal(false)
            loadData()
          }}
          onError={(error) => setActionError(error)}
        />
      )}

      {showSignOffModal && (
        <ShariahSignOffModal
          id={id}
          isSubmitting={isActionPending}
          onClose={() => setShowSignOffModal(false)}
          onSignedOff={() => {
            setShowSignOffModal(false)
            loadData()
          }}
          onError={(error) => setActionError(error)}
        />
      )}
    </div>
  )
}

function ApprovalTimeline({ stages }: { stages: TimelineStage[] }) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
      {stages.map((stage) => (
        <div key={stage.key} className="rounded-lg border border-white/8 bg-navy-900 p-4">
          <p className="text-xs font-semibold tracking-wide text-ink-secondary uppercase">{stage.label}</p>
          <div className="mt-2">
            <Badge variant={STAGE_DECISION_BADGE[stage.decision]}>{STAGE_DECISION_LABEL[stage.decision]}</Badge>
          </div>
          <p className="mt-3 text-sm text-ink-primary">{stage.owner ?? "—"}</p>
          <p className="mt-1 text-xs text-ink-secondary">
            {stage.timestamp ? new Date(stage.timestamp).toLocaleString() : "—"}
          </p>
        </div>
      ))}
    </div>
  )
}

interface ShariahSignOffModalProps {
  id: string
  isSubmitting: boolean
  onClose: () => void
  onSignedOff: () => void
  onError: (error: string) => void
}

function ShariahSignOffModal({ id, isSubmitting, onClose, onSignedOff, onError }: ShariahSignOffModalProps) {
  const [note, setNote] = useState("")
  const [error, setError] = useState("")

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")
    try {
      await shariahSignOffRun(id, note)
      onSignedOff()
    } catch (err) {
      const message = extractErrorMessage(err, "Unable to record Shariah sign-off.")
      setError(message)
      onError(message)
    }
  }

  return (
    <Modal title="Shariah Sign-Off" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Note (optional)
          </label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={4}
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
            placeholder="Evidence reviewed, comments for the record..."
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Sign Off"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

interface RejectModalProps {
  id: string
  isSubmitting: boolean
  onClose: () => void
  onRejected: () => void
  onError: (error: string) => void
}

function RejectModal({ id, isSubmitting, onClose, onRejected, onError }: RejectModalProps) {
  const [reason, setReason] = useState("")
  const [error, setError] = useState("")

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")

    if (!reason.trim()) {
      setError("Rejection reason is required.")
      return
    }

    try {
      await rejectRun(id, reason)
      onRejected()
    } catch (err) {
      const message = extractErrorMessage(err, "Unable to reject.")
      setError(message)
      onError(message)
    }
  }

  return (
    <Modal title="Reject Allocation Run" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Reason (required)
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            required
            rows={4}
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
            placeholder="Explain why this allocation run is being rejected..."
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Reject"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
