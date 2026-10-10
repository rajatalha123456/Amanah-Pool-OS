import { useEffect, useState, type FormEvent } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { fetchAllocationRunDetail, restateRun } from "../api/allocationRuns"
import { extractErrorMessage } from "../api/errors"
import type { AllocationRun } from "../types"

const RESTATEMENT_REASONS = [
  "Data Source Error (Late CBS feed adjustments)",
  "Shariah Audit Directive / Non-Compliant Asset Exclusion",
  "Weightage Matrix Indexing Discrepancy",
  "Regulatory Examination Finding (SBP / Central Bank)",
  "System Calculation Anomaly / Rate Correction",
  "Other Exceptional Fiqh Reason",
]

export function RestatementWizard() {
  const params = useParams<{ runId?: string; id?: string }>()
  const runId = params.runId || params.id
  const navigate = useNavigate()

  const [run, setRun] = useState<AllocationRun | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [reasonCategory, setReasonCategory] = useState(RESTATEMENT_REASONS[0])
  const [detailedNotes, setDetailedNotes] = useState("")
  const [revisedGrossIncome, setRevisedGrossIncome] = useState<string>("")
  const [revisedExpenses, setRevisedExpenses] = useState<string>("0.00")
  const [confirmedShariah, setConfirmedShariah] = useState(false)
  const [confirmedContra, setConfirmedContra] = useState(false)

  const [submitting, setSubmitting] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [result, setResult] = useState<{
    original_run: AllocationRun
    draft_rerun: AllocationRun
    message: string
  } | null>(null)

  useEffect(() => {
    if (!runId) return
    setLoading(true)
    fetchAllocationRunDetail(runId)
      .then((data) => {
        setRun(data)
        setRevisedGrossIncome(data.gross_income || data.distributable_amount || "5000000.00")
        setRevisedExpenses(data.direct_expenses || "0.00")
        setLoading(false)
      })
      .catch((err) => {
        setError(extractErrorMessage(err))
        setLoading(false)
      })
  }, [runId])

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!runId || !confirmedShariah || !confirmedContra) return

    setSubmitting(true)
    setSubmitError(null)

    const fullReason = `[${reasonCategory}] ${detailedNotes.trim()}`

    try {
      const res = await restateRun(runId, {
        restatement_reason: fullReason,
        notes: detailedNotes,
        gross_income: revisedGrossIncome || undefined,
        direct_expenses: revisedExpenses || undefined,
      })
      setResult({
        original_run: run!,
        draft_rerun: res,
        message: "Restatement rerun created and sent for maker-checker approval.",
      })
    } catch (err) {
      setSubmitError(extractErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading allocation run for restatement...</span>
      </div>
    )
  }

  if (error || !run) {
    return (
      <Card>
        <p className="text-sm text-red-400">{error || "Allocation run not found"}</p>
        <Button variant="secondary" className="mt-4" onClick={() => navigate(-1)}>
          Go Back
        </Button>
      </Card>
    )
  }

  if (result) {
    return (
      <div className="space-y-6">
        <PageHeader
          title="Restatement Submitted"
          subtitle={`Run #${run.id.slice(0, 8)} will be reversed once the rerun is approved`}
          actions={<Badge variant="emerald">Rerun Created</Badge>}
        />

        <Card title="Restatement Execution Summary">
          <div className="space-y-4">
            <div className="rounded-md border border-emerald-500/30 bg-emerald-950/20 p-4 text-sm text-emerald-300">
              <p className="font-semibold">{result.message}</p>
              <p className="mt-1 text-xs text-ink-secondary">
                A linked restatement rerun has been created. The original run stays signed; its GL impact
                is reversed by a contra Journal Batch automatically when the rerun is approved.
              </p>
            </div>

            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
              <div className="rounded-lg border border-navy-700 bg-navy-900/50 p-4">
                <span className="text-xs uppercase tracking-wider text-ink-muted">Original Run</span>
                <p className="mt-1 text-base font-semibold text-ink-primary">Run #{result.original_run.id.slice(0, 8)}</p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant="navy">Status: {result.original_run.status}</Badge>
                </div>
              </div>

              <div className="rounded-lg border border-gold-500/40 bg-navy-900/50 p-4">
                <span className="text-xs uppercase tracking-wider text-gold-400">New Restatement Rerun (Draft)</span>
                <p className="mt-1 text-base font-semibold text-ink-primary">Run #{result.draft_rerun.id.slice(0, 8)}</p>
                <div className="mt-2 flex items-center gap-2">
                  <Badge variant="gold">Status: {result.draft_rerun.status}</Badge>
                  <span className="text-xs text-ink-secondary">Linked to original run</span>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-3 pt-4">
              <Button
                variant="primary"
                onClick={() => navigate(`/allocation-runs/${result.draft_rerun.id}`)}
              >
                Open Draft Restatement Rerun
              </Button>
              <Button
                variant="secondary"
                onClick={() => navigate(`/allocation-runs/${run.id}`)}
              >
                View Reversal Journal Entries
              </Button>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader
        screenNumber="17"
        title="Restatement Wizard"
        subtitle={`Controlled Correction for Certified Run #${run.id.slice(0, 8)} (${run.value_date})`}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="emerald">Original Status: {run.status}</Badge>
            <Link to={`/allocation-runs/${run.id}`}>
              <Button variant="secondary" className="text-xs">
                Back to Run
              </Button>
            </Link>
          </div>
        }
      />

      {/* Shariah Audit Trail Banner */}
      <div className="rounded-lg border border-amber-500/40 bg-amber-950/20 p-4 text-amber-200">
        <div className="flex items-start gap-3">
          <span className="mt-0.5 text-lg font-bold">⚠️</span>
          <div>
            <h4 className="font-semibold text-amber-300">
              BR-004 Shariah Immutable Governance & Controlled Reversal
            </h4>
            <p className="mt-1 text-sm text-ink-secondary">
              Certified and signed profit allocation runs cannot be deleted or directly edited.
              Executing this wizard creates a linked Restatement Rerun in <strong className="text-ink-primary">SIMULATED</strong> status.
              The current run stays <strong className="text-ink-primary">SIGNED</strong> until the rerun is approved by an independent
              checker; approval then reverses the original (full contra-journal and reserve movements) and signs the rerun.
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard label="Distributable Amount" value={run.distributable_amount} deltaTone="neutral" />
        <StatCard label="Mudarib Share" value={run.mudarib_share} deltaTone="neutral" />
        <StatCard label="Depositor Pool Share" value={run.depositor_pool_share} deltaTone="neutral" />
        <StatCard label="Value Date" value={run.value_date} deltaTone="neutral" />
      </div>

      <Card title="Restatement Reason & Audit Justification">
        <form onSubmit={handleSubmit} className="space-y-5">
          {submitError && (
            <div className="rounded border border-red-500/30 bg-red-950/30 p-3 text-sm text-red-400">
              {submitError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Primary Restatement Reason *
            </label>
            <select
              value={reasonCategory}
              onChange={(e) => setReasonCategory(e.target.value)}
              className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
            >
              {RESTATEMENT_REASONS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 rounded-lg border border-white/5 bg-navy-900/40 p-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Adjusted Gross Income (PKR) *
              </label>
              <input
                type="number"
                step="0.01"
                value={revisedGrossIncome}
                onChange={(e) => setRevisedGrossIncome(e.target.value)}
                required
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary font-mono focus:border-emerald-500 focus:outline-none"
              />
              <span className="text-[10px] text-ink-muted mt-1 block">
                Original run value: PKR {run.gross_income || run.distributable_amount}
              </span>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
                Adjusted Direct Expenses (PKR)
              </label>
              <input
                type="number"
                step="0.01"
                value={revisedExpenses}
                onChange={(e) => setRevisedExpenses(e.target.value)}
                className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary font-mono focus:border-emerald-500 focus:outline-none"
              />
              <span className="text-[10px] text-ink-muted mt-1 block">
                Original expenses: PKR {run.direct_expenses || "0.00"}
              </span>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
              Detailed Audit Justification & Remediation Notes *
            </label>
            <textarea
              rows={4}
              value={detailedNotes}
              onChange={(e) => setDetailedNotes(e.target.value)}
              placeholder="Specify the exact root cause, affected depositor tiers, corrective parameters, and regulatory notification ref..."
              required
              className="mt-1 w-full rounded border border-navy-700 bg-navy-900 px-3 py-2 text-sm text-ink-primary placeholder-ink-muted focus:border-emerald-500 focus:outline-none"
            />
          </div>

          <div className="rounded-lg border border-navy-700 bg-navy-900/60 p-4 space-y-3">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-primary">
              Pre-Restatement Dual Authorization Gate
            </h4>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={confirmedShariah}
                onChange={(e) => setConfirmedShariah(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-navy-700 text-emerald-600 focus:ring-emerald-500"
              />
              <span className="text-xs text-ink-secondary">
                I verify that this restatement has been reviewed by the Shariah Compliance Officer or Resident Shariah Board Member, and meets AAOIFI / SBP restatement guidelines.
              </span>
            </label>
            <label className="flex items-start gap-3 cursor-pointer">
              <input
                type="checkbox"
                checked={confirmedContra}
                onChange={(e) => setConfirmedContra(e.target.checked)}
                className="mt-1 h-4 w-4 rounded border-navy-700 text-emerald-600 focus:ring-emerald-500"
              />
              <span className="text-xs text-ink-secondary">
                I acknowledge that reversing contra-journal entries will be posted immediately with immutable audit metadata, and cannot be revoked.
              </span>
            </label>
          </div>

          <div className="flex items-center justify-end gap-3 pt-2">
            <Button type="button" variant="secondary" onClick={() => navigate(-1)}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={submitting || !confirmedShariah || !confirmedContra || !detailedNotes.trim()}
            >
              {submitting ? (
                <span className="flex items-center gap-2">
                  <Spinner className="h-4 w-4" /> Generating Contra & Spawning Rerun...
                </span>
              ) : (
                "Authorize Restatement & Spawn Draft Rerun"
              )}
            </Button>
          </div>
        </form>
      </Card>
    </div>
  )
}
