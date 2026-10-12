import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Card } from "../Card"
import { useAuth } from "../../api/auth"
import { extractErrorMessage } from "../../api/errors"
import {
  acceptCircleRules,
  closeCircle,
  commitCircleDraw,
  executeCircleDraw,
  fetchCircleDraws,
  fetchClosurePreview,
  fetchRulesSummary,
  prepareCircleClosure,
  publishCircleRules,
  verifyCircleDraw,
} from "../../api/circleGovernance"
import { fetchCircleMembers } from "../../api/circles"
import type {
  CircleClosurePreview,
  CircleDrawRecord,
  CircleMember,
  CircleRulesSummary,
} from "../../types"

const INPUT =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const money = (v: string) => Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })

/** Circle rules + member acceptance, the verifiable commit-reveal draw, and final reconciliation / closure. */
export function CircleGovernance({ poolId }: { poolId: string }) {
  const { user } = useAuth()
  const role = user?.role ?? ""
  const isOrganizer = role === "pool_manager"
  const canRecord = isOrganizer || role === "risk_compliance"

  const [summary, setSummary] = useState<CircleRulesSummary | null>(null)
  const [members, setMembers] = useState<CircleMember[]>([])
  const [draws, setDraws] = useState<CircleDrawRecord[]>([])
  const [closure, setClosure] = useState<CircleClosurePreview | null>(null)
  const [verdicts, setVerdicts] = useState<Record<string, string>>({})
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [rules, setRules] = useState({
    contribution_amount: "",
    cycle_days: "30",
    order_policy: "",
    hardship_policy: "",
    schedule_note: "",
    first_due_date: "",
  })
  const [clientSeed, setClientSeed] = useState("")
  const [note, setNote] = useState("")

  const load = useCallback(async () => {
    try {
      const [s, m, d, c] = await Promise.all([
        fetchRulesSummary(poolId),
        fetchCircleMembers(poolId),
        fetchCircleDraws(poolId),
        fetchClosurePreview(poolId),
      ])
      setSummary(s)
      setMembers(m)
      setDraws(d)
      setClosure(c)
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load circle governance data."))
    }
  }, [poolId])

  useEffect(() => {
    void load()
  }, [load])

  async function act(action: () => Promise<unknown>, after?: () => void) {
    setBusy(true)
    setError("")
    try {
      await action()
      after?.()
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "The action failed."))
    } finally {
      setBusy(false)
    }
  }

  const missing = new Set(summary?.missing ?? [])
  const pending = draws.find((d) => d.status === "committed")

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-red-400">{error}</p>}

      <Card title="Circle rules & member acceptance">
        {summary?.rules ? (
          <div className="mb-4 text-sm text-ink-secondary">
            <p className="text-ink-primary">
              Rules v{summary.rules.version} · PKR {money(summary.rules.contribution_amount)} every{" "}
              {summary.rules.cycle_days} days ·{" "}
              <Badge variant={summary.missing.length === 0 ? "emerald" : "gold"}>
                accepted by {summary.accepted}/{summary.total}
              </Badge>
            </p>
            <p className="mt-1 text-xs">Order: {summary.rules.order_policy}</p>
            <p className="text-xs">Hardship: {summary.rules.hardship_policy}</p>
            <p className="font-mono text-[10px] text-ink-muted">sealed {summary.rules.content_hash}</p>
          </div>
        ) : (
          <p className="mb-4 text-sm text-ink-secondary">No rules published yet.</p>
        )}

        {summary?.rules && (
          <div className="mb-4 space-y-1">
            {members
              .filter((m) => m.status === "active")
              .map((m) => (
                <div key={m.id} className="flex items-center justify-between text-sm">
                  <span>
                    {m.member_reference} · {m.member_name}
                  </span>
                  {missing.has(m.member_reference) ? (
                    canRecord ? (
                      <button
                        type="button"
                        disabled={busy}
                        className="text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
                        onClick={() => {
                          const method = window.prompt("How was it accepted? in_person, otp or e_sign", "in_person")
                          if (!method) return
                          const evidence = method === "in_person" ? "" : (window.prompt("OTP / e-signature reference") ?? "")
                          void act(() => acceptCircleRules(m.id, method, evidence))
                        }}
                      >
                        Record acceptance
                      </button>
                    ) : (
                      <Badge variant="gold">pending</Badge>
                    )
                  ) : (
                    <Badge variant="emerald">accepted</Badge>
                  )}
                </div>
              ))}
          </div>
        )}

        {isOrganizer && (
          <form
            className="grid grid-cols-1 gap-3 border-t border-white/8 pt-4 sm:grid-cols-2"
            onSubmit={(e: FormEvent) => {
              e.preventDefault()
              void act(() => publishCircleRules(poolId, rules))
            }}
          >
            <input required type="number" min="1" step="0.01" placeholder="Contribution (PKR)" className={INPUT} value={rules.contribution_amount} onChange={(e) => setRules({ ...rules, contribution_amount: e.target.value })} />
            <input required type="number" min="1" placeholder="Cycle length (days)" className={INPUT} value={rules.cycle_days} onChange={(e) => setRules({ ...rules, cycle_days: e.target.value })} />
            <textarea required rows={2} placeholder="How the payout order is decided" className={INPUT} value={rules.order_policy} onChange={(e) => setRules({ ...rules, order_policy: e.target.value })} />
            <textarea required rows={2} placeholder="Hardship policy" className={INPUT} value={rules.hardship_policy} onChange={(e) => setRules({ ...rules, hardship_policy: e.target.value })} />
            <label className="text-xs text-ink-secondary sm:col-span-2">
              First contribution due date (used for reminders)
              <input type="date" className={`${INPUT} mt-1`} value={rules.first_due_date} onChange={(e) => setRules({ ...rules, first_due_date: e.target.value })} />
            </label>
            <input placeholder="Schedule note (optional)" className={`${INPUT} sm:col-span-2`} value={rules.schedule_note} onChange={(e) => setRules({ ...rules, schedule_note: e.target.value })} />
            <div className="sm:col-span-2">
              <Button type="submit" variant="primary" disabled={busy}>
                {summary?.rules ? "Publish new version (members must re-accept)" : "Publish rules"}
              </Button>
            </div>
          </form>
        )}
      </Card>

      <Card title="Verifiable payout draw (commit, then reveal)">
        <p className="mb-3 text-xs text-ink-secondary">
          Step 1 publishes only a hash of the secret seed. Step 2 takes a seed chosen by the members, derives the
          order, and reveals the secret so anyone can recompute and verify it.
        </p>
        {isOrganizer && !pending && (
          <Button variant="primary" disabled={busy} onClick={() => void act(() => commitCircleDraw(poolId))}>
            1. Commit draw
          </Button>
        )}
        {pending && (
          <div className="space-y-2">
            <p className="font-mono text-[11px] text-ink-secondary">commitment {pending.commitment}</p>
            <p className="text-xs text-ink-secondary">Drawing for: {pending.participants.join(", ")}</p>
            {isOrganizer && (
              <div className="flex gap-2">
                <input placeholder="Seed chosen by members" className={INPUT} value={clientSeed} onChange={(e) => setClientSeed(e.target.value)} />
                <Button
                  variant="primary"
                  disabled={busy}
                  onClick={() => void act(() => executeCircleDraw(pending.id, clientSeed), () => setClientSeed(""))}
                >
                  2. Execute
                </Button>
              </div>
            )}
          </div>
        )}
        <div className="mt-4 space-y-3">
          {draws
            .filter((d) => d.status === "executed")
            .map((d) => (
              <div key={d.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-xs">
                <p className="text-ink-primary">
                  Draw #{d.sequence} · {d.assignments.sort((a, b) => a.position - b.position).map((a) => `${a.position}. ${a.member_reference}`).join("  ")}
                </p>
                <p className="mt-1 font-mono text-[10px] text-ink-muted">
                  commitment {d.commitment}
                  <br />
                  server seed {d.server_seed} · client seed {d.client_seed}
                </p>
                <button
                  type="button"
                  className="mt-1 text-emerald-400 hover:text-emerald-300"
                  onClick={async () => {
                    const v = await verifyCircleDraw(d.id)
                    setVerdicts((prev) => ({ ...prev, [d.id]: v.verified ? "Verified: seed matches commitment and order recomputes." : "FAILED verification." }))
                  }}
                >
                  Verify
                </button>
                {verdicts[d.id] && <span className="ml-2 text-ink-secondary">{verdicts[d.id]}</span>}
              </div>
            ))}
        </div>
      </Card>

      <Card title="Final reconciliation & closure">
        {closure && (
          <>
            <p className="mb-2 text-sm text-ink-primary">
              Collected PKR {money(closure.total_collected)} · disbursed PKR {money(closure.total_disbursed)} ·{" "}
              {Number(closure.difference) === 0 ? "balanced" : `difference PKR ${money(closure.difference)}`}
            </p>
            {closure.blockers.length > 0 && (
              <ul className="mb-3 list-disc pl-5 text-xs text-amber-300">
                {closure.blockers.map((b) => (
                  <li key={b}>{b}</li>
                ))}
              </ul>
            )}
            <div className="mb-3 space-y-1 text-xs text-ink-secondary">
              {closure.members.map((m) => (
                <div key={m.member_reference}>
                  {m.member_reference} · contributed {money(m.contributed)} · received {money(m.received)} · net {money(m.net)}
                </div>
              ))}
            </div>
            {(role === "pool_manager" || role === "finance_maker" || role === "finance_checker") && (
              <div className="flex flex-wrap gap-2">
                {(role === "pool_manager" || role === "finance_maker") && (
                  <>
                    {Number(closure.difference) !== 0 && (
                      <input placeholder="Surplus / shortfall resolution" className={INPUT} value={note} onChange={(e) => setNote(e.target.value)} />
                    )}
                    <Button variant="secondary" disabled={busy || closure.blockers.length > 0} onClick={() => void act(() => prepareCircleClosure(poolId, note))}>
                      Prepare closure
                    </Button>
                  </>
                )}
                {role === "finance_checker" && (
                  <Button variant="primary" disabled={busy} onClick={() => void act(() => closeCircle(poolId))}>
                    Confirm & close circle
                  </Button>
                )}
              </div>
            )}
          </>
        )}
      </Card>
    </div>
  )
}
