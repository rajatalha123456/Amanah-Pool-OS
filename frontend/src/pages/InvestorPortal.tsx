import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { useAuth } from "../api/auth"
import { acknowledgeDisclosure, fetchDisclosures, fetchSubscriptionStatus } from "../api/disclosures"
import { extractErrorMessage } from "../api/errors"
import { apiClient } from "../api/axios"
import { fetchMyStatements } from "../api/participants"
import { redeem } from "../api/investments"
import { fetchMyConsents, fetchMyData, withdrawConsent, type ConsentRow } from "../api/consents"
import { CircleVoting } from "../components/portal/CircleVoting"
import { MyRequests } from "../components/portal/MyRequests"
import { MyTransactions, TaxSupportCard } from "../components/portal/MyTransactionsAndTax"
import { acceptCircleRules, fetchMyCircles, type MyCircle } from "../api/memberCircles"
import type { CapitalAccount, DepositorStatement, PoolDisclosureRecord } from "../types"

const money = (v: string) => Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })

/** A plain printable receipt for a recorded contribution (the member's own record only). */
function printReceipt(circle: MyCircle, c: MyCircle["contributions"][number]) {
  const w = window.open("", "_blank", "width=480,height=600")
  if (!w) return
  const esc = (v: string) => v.replace(/[&<>"]/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[ch] ?? ch)
  w.document.write(
    `<title>Receipt</title><body style="font-family:sans-serif;padding:24px"><h2>Contribution receipt</h2>` +
      `<p>${esc(circle.pool_name)} (${esc(circle.pool_code)})</p><p>Member: ${esc(circle.member_reference)}</p>` +
      `<p>Cycle ${c.cycle_number}</p><p>Amount: PKR ${esc(money(c.amount))}</p><p>Received on: ${esc(c.date)}</p>` +
      `<p>Payment reference: ${esc(c.payment_reference || "-")}</p><p style="color:#666;font-size:12px">Recorded by the circle organizer.</p></body>`,
  )
  w.document.close()
  w.print()
}

/**
 * Self-service home for investors / members: only their own accounts, statements and disclosures.
 * Every call here is on the investor allow-list enforced by the backend.
 */
export function InvestorPortal() {
  const { user } = useAuth()
  const [accounts, setAccounts] = useState<CapitalAccount[]>([])
  const [circles, setCircles] = useState<MyCircle[]>([])
  const [consents, setConsents] = useState<ConsentRow[]>([])
  const [statements, setStatements] = useState<DepositorStatement[]>([])
  const [disclosures, setDisclosures] = useState<Record<string, PoolDisclosureRecord | undefined>>({})
  const [cleared, setCleared] = useState<Record<string, { may_subscribe: boolean; reason: string }>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")

  const load = useCallback(async () => {
    try {
      const [accountRows, statementRows, circleRows, consentRows] = await Promise.all([
        apiClient.get<CapitalAccount[]>("investments/capital-accounts/").then((r) => r.data),
        fetchMyStatements(),
        fetchMyCircles(),
        fetchMyConsents(),
      ])
      setConsents(consentRows)
      setAccounts(accountRows)
      setCircles(circleRows)
      setStatements(statementRows)
      const latest: Record<string, PoolDisclosureRecord | undefined> = {}
      const status: Record<string, { may_subscribe: boolean; reason: string }> = {}
      for (const account of accountRows) {
        if (!(account.pool in latest)) latest[account.pool] = (await fetchDisclosures(account.pool))[0]
        status[account.id] = await fetchSubscriptionStatus(account.id)
      }
      setDisclosures(latest)
      setCleared(status)
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load your accounts."))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function requestRedemption(account: CapitalAccount) {
    const units = window.prompt(`Units to redeem (you hold ${Number(account.units_held).toLocaleString()})`)
    if (!units) return
    const date = window.prompt("Dealing date (YYYY-MM-DD) - your product's notice period applies", new Date().toISOString().slice(0, 10))
    if (!date) return
    try {
      await redeem(account.id, { units_redeemed: units, transaction_date: date })
      setMessage("Redemption request submitted. It is priced and paid only after the bank's independent approval.")
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to submit the redemption request."))
    }
  }

  async function acknowledge(account: CapitalAccount, disclosure: PoolDisclosureRecord) {
    if (!window.confirm("I have read the terms, fees and risk warnings of this disclosure and I acknowledge them.")) return
    try {
      await acknowledgeDisclosure(disclosure.id, account.id, "portal", "")
      setMessage("Disclosure acknowledged.")
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to record the acknowledgement."))
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-5 w-5" /> <span className="text-sm">Loading your accounts...</span>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <PageHeader title={`Assalamu alaikum${user?.full_name ? `, ${user.full_name}` : ""}`} subtitle="Your accounts, statements and disclosures" />
      {error && <p className="text-sm text-red-400">{error}</p>}
      {message && <p className="text-sm text-emerald-400">{message}</p>}

      {circles.length > 0 && (
        <Card title="My savings circles">
          <div className="space-y-3">
            {circles.map((circle) => (
              <div key={circle.member_id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-sm" data-testid="my-circle">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold text-ink-primary">
                    {circle.pool_name} · {circle.member_reference}
                  </span>
                  <Badge variant="neutral">
                    {circle.payout_position ? `Payout position ${circle.payout_position}` : "Position not drawn yet"}
                  </Badge>
                </div>
                {circle.rules && (
                  <p className="mt-1 text-xs text-ink-secondary">
                    Rules v{circle.rules.version}: PKR {money(circle.rules.contribution_amount)} every {circle.rules.cycle_days} days.{" "}
                    {circle.rules.accepted ? (
                      "You have accepted these rules."
                    ) : (
                      <button
                        type="button"
                        className="text-emerald-400 hover:text-emerald-300"
                        onClick={() => {
                          const reference = window.prompt("Enter your e-signature or OTP reference to accept these rules")
                          if (!reference) return
                          acceptCircleRules(circle.pool, "e_sign", reference)
                            .then(() => load())
                            .catch((err) => setError(extractErrorMessage(err, "Could not record your acceptance.")))
                        }}
                      >
                        Accept rules
                      </button>
                    )}
                  </p>
                )}
                <div className="mt-2 space-y-1 text-xs text-ink-secondary">
                  <p className="font-semibold text-ink-primary">My contributions</p>
                  {circle.contributions.length === 0 ? (
                    <p>none recorded</p>
                  ) : (
                    circle.contributions.map((c) => (
                      <p key={c.cycle_number} className="flex flex-wrap items-center gap-2">
                        <span>
                          Cycle {c.cycle_number}: PKR {money(c.amount)} ({c.status}) {c.payment_reference ? `· ref ${c.payment_reference}` : ""}
                        </span>
                        {c.status === "received" && (
                          <button
                            type="button"
                            className="text-emerald-400 hover:text-emerald-300"
                            onClick={() => printReceipt(circle, c)}
                          >
                            Receipt
                          </button>
                        )}
                      </p>
                    ))
                  )}
                </div>
                {circle.ledger.length > 0 && (
                  <details className="mt-2 text-xs text-ink-secondary">
                    <summary className="cursor-pointer text-ink-primary">Circle ledger (every cycle)</summary>
                    <table className="mt-2 w-full text-left">
                      <thead>
                        <tr className="text-[11px] uppercase tracking-wider text-ink-muted">
                          <th className="py-1 pr-2">Cycle</th>
                          <th className="py-1 pr-2">Received</th>
                          <th className="py-1 pr-2">Collected</th>
                          <th className="py-1">Payout</th>
                        </tr>
                      </thead>
                      <tbody>
                        {circle.ledger.map((l) => (
                          <tr key={l.cycle_number}>
                            <td className="py-1 pr-2">{l.cycle_number}</td>
                            <td className="py-1 pr-2">{l.contributions_received}</td>
                            <td className="py-1 pr-2">PKR {money(l.collected)}</td>
                            <td className="py-1">
                              {l.payout ? `${l.payout.recipient} · PKR ${money(l.payout.amount)} (${l.payout.status})` : "not yet"}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </details>
                )}
                {circle.payouts.length > 0 && (
                  <p className="mt-1 text-xs text-ink-secondary">
                    Payouts: {circle.payouts.map((p) => `cycle ${p.cycle_number} PKR ${money(p.amount)} (${p.status})`).join("; ")}
                  </p>
                )}
              </div>
            ))}
          </div>
        </Card>
      )}

      <CircleVoting />

      <MyTransactions accounts={accounts} />
      <TaxSupportCard />

      <MyRequests
        pools={[
          ...accounts.map((a) => ({ id: a.pool, label: `${a.investor_reference} (investment)` })),
          ...circles.map((c) => ({ id: c.pool, label: `${c.pool_name} (circle)` })),
        ].filter((p, i, all) => all.findIndex((x) => x.id === p.id) === i)}
      />

      <Card title="My privacy">
        <div className="space-y-2 text-sm" data-testid="my-privacy">
          {consents.length === 0 ? (
            <p className="text-xs text-ink-secondary">No consents are recorded for you.</p>
          ) : (
            consents.map((c) => (
              <div key={c.id} className="flex flex-wrap items-center justify-between gap-2 text-xs text-ink-secondary">
                <span>
                  {c.purpose_label} - {c.status === "granted" ? `given ${c.granted_at.slice(0, 10)}` : `withdrawn ${c.withdrawn_at?.slice(0, 10) ?? ""}`}
                </span>
                {c.status === "granted" && (
                  <button
                    type="button"
                    className="text-amber-300 hover:text-amber-200"
                    onClick={() => {
                      const reason = window.prompt("Why are you withdrawing this consent? (optional)") ?? ""
                      withdrawConsent(c.id, reason)
                        .then(() => load())
                        .catch((err) => setError(extractErrorMessage(err, "Could not withdraw the consent.")))
                    }}
                  >
                    Withdraw
                  </button>
                )}
              </div>
            ))
          )}
          <Button
            size="sm"
            variant="secondary"
            onClick={() =>
              void fetchMyData()
                .then((data) => {
                  const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }))
                  const link = document.createElement("a")
                  link.href = url
                  link.download = "my-data.json"
                  link.click()
                  URL.revokeObjectURL(url)
                })
                .catch((err) => setError(extractErrorMessage(err, "Could not prepare your data.")))
            }
          >
            Download my data
          </Button>
        </div>
      </Card>

      <Card title="My investment accounts">
        {accounts.length === 0 ? (
          <p className="text-sm text-ink-secondary">No investment accounts are linked to your login.</p>
        ) : (
          <div className="space-y-3">
            {accounts.map((account) => {
              const disclosure = disclosures[account.pool]
              const status = cleared[account.id]
              return (
                <div key={account.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-sm">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <span className="font-semibold text-ink-primary">
                      {account.investor_reference} · {Number(account.units_held).toLocaleString()} units
                    </span>
                    <div className="flex gap-2">
                      <Link to={`/investments/capital-accounts/${account.id}`} className="text-xs text-emerald-400 hover:text-emerald-300">
                        Statement
                      </Link>
                      <Button size="sm" variant="secondary" disabled={Number(account.units_held) <= 0} onClick={() => void requestRedemption(account)}>
                        Request redemption
                      </Button>
                    </div>
                  </div>
                  {disclosure && (
                    <div className="mt-2 text-xs text-ink-secondary">
                      Disclosure v{disclosure.version}: {disclosure.risk_warnings}{" "}
                      {status?.may_subscribe ? (
                        <Badge variant="emerald">acknowledged</Badge>
                      ) : (
                        <Button size="sm" variant="primary" onClick={() => void acknowledge(account, disclosure)}>
                          Read &amp; acknowledge
                        </Button>
                      )}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </Card>

      <Card title="My deposit profit statements">
        {statements.length === 0 ? (
          <p className="text-sm text-ink-secondary">No statements issued yet.</p>
        ) : (
          <div className="space-y-2 text-sm">
            {statements.map((s) => (
              <div key={s.id} className="flex flex-wrap justify-between gap-2 border-b border-white/5 pb-2">
                <span className="text-ink-primary">
                  {s.period_start} to {s.period_end} · {s.account_number ?? s.participant_class}
                </span>
                <span className="text-ink-secondary">
                  opening {money(s.opening_balance)} · profit <span className="text-emerald-400">{money(s.profit_allocated)}</span> · closing{" "}
                  {money(s.closing_balance)}
                </span>
              </div>
            ))}
          </div>
        )}
      </Card>
    </div>
  )
}
