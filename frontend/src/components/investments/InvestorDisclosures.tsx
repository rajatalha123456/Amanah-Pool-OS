import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Card } from "../Card"
import { useAuth } from "../../api/auth"
import { extractErrorMessage } from "../../api/errors"
import {
  acknowledgeDisclosure,
  approveDisclosure,
  fetchDisclosures,
  fetchSubscriptionStatus,
  publishDisclosure,
} from "../../api/disclosures"
import type { CapitalAccount, PoolDisclosureRecord } from "../../types"

const INPUT =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

/** Sealed investor disclosure of the pool's terms, and per-investor acknowledgement (gates subscription). */
export function InvestorDisclosures({ poolId, accounts }: { poolId: string; accounts: CapitalAccount[] }) {
  const { user } = useAuth()
  const role = user?.role ?? ""
  const canPublish = role === "pool_manager" || role === "product_manager" // prepares
  const canApprove = role === "shariah_board" || role === "risk_compliance" // a different person approves
  const canRecord = role === "finance_maker" || role === "pool_manager"
  const isInvestor = role === "investor_member"

  const [list, setList] = useState<PoolDisclosureRecord[]>([])
  const [status, setStatus] = useState<Record<string, { may_subscribe: boolean; reason: string }>>({})
  const [form, setForm] = useState({ risk_warnings: "", fee_statement: "", summary: "" })
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const rows = await fetchDisclosures(poolId)
      setList(rows)
      const entries = await Promise.all(
        accounts.map(async (a) => [a.id, await fetchSubscriptionStatus(a.id)] as const),
      )
      setStatus(Object.fromEntries(entries))
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load disclosures."))
    }
  }, [poolId, accounts])

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

  const latest = list.find((d) => d.status === "published")
  const pending = list.find((d) => d.status === "pending_review")

  return (
    <Card title="Investor disclosure & acknowledgement">
      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
      {latest ? (
        <div className="space-y-2 text-sm">
          <p className="text-ink-primary">
            Disclosure v{latest.version} · <span className="font-mono text-[11px] text-ink-muted">{latest.terms_hash.slice(0, 16)}...</span>
          </p>
          <div className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-xs text-ink-secondary">
            <p>
              {latest.terms.contract.name} ({latest.terms.contract.type}) · profit share{" "}
              {latest.terms.profit_sharing
                ? `${latest.terms.profit_sharing.investor_share_pct}% investors / ${latest.terms.profit_sharing.manager_share_pct}% manager`
                : "not set"}
              {latest.terms.profit_sharing && latest.terms.profit_sharing.wakalah_fee_pct > 0
                ? ` · agent fee ${latest.terms.profit_sharing.wakalah_fee_pct}% p.a.`
                : ""}
            </p>
            <p>
              Exit: {latest.terms.redemption.notice_days} days notice · gate {latest.terms.redemption.gate_pct_per_30_days}% per 30 days
            </p>
            <p className="mt-1">Fees: {latest.fee_statement}</p>
            <p className="text-amber-300">Risks: {latest.risk_warnings}</p>
          </div>
        </div>
      ) : (
        <p className="text-sm text-ink-secondary">No disclosure has been published for this pool - nobody can subscribe yet.</p>
      )}

      {latest && (
        <div className="mt-4 space-y-1">
          {accounts.map((a) => {
            const s = status[a.id]
            return (
              <div key={a.id} className="flex flex-wrap items-center justify-between gap-2 text-sm">
                <span>
                  {a.investor_reference} · {a.investor_name}
                </span>
                <span className="flex items-center gap-3">
                  {s?.may_subscribe ? (
                    <Badge variant="emerald">acknowledged</Badge>
                  ) : (
                    <>
                      <Badge variant="gold">not cleared</Badge>
                      {(isInvestor || canRecord) && (
                        <button
                          type="button"
                          disabled={busy}
                          className="text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
                          onClick={() => {
                            if (!window.confirm("I have read the terms, fees and risk warnings and I acknowledge them.")) return
                            let method = "portal"
                            let evidence = ""
                            if (!isInvestor) {
                              method = window.prompt("How was it acknowledged? in_person, otp or e_sign", "in_person") ?? ""
                              if (!method) return
                              if (method !== "in_person") evidence = window.prompt("OTP / e-signature reference") ?? ""
                            }
                            void act(() => acknowledgeDisclosure(latest.id, a.id, method, evidence))
                          }}
                        >
                          {isInvestor ? "Acknowledge" : "Record acknowledgement"}
                        </button>
                      )}
                    </>
                  )}
                  {s && !s.may_subscribe && <span className="max-w-xs text-[11px] text-ink-muted">{s.reason}</span>}
                </span>
              </div>
            )
          })}
        </div>
      )}

      {pending && (
        <div className="mt-4 rounded-lg border border-amber-500/30 bg-amber-950/20 p-3 text-xs text-amber-200">
          <p className="font-semibold">Disclosure v{pending.version} is prepared and waiting for approval by a different person.</p>
          <p className="mt-1 text-amber-100/80">Fees: {pending.fee_statement}</p>
          <p className="text-amber-100/80">Risks: {pending.risk_warnings}</p>
          {canApprove && (
            <Button size="sm" variant="primary" className="mt-2" disabled={busy} onClick={() => void act(() => approveDisclosure(pending.id))}>
              Approve and publish
            </Button>
          )}
        </div>
      )}

      {canPublish && (
        <form
          className="mt-4 grid grid-cols-1 gap-3 border-t border-white/8 pt-4"
          onSubmit={(e: FormEvent) => {
            e.preventDefault()
            void act(() => publishDisclosure(poolId, form), () => setForm({ risk_warnings: "", fee_statement: "", summary: "" }))
          }}
        >
          <p className="text-xs text-ink-secondary">
            Preparing seals the pool&apos;s current terms into a new version. A different person must approve it before it is published; every investor then acknowledges it before subscribing again.
          </p>
          <textarea required rows={2} placeholder="Risk warnings" className={INPUT} value={form.risk_warnings} onChange={(e) => setForm({ ...form, risk_warnings: e.target.value })} />
          <textarea required rows={2} placeholder="Fee statement" className={INPUT} value={form.fee_statement} onChange={(e) => setForm({ ...form, fee_statement: e.target.value })} />
          <div>
            <Button type="submit" variant="primary" disabled={busy}>
              Prepare new disclosure version
            </Button>
          </div>
        </form>
      )}
    </Card>
  )
}
