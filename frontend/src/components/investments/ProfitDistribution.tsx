import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Card } from "../Card"
import { Spinner } from "../Spinner"
import { useAuth } from "../../api/auth"
import { extractErrorMessage } from "../../api/errors"
import {
  approveDistributionRun,
  checkDistributionRun,
  shariahSignOffDistributionRun,
  createDistributionRun,
  fetchCapitalAccounts,
  fetchCapitalStatement,
  fetchDistributionRuns,
  rejectDistributionRun,
  restateDistributionRun,
  simulateDistribution,
  submitDistributionRun,
} from "../../api/investments"
import type {
  BadgeVariant,
  CapitalAccount,
  CapitalStatement,
  DistributionInput,
  DistributionRun,
  DistributionSimulation,
} from "../../types"

const STATUS_BADGE: Record<string, BadgeVariant> = {
  simulated: "neutral",
  pending_approval: "gold",
  checked: "gold",
  shariah_review: "gold",
  signed: "emerald",
  rejected: "neutral",
  reversed: "navy",
}

const money = (value: string | number) =>
  `PKR ${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2 })}`

const input =
  "rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

/** Investor view: their own capital-account statements only (the API scopes the accounts). */
function InvestorStatements({ poolId }: { poolId: string }) {
  const [accounts, setAccounts] = useState<CapitalAccount[]>([])
  const [statements, setStatements] = useState<CapitalStatement[]>([])
  const [error, setError] = useState("")

  useEffect(() => {
    const today = new Date()
    const to = today.toISOString().split("T")[0]
    const from = new Date(today.getFullYear(), today.getMonth() - 1, 1).toISOString().split("T")[0]
    fetchCapitalAccounts(poolId)
      .then(async (list) => {
        setAccounts(list)
        setStatements(await Promise.all(list.map((a) => fetchCapitalStatement(a.id, from, to))))
      })
      .catch((err) => setError(extractErrorMessage(err, "Unable to load your statement.")))
  }, [poolId])

  if (error) return <p className="text-sm text-red-400">{error}</p>
  if (accounts.length === 0) return <p className="text-sm text-ink-secondary">You have no capital account in this pool.</p>

  return (
    <div className="space-y-4">
      {statements.map((st) => (
        <Card key={st.capital_account} title={`${st.investor_name} — ${st.pool}`}>
          <p className="mb-3 text-xs text-ink-secondary">
            Statement {st.period_start} to {st.period_end}
          </p>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-3">
            {(
              [
                ["Opening units", st.opening_units],
                ["Closing units", st.closing_units],
                ["Average units (profit basis)", st.average_units],
                ["NAV per unit", st.nav_per_unit ?? "—"],
                ["Market value", st.market_value ? money(st.market_value) : "—"],
                ["Profit distributed", money(st.total_profit_distributed)],
              ] as Array<[string, string]>
            ).map(([label, value]) => (
              <div key={label}>
                <dt className="text-xs text-ink-secondary">{label}</dt>
                <dd className="font-mono text-ink-primary">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>
      ))}
    </div>
  )
}

/**
 * Mudarabah profit distribution (BRD 6.4 / 7.1): the manager takes its approved PSR share of
 * profit, investors share the rest by time-weighted units, a loss falls on investors only.
 * Maker drafts; an independent finance checker checks; the Shariah Secretariat or Board reviews; the authorized
 * signatory releases (three different people). Signed runs are corrected by restatement.
 */
export function ProfitDistribution({ poolId }: { poolId: string }) {
  const { user } = useAuth()
  const role = user?.role ?? ""
  const canDraft = role === "pool_manager" || role === "finance_maker"
  const canSubmit = role === "finance_maker"
  const canCheck = role === "finance_checker"
  const canShariah = role === "shariah_secretariat" || role === "shariah_board"
  const canRelease = role === "authorized_signatory"
  const canReject = canCheck || canShariah || canRelease

  const [runs, setRuns] = useState<DistributionRun[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState<DistributionInput>({
    pool: poolId, period_start: "", period_end: "", gross_income: "", direct_expenses: "0",
  })
  const [preview, setPreview] = useState<DistributionSimulation | null>(null)
  const [openRun, setOpenRun] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setRuns(await fetchDistributionRuns(poolId))
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load distribution runs."))
    } finally {
      setLoading(false)
    }
  }, [poolId])

  useEffect(() => {
    setForm((f) => ({ ...f, pool: poolId }))
    setPreview(null)
    void load()
  }, [poolId, load])

  async function act(action: () => Promise<unknown>) {
    setBusy(true)
    setError("")
    try {
      await action()
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "The action failed."))
    } finally {
      setBusy(false)
    }
  }

  if (role === "investor_member") return <InvestorStatements poolId={poolId} />

  return (
    <div className="space-y-6">
      {error && <p className="rounded-md border border-red-500/30 bg-red-950/20 p-3 text-sm text-red-300">{error}</p>}

      {canDraft && (
        <Card title="New profit distribution">
          <form
            className="flex flex-wrap items-end gap-3"
            onSubmit={(event: FormEvent) => {
              event.preventDefault()
              void act(async () => setPreview(await simulateDistribution(form)))
            }}
          >
            <label className="text-xs text-ink-secondary">
              Period start
              <input type="date" required className={`mt-1 block ${input}`} value={form.period_start}
                onChange={(e) => setForm({ ...form, period_start: e.target.value })} />
            </label>
            <label className="text-xs text-ink-secondary">
              Period end
              <input type="date" required className={`mt-1 block ${input}`} value={form.period_end}
                onChange={(e) => setForm({ ...form, period_end: e.target.value })} />
            </label>
            <label className="text-xs text-ink-secondary">
              Gross income (PKR)
              <input type="number" step="0.01" required className={`mt-1 block ${input}`} value={form.gross_income}
                onChange={(e) => setForm({ ...form, gross_income: e.target.value })} />
            </label>
            <label className="text-xs text-ink-secondary">
              Direct expenses (PKR)
              <input type="number" step="0.01" className={`mt-1 block ${input}`} value={form.direct_expenses}
                onChange={(e) => setForm({ ...form, direct_expenses: e.target.value })} />
            </label>
            <Button type="submit" variant="secondary" disabled={busy}>
              Simulate
            </Button>
            {preview && (
              <Button
                type="button"
                variant="primary"
                disabled={busy}
                onClick={() => void act(async () => { await createDistributionRun(form); setPreview(null) })}
              >
                Save as draft run
              </Button>
            )}
          </form>

          {preview && (
            <div className="mt-5 space-y-3 text-sm">
              <p className="text-ink-secondary">
                {preview.is_loss
                  ? "Loss: borne by investors pro-rata to units; the manager bears no capital loss."
                  : `Manager share ${money(preview.manager_share)} · investors ${money(preview.investor_share)}`}
                {" · rounding residual "}
                {money(preview.rounding_residual)}
              </p>
              <table className="w-full text-left text-xs">
                <thead className="border-b border-white/8 text-[11px] uppercase text-ink-muted">
                  <tr>
                    <th className="px-3 py-2">Investor</th>
                    <th className="px-3 py-2">Average units</th>
                    <th className="px-3 py-2">Share</th>
                    <th className="px-3 py-2 text-right">Amount</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {preview.lines.map((l) => (
                    <tr key={l.capital_account_id}>
                      <td className="px-3 py-2 text-ink-primary">{l.investor_name} <span className="font-mono text-ink-muted">{l.investor_reference}</span></td>
                      <td className="px-3 py-2 font-mono">{l.average_units}</td>
                      <td className="px-3 py-2 font-mono">{(Number(l.share_ratio) * 100).toFixed(4)}%</td>
                      <td className="px-3 py-2 text-right font-mono">{money(l.allocated_amount)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      )}

      <Card title="Distribution runs">
        {loading ? (
          <div className="flex items-center gap-2 py-6 text-ink-secondary">
            <Spinner /> <span className="text-sm">Loading...</span>
          </div>
        ) : runs.length === 0 ? (
          <p className="text-sm text-ink-secondary">No distribution runs yet.</p>
        ) : (
          <div className="space-y-3">
            {runs.map((run) => (
              <div key={run.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <button type="button" className="text-left" onClick={() => setOpenRun(openRun === run.id ? null : run.id)}>
                    <p className="font-semibold text-ink-primary">
                      {run.period_start} → {run.period_end}
                      {run.is_restatement && <span className="ml-2 text-xs text-amber-300">restatement</span>}
                    </p>
                    <p className="text-xs text-ink-secondary">
                      Result {money(run.distributable_amount)} · manager {money(run.manager_share)} · investors {money(run.investor_share)}
                    </p>
                  </button>
                  <div className="flex items-center gap-2">
                    <Badge variant={STATUS_BADGE[run.status] ?? "neutral"}>{run.status}</Badge>
                    {canSubmit && run.status === "simulated" && (
                      <Button size="sm" variant="primary" disabled={busy} onClick={() => void act(() => submitDistributionRun(run.id))}>
                        Submit for checking
                      </Button>
                    )}
                    {canCheck && run.status === "pending_approval" && (
                      <Button size="sm" variant="primary" disabled={busy} onClick={() => void act(() => checkDistributionRun(run.id))}>
                        Independent check
                      </Button>
                    )}
                    {canShariah && run.status === "checked" && (
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={busy}
                        onClick={() => {
                          const note = window.prompt("Shariah review note (what was reviewed)") ?? ""
                          void act(() => shariahSignOffDistributionRun(run.id, note))
                        }}
                      >
                        Shariah review
                      </Button>
                    )}
                    {canRelease && run.status === "shariah_review" && (
                      <Button size="sm" variant="primary" disabled={busy} onClick={() => void act(() => approveDistributionRun(run.id))}>
                        Release
                      </Button>
                    )}
                    {canReject && ["pending_approval", "checked", "shariah_review"].includes(run.status) && (
                      <>
                        <Button
                          size="sm"
                          variant="secondary"
                          disabled={busy}
                          onClick={() => {
                            const reason = window.prompt("Reason for rejecting this run?")
                            if (reason) void act(() => rejectDistributionRun(run.id, reason))
                          }}
                        >
                          Reject
                        </Button>
                      </>
                    )}
                    {canDraft && run.status === "signed" && (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => {
                          const reason = window.prompt("Reason for restating this signed run?")
                          if (reason) void act(() => restateDistributionRun(run.id, reason))
                        }}
                      >
                        Restate
                      </Button>
                    )}
                  </div>
                </div>

                {openRun === run.id && (
                  <div className="mt-4 space-y-2 text-xs">
                    <p className="font-mono text-ink-muted">Seal: {run.calculation_hash}</p>
                    {run.rejection_reason && <p className="text-amber-300">Rejected: {run.rejection_reason}</p>}
                    <table className="w-full text-left">
                      <thead className="border-b border-white/8 text-[11px] uppercase text-ink-muted">
                        <tr>
                          <th className="px-3 py-2">Investor</th>
                          <th className="px-3 py-2">Average units</th>
                          <th className="px-3 py-2 text-right">Amount</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-white/5">
                        {run.lines.map((l) => (
                          <tr key={l.id}>
                            <td className="px-3 py-2 text-ink-primary">{l.investor_name}</td>
                            <td className="px-3 py-2 font-mono">{l.average_units}</td>
                            <td className="px-3 py-2 text-right font-mono">{money(l.allocated_amount)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
