import { useEffect, useState } from "react"
import { Card } from "../Card"
import { fetchMyTaxSupport, type MyTaxSupport } from "../../api/portal"
import { fetchRedemptionsForAccount, fetchSubscriptionsForAccount } from "../../api/investments"
import type { CapitalAccount, Redemption, Subscription } from "../../types"

const money = (v: string) => Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })

/** BRD 13 investor dashboard: transactions, and tax / Zakat support. Own data only. */
export function MyTransactions({ accounts }: { accounts: CapitalAccount[] }) {
  const [rows, setRows] = useState<{ date: string; kind: string; account: string; detail: string; amount: string; status: string }[]>([])

  useEffect(() => {
    let live = true
    void Promise.all(
      accounts.map(async (a) => {
        const [subs, reds] = await Promise.all([fetchSubscriptionsForAccount(a.id), fetchRedemptionsForAccount(a.id)])
        return [
          ...subs.map((s: Subscription) => ({ date: s.transaction_date, kind: "Subscription", account: a.investor_reference, detail: `${Number(s.units_allotted).toLocaleString()} units at ${s.nav_per_unit}`, amount: s.amount, status: s.status })),
          ...reds.map((r: Redemption) => ({ date: r.transaction_date, kind: "Redemption", account: a.investor_reference, detail: `${Number(r.units_redeemed).toLocaleString()} units at ${r.nav_per_unit}`, amount: r.amount, status: r.status })),
        ]
      }),
    ).then((parts) => {
      if (live) setRows(parts.flat().sort((a, b) => b.date.localeCompare(a.date)))
    })
    return () => {
      live = false
    }
  }, [accounts])

  if (accounts.length === 0) return null
  return (
    <Card title="My transactions">
      {rows.length === 0 ? (
        <p className="text-xs text-ink-secondary">No subscriptions or redemptions yet.</p>
      ) : (
        <div className="overflow-x-auto" data-testid="my-transactions">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-white/8 text-[11px] uppercase tracking-wider text-ink-secondary">
                <th className="py-2 pr-3">Date</th>
                <th className="py-2 pr-3">Type</th>
                <th className="py-2 pr-3">Account</th>
                <th className="py-2 pr-3">Detail</th>
                <th className="py-2 pr-3 text-right">Amount (PKR)</th>
                <th className="py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5">
              {rows.map((r, i) => (
                <tr key={i}>
                  <td className="py-2 pr-3">{r.date}</td>
                  <td className="py-2 pr-3">{r.kind}</td>
                  <td className="py-2 pr-3">{r.account}</td>
                  <td className="py-2 pr-3 text-ink-secondary">{r.detail}</td>
                  <td className="py-2 pr-3 text-right font-mono">{money(r.amount)}</td>
                  <td className="py-2">{r.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  )
}

export function TaxSupportCard() {
  const [data, setData] = useState<MyTaxSupport | null | undefined>(undefined)
  useEffect(() => {
    void fetchMyTaxSupport().then(setData)
  }, [])
  if (!data) return null
  return (
    <Card title="Tax and Zakat support">
      <div className="space-y-3 text-xs" data-testid="tax-support">
        <p className="text-ink-secondary">
          Tax status on record: <span className="text-ink-primary">{data.tax_status.replace("_", "-")}</span>
          {data.zakat_exempt ? " · Zakat exempt" : ""}
        </p>
        {data.rows.length === 0 ? (
          <p className="text-ink-secondary">No profit payment has been computed for you yet.</p>
        ) : (
          <>
            <div className="overflow-x-auto">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-white/8 text-[11px] uppercase tracking-wider text-ink-secondary">
                    <th className="py-2 pr-3">Period end</th>
                    <th className="py-2 pr-3">Pool</th>
                    <th className="py-2 pr-3 text-right">Gross profit</th>
                    <th className="py-2 pr-3 text-right">Withholding</th>
                    <th className="py-2 pr-3 text-right">Zakat</th>
                    <th className="py-2 text-right">Net</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {data.rows.map((r, i) => (
                    <tr key={i}>
                      <td className="py-2 pr-3">{r.period_end}</td>
                      <td className="py-2 pr-3">{r.pool}</td>
                      <td className="py-2 pr-3 text-right font-mono">{money(r.gross_profit)}</td>
                      <td className="py-2 pr-3 text-right font-mono">
                        {money(r.wht_amount)} <span className="text-ink-muted">({r.wht_rate_pct}%)</span>
                      </td>
                      <td className="py-2 pr-3 text-right font-mono">{money(r.zakat_amount)}</td>
                      <td className="py-2 text-right font-mono">{money(r.net_payout)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="font-semibold text-ink-primary">
              Total gross PKR {money(data.totals.gross_profit)} · withholding PKR {money(data.totals.wht_amount)} · Zakat PKR {money(data.totals.zakat_amount)}
            </p>
          </>
        )}
        <p className="text-ink-muted">{data.note}</p>
      </div>
    </Card>
  )
}
