import { useEffect, useState, type FormEvent } from "react"
import { Link, useParams } from "react-router-dom"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { Card } from "../../components/Card"
import { PageHeader } from "../../components/PageHeader"
import { Spinner } from "../../components/Spinner"
import { useAuth } from "../../api/auth"
import {
  decideQuarantine,
  dismissException,
  fetchExceptionCase,
  quarantineValue,
  resolveException,
  setTreatmentPlan,
  startInvestigation,
} from "../../api/governance"
import { extractErrorMessage } from "../../api/errors"
import type { BadgeVariant, ExceptionCase } from "../../types"

type PageState = "loading" | "loaded" | "error"

const STATUS_BADGE: Record<string, BadgeVariant> = {
  open: "gold",
  investigating: "gold",
  resolved: "emerald",
  dismissed: "navy",
}

function statusBadgeVariant(status: string): BadgeVariant {
  return STATUS_BADGE[status] ?? "neutral"
}

const SEVERITY_BADGE: Record<string, BadgeVariant> = {
  low: "neutral",
  medium: "gold",
  high: "gold",
  critical: "navy",
}

function severityBadgeVariant(severity: string): BadgeVariant {
  return SEVERITY_BADGE[severity] ?? "neutral"
}

type StageDecision = "completed" | "in_review" | "blocked" | "pending"

const STAGE_DECISION_BADGE: Record<StageDecision, BadgeVariant> = {
  completed: "emerald",
  in_review: "gold",
  blocked: "navy",
  pending: "neutral",
}

const STAGE_DECISION_LABEL: Record<StageDecision, string> = {
  completed: "Completed",
  in_review: "In Review",
  blocked: "Blocked",
  pending: "Pending",
}

interface Stage {
  key: string
  label: string
  decision: StageDecision
  detail: string | null
}

function buildStages(exceptionCase: ExceptionCase): Stage[] {
  const isClosed = exceptionCase.status === "resolved" || exceptionCase.status === "dismissed"
  const isDismissed = exceptionCase.status === "dismissed"

  const quarantine: Stage = {
    key: "quarantine",
    label: "Quarantine",
    decision: "completed",
    detail: `Detected by ${exceptionCase.detected_by}`,
  }

  const investigation: Stage = {
    key: "investigation",
    label: "Investigation",
    decision: exceptionCase.investigation_notes
      ? "completed"
      : exceptionCase.status === "open"
        ? "pending"
        : "in_review",
    detail: exceptionCase.investigation_notes,
  }

  const treatment: Stage = {
    key: "treatment",
    label: "Treatment Plan",
    decision: exceptionCase.treatment_plan
      ? "completed"
      : exceptionCase.investigation_notes
        ? "in_review"
        : "pending",
    detail: exceptionCase.treatment_plan,
  }

  const resolution: Stage = {
    key: "resolution",
    label: "Resolve / Dismiss",
    decision: isClosed ? (isDismissed ? "blocked" : "completed") : "pending",
    detail: exceptionCase.resolution_notes,
  }

  return [quarantine, investigation, treatment, resolution]
}

const TREATMENTS: Record<string, string> = {
  release_to_pool: "Release to the pool (no non-compliance found)",
  purify: "Purify: route to charity",
  return_to_source: "Return to the source",
  write_off: "Write off at the bank's cost",
}

/** Value held while a case is investigated (BRD 8: classify, quarantine value, investigate, decide treatment, disclose). */
function QuarantineCard({
  exceptionCase,
  canQuarantine,
  isBoard,
  onUpdated,
  onError,
}: {
  exceptionCase: ExceptionCase
  canQuarantine: boolean
  isBoard: boolean
  onUpdated: (updated: ExceptionCase) => void
  onError: (error: string) => void
}) {
  const [amount, setAmount] = useState("")
  const [reason, setReason] = useState("")
  const [treatment, setTreatment] = useState("")
  const [note, setNote] = useState("")
  const [busy, setBusy] = useState(false)

  async function run(action: () => Promise<ExceptionCase>) {
    setBusy(true)
    try {
      onUpdated(await action())
    } catch (err) {
      onError(extractErrorMessage(err, "The action was refused."))
    } finally {
      setBusy(false)
    }
  }

  const status = exceptionCase.quarantine_status
  return (
    <Card title="Quarantined value" className="mb-6">
      {status === "none" && canQuarantine && (
        <form
          className="grid grid-cols-1 gap-3 sm:grid-cols-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault()
            void run(() => quarantineValue(exceptionCase.id, amount, reason))
          }}
        >
          <label className={labelClasses}>
            Amount to hold (PKR)
            <input required type="number" min="0.01" step="0.01" value={amount} onChange={(e) => setAmount(e.target.value)} className={inputClasses} />
          </label>
          <label className={`${labelClasses} sm:col-span-2`}>
            What is held and why
            <input required value={reason} onChange={(e) => setReason(e.target.value)} className={inputClasses} />
          </label>
          <div className="sm:col-span-3">
            <Button type="submit" disabled={busy}>
              Quarantine this value
            </Button>
            <span className="ml-3 text-xs text-ink-secondary">The case cannot close until the Shariah Board decides what happens to it.</span>
          </div>
        </form>
      )}

      {status !== "none" && (
        <div className="space-y-2 text-sm text-ink-primary">
          <p>
            <span className="font-semibold">PKR {Number(exceptionCase.quarantined_amount ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}</span> held: {exceptionCase.quarantine_reason}
          </p>
          {status === "held" && <Badge variant="gold">Treatment not decided yet</Badge>}
          {status === "decided" && (
            <>
              <p>
                <Badge variant="emerald">Decided</Badge> {TREATMENTS[exceptionCase.quarantine_treatment] ?? exceptionCase.quarantine_treatment}
              </p>
              <p className="text-ink-secondary">Board reasoning: {exceptionCase.treatment_note}</p>
            </>
          )}
          {exceptionCase.disclosure_note && <p className="text-ink-secondary">Disclosure: {exceptionCase.disclosure_note}</p>}
        </div>
      )}

      {status === "held" && isBoard && (
        <form
          className="mt-4 grid grid-cols-1 gap-3 border-t border-white/8 pt-4 sm:grid-cols-3"
          onSubmit={(e: FormEvent) => {
            e.preventDefault()
            void run(() => decideQuarantine(exceptionCase.id, treatment, note))
          }}
        >
          <label className={labelClasses}>
            Treatment
            <select required value={treatment} onChange={(e) => setTreatment(e.target.value)} className={inputClasses}>
              <option value="">Choose a treatment</option>
              {Object.entries(TREATMENTS).map(([key, label]) => (
                <option key={key} value={key}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className={`${labelClasses} sm:col-span-2`}>
            Reasoning
            <input required value={note} onChange={(e) => setNote(e.target.value)} className={inputClasses} />
          </label>
          <div className="sm:col-span-3">
            <Button type="submit" disabled={busy}>
              Record the Board&apos;s decision
            </Button>
          </div>
        </form>
      )}
    </Card>
  )
}

export function ExceptionCaseDetail() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuth()
  const canAct = user?.role === "risk_compliance"
  const canQuarantine = user?.role === "risk_compliance" || user?.role === "shariah_secretariat" || user?.role === "shariah_board"
  const isBoard = user?.role === "shariah_board"

  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [exceptionCase, setExceptionCase] = useState<ExceptionCase | null>(null)
  const [actionError, setActionError] = useState("")

  function loadCase() {
    if (!id) return
    setPageState("loading")
    setPageError("")
    fetchExceptionCase(id)
      .then((data) => {
        setExceptionCase(data)
        setPageState("loaded")
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load this exception case."))
        setPageState("error")
      })
  }

  useEffect(() => {
    loadCase()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  function handleUpdated(updated: ExceptionCase) {
    setExceptionCase(updated)
    setActionError("")
  }

  if (pageState === "loading") {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading exception case...</span>
      </div>
    )
  }

  if (pageState === "error" || !exceptionCase) {
    return (
      <Card>
        <p className="text-sm text-red-400">{pageError || "Exception case not found."}</p>
      </Card>
    )
  }

  return (
    <div>
      <PageHeader
        title={exceptionCase.title}
        subtitle={`Source: ${exceptionCase.source_module}${exceptionCase.pool ? ` — Pool ${exceptionCase.pool}` : ""}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant={severityBadgeVariant(exceptionCase.severity)}>{exceptionCase.severity}</Badge>
            <Badge variant={statusBadgeVariant(exceptionCase.status)}>{exceptionCase.status}</Badge>
          </div>
        }
      />

      <div className="mb-4">
        <Link to="/risk-compliance" className="text-sm text-emerald-400 hover:text-emerald-300">
          ← Back to Exception Queue
        </Link>
      </div>

      <Card title="Description" className="mb-6">
        <p className="text-sm text-ink-primary">{exceptionCase.description}</p>
      </Card>

      <Card title="Quarantine, Investigation & Treatment" className="mb-6">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {buildStages(exceptionCase).map((stage) => (
            <div key={stage.key} className="rounded-lg border border-white/8 bg-navy-900 p-4">
              <p className="text-xs font-semibold tracking-wide text-ink-secondary uppercase">{stage.label}</p>
              <div className="mt-2">
                <Badge variant={STAGE_DECISION_BADGE[stage.decision]}>{STAGE_DECISION_LABEL[stage.decision]}</Badge>
              </div>
              <p className="mt-3 whitespace-pre-wrap text-sm text-ink-primary">{stage.detail ?? "—"}</p>
            </div>
          ))}
        </div>
      </Card>

      {actionError && <p className="mb-4 text-sm text-red-400">{actionError}</p>}

      {(exceptionCase.quarantine_status !== "none" || (canQuarantine && !(exceptionCase.status === "resolved" || exceptionCase.status === "dismissed"))) && (
        <QuarantineCard
          exceptionCase={exceptionCase}
          canQuarantine={canQuarantine}
          isBoard={isBoard}
          onUpdated={handleUpdated}
          onError={setActionError}
        />
      )}

      {canAct && exceptionCase.status === "open" && (
        <Card title="Start Investigation" className="mb-6">
          <InvestigationForm exceptionCase={exceptionCase} onUpdated={handleUpdated} onError={setActionError} />
        </Card>
      )}

      {canAct && exceptionCase.status === "investigating" && !exceptionCase.treatment_plan && (
        <Card title="Set Treatment Plan" className="mb-6">
          <TreatmentForm exceptionCase={exceptionCase} onUpdated={handleUpdated} onError={setActionError} />
        </Card>
      )}

      {canAct && exceptionCase.status === "investigating" && (
        <Card title="Resolve or Dismiss" className="mb-6">
          <ResolveDismissForm exceptionCase={exceptionCase} onUpdated={handleUpdated} onError={setActionError} />
        </Card>
      )}

      {exceptionCase.status === "resolved" && (
        <Card title="Resolution" className="mb-6">
          <p className="text-sm text-ink-primary">{exceptionCase.resolution_notes}</p>
        </Card>
      )}

      {exceptionCase.status === "dismissed" && (
        <Card title="Dismissal Reason" className="mb-6">
          <p className="text-sm text-ink-primary">{exceptionCase.resolution_notes}</p>
        </Card>
      )}
    </div>
  )
}

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

function InvestigationForm({
  exceptionCase,
  onUpdated,
  onError,
}: {
  exceptionCase: ExceptionCase
  onUpdated: (updated: ExceptionCase) => void
  onError: (error: string) => void
}) {
  const [notes, setNotes] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!notes.trim()) {
      setError("Investigation notes are required.")
      return
    }
    setError("")
    setIsSubmitting(true)
    try {
      const updated = await startInvestigation(exceptionCase.id, notes)
      onUpdated(updated)
    } catch (err) {
      const message = extractErrorMessage(err, "Unable to start investigation.")
      setError(message)
      onError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="investigation-notes" className={labelClasses}>
          Investigation Notes
        </label>
        <textarea
          id="investigation-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          required
          rows={4}
          className={inputClasses}
        />
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}
      <Button type="submit" variant="primary" disabled={isSubmitting}>
        {isSubmitting ? <Spinner className="h-4 w-4" /> : "Start Investigation"}
      </Button>
    </form>
  )
}

function TreatmentForm({
  exceptionCase,
  onUpdated,
  onError,
}: {
  exceptionCase: ExceptionCase
  onUpdated: (updated: ExceptionCase) => void
  onError: (error: string) => void
}) {
  const [plan, setPlan] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!plan.trim()) {
      setError("Treatment plan is required.")
      return
    }
    setError("")
    setIsSubmitting(true)
    try {
      const updated = await setTreatmentPlan(exceptionCase.id, plan)
      onUpdated(updated)
    } catch (err) {
      const message = extractErrorMessage(err, "Unable to set treatment plan.")
      setError(message)
      onError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="treatment-plan" className={labelClasses}>
          Treatment Plan
        </label>
        <textarea
          id="treatment-plan"
          value={plan}
          onChange={(e) => setPlan(e.target.value)}
          required
          rows={4}
          className={inputClasses}
        />
      </div>
      {error && <p className="text-sm text-red-400">{error}</p>}
      <Button type="submit" variant="primary" disabled={isSubmitting}>
        {isSubmitting ? <Spinner className="h-4 w-4" /> : "Set Treatment Plan"}
      </Button>
    </form>
  )
}

function ResolveDismissForm({
  exceptionCase,
  onUpdated,
  onError,
}: {
  exceptionCase: ExceptionCase
  onUpdated: (updated: ExceptionCase) => void
  onError: (error: string) => void
}) {
  const [notes, setNotes] = useState("")
  const [disclosure, setDisclosure] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(mode: "resolve" | "dismiss") {
    if (!notes.trim()) {
      setError("Notes are required.")
      return
    }
    setError("")
    setIsSubmitting(true)
    try {
      const updated =
        mode === "resolve"
          ? await resolveException(exceptionCase.id, notes, disclosure)
          : await dismissException(exceptionCase.id, notes, disclosure)
      onUpdated(updated)
    } catch (err) {
      const message = extractErrorMessage(err, `Unable to ${mode} this exception.`)
      setError(message)
      onError(message)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <label htmlFor="resolution-notes" className={labelClasses}>
          Notes
        </label>
        <textarea
          id="resolution-notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          rows={4}
          className={inputClasses}
        />
      </div>
      {exceptionCase.quarantine_status === "decided" && (
        <div>
          <label htmlFor="disclosure-note" className={labelClasses}>
            Disclosure of the treatment of the held value
          </label>
          <textarea
            id="disclosure-note"
            value={disclosure}
            onChange={(e) => setDisclosure(e.target.value)}
            rows={2}
            className={inputClasses}
            placeholder="Where and how the treatment is disclosed (report, note or notice)"
          />
        </div>
      )}
      {error && <p className="text-sm text-red-400">{error}</p>}
      <div className="flex gap-2">
        <Button type="button" variant="primary" disabled={isSubmitting} onClick={() => handleSubmit("resolve")}>
          {isSubmitting ? <Spinner className="h-4 w-4" /> : "Resolve"}
        </Button>
        <Button type="button" variant="outline" disabled={isSubmitting} onClick={() => handleSubmit("dismiss")}>
          Dismiss
        </Button>
      </div>
    </div>
  )
}
