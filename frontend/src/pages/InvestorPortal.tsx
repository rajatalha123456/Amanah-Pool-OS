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
import type { CapitalAccount, DepositorStatement, PoolDisclosureRecord } from "../types"

const money = (v: string) => Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })

/**
 * Self-service home for investors / members: only their own accounts, statements and disclosures.
 * Every call here is on the investor allow-list enforced by the backend.
 */
export function InvestorPortal() {
  const { user } = useAuth()
  const [accounts, setAccounts] = useState<CapitalAccount[]>([])
  const [statements, setStatements] = useState<DepositorStatement[]>([])
  const [disclosures, setDisclosures] = useState<Record<string, PoolDisclosureRecord | undefined>>({})
  const [cleared, setCleared] = useState<Record<string, { may_subscribe: boolean; reason: string }>>({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")

  const load = useCallback(async () => {
    try {
      const [accountRows, statementRows] = await Promise.all([
        apiClient.get<CapitalAccount[]>("investments/capital-accounts/").then((r) => r.data),
        fetchMyStatements(),
      ])
      setAccounts(accountRows)
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
