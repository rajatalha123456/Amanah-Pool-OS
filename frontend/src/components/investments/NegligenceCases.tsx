import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Card } from "../Card"
import { useAuth } from "../../api/auth"
import { extractErrorMessage } from "../../api/errors"
import {
  addNegligenceNote,
  determineNegligenceCase,
  fetchNegligenceCases,
  raiseNegligenceCase,
} from "../../api/investments"
import type { BadgeVariant, NegligenceCase } from "../../types"

const STATUS: Record<NegligenceCase["status"], { label: string; variant: BadgeVariant }> = {
  open: { label: "Under investigation", variant: "gold" },
  liable: { label: "Manager liable", variant: "navy" },
  cleared: { label: "Manager cleared", variant: "emerald" },
}

const field =
  "rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

/**
 * Manager negligence allegations (BRD 6.4 / BR-006). An open case freezes loss allocation for the
 * periods it covers; only the Shariah Board can find the manager liable (that amount is then borne
 * by the manager) or clear them.
 */
export function NegligenceCases({ poolId }: { poolId: string }) {
  const { user } = useAuth()
  const role = user?.role ?? ""
  const canRaise = ["risk_compliance", "pool_manager", "auditor", "shariah_board"].includes(role)
  const canNote = canRaise || role === "shariah_secretariat"
  const canDetermine = role === "shariah_board"
  const canSee = canNote || role === "finance_maker" || role === "finance_checker"

  const [cases, setCases] = useState<NegligenceCase[]>([])
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)
  const [form, setForm] = useState({ title: "", allegation: "", period_start: "", period_end: "" })

  const load = useCallback(async () => {
    if (!canSee) return
    try {
      setCases(await fetchNegligenceCases(poolId))
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load negligence cases."))
    }
  }, [poolId, canSee])

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

  if (!canSee) return null

  return (
    <Card title="Negligence cases (Musharakah loss control)">
      <p className="mb-3 text-xs text-ink-secondary">
        While a case is open, loss allocation for its period is frozen. A &quot;liable&quot; determination makes the
        manager bear that amount of the loss; the rest follows capital ratio.
      </p>
      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}

      {cases.length === 0 ? (
        <p className="text-sm text-ink-secondary">No cases.</p>
      ) : (
        <div className="space-y-3">
          {cases.map((c) => (
            <div key={c.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-4 text-sm">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div>
                  <p className="font-semibold text-ink-primary">{c.title}</p>
                  <p className="text-xs text-ink-secondary">
                    {c.period_start} to {c.period_end} · raised by {c.raised_by_name ?? "—"}
                  </p>
                </div>
                <Badge variant={STATUS[c.status].variant}>{STATUS[c.status].label}</Badge>
              </div>
              <p className="mt-2 text-xs text-ink-secondary">{c.allegation}</p>
              {c.notes.map((n, i) => (
                <p key={i} className="mt-1 text-xs text-ink-secondary">
                  <span className="text-ink-muted">{new Date(n.at).toLocaleDateString()} · {n.by}:</span> {n.note}
                </p>
              ))}
              {c.status !== "open" && (
                <p className="mt-2 text-xs text-ink-primary">
                  Determination by {c.determined_by_name}: {c.determination_note}
                  {c.liability_amount && <strong> · manager bears PKR {Number(c.liability_amount).toLocaleString()}</strong>}
                  {c.applied_run && <span className="text-emerald-400"> · applied to a signed distribution</span>}
                </p>
              )}
              {c.status === "open" && (
                <div className="mt-3 flex flex-wrap gap-2">
                  {canNote && (
                    <Button
                      size="sm"
                      variant="secondary"
                      disabled={busy}
                      onClick={() => {
                        const note = window.prompt("Investigation note")
                        if (note) void act(() => addNegligenceNote(c.id, note))
                      }}
                    >
                      Add note
                    </Button>
                  )}
                  {canDetermine && (
                    <>
                      <Button
                        size="sm"
                        variant="primary"
                        disabled={busy}
                        onClick={() => {
                          const amount = window.prompt("Liability amount the manager must bear (PKR)")
                          const note = amount ? window.prompt("Reasoning for the determination") : null
                          if (amount && note)
                            void act(() =>
                              determineNegligenceCase(c.id, {
                                outcome: "liable",
                                liability_amount: amount,
                                determination_note: note,
                              }),
                            )
                        }}
                      >
                        Find manager liable
                      </Button>
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => {
                          const note = window.prompt("Reasoning for clearing the manager")
                          if (note) void act(() => determineNegligenceCase(c.id, { outcome: "cleared", determination_note: note }))
                        }}
                      >
                        Clear manager
                      </Button>
                    </>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {canRaise && (
        <form
          className="mt-4 grid grid-cols-1 gap-3 border-t border-white/8 pt-4 sm:grid-cols-2"
          onSubmit={(e: FormEvent) => {
            e.preventDefault()
            void act(
              () => raiseNegligenceCase({ pool: poolId, ...form }),
              () => setForm({ title: "", allegation: "", period_start: "", period_end: "" }),
            )
          }}
        >
          <input required placeholder="Case title" className={field} value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} />
          <div className="flex gap-2">
            <input required type="date" className={`${field} flex-1`} value={form.period_start} onChange={(e) => setForm({ ...form, period_start: e.target.value })} />
            <input required type="date" className={`${field} flex-1`} value={form.period_end} onChange={(e) => setForm({ ...form, period_end: e.target.value })} />
          </div>
          <textarea
            required
            rows={2}
            placeholder="Allegation / what the manager is said to have done or failed to do"
            className={`${field} sm:col-span-2`}
            value={form.allegation}
            onChange={(e) => setForm({ ...form, allegation: e.target.value })}
          />
          <div className="sm:col-span-2">
            <Button type="submit" variant="primary" disabled={busy}>
              Open investigation case
            </Button>
          </div>
        </form>
      )}
    </Card>
  )
}
