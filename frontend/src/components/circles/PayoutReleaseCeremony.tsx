import { useCallback, useEffect, useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import { Modal } from "../Modal"
import { useAuth } from "../../api/auth"
import { extractErrorMessage } from "../../api/errors"
import {
  approvePayout,
  fetchCeremonyReadiness,
  fetchPayoutReceipt,
  rejectPayout,
  requestPayout,
  settlePayout,
} from "../../api/circles"
import type { BadgeVariant, Payout, PayoutCeremonyReadiness, PayoutReceiptData } from "../../types"

interface PayoutReleaseCeremonyProps {
  poolId: string
  onPayoutDisbursed?: () => void
}

const STATUS_BADGE: Record<string, BadgeVariant> = {
  pending: "gold",
  approved: "navy",
  disbursed: "emerald",
  rejected: "neutral",
}

const money = (value: number | string) =>
  `PKR ${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2 })}`

/**
 * Payout release (BRD BR-008): a maker requests the payout for the member whose
 * turn it is, an independent checker approves it, and settlement is confirmed
 * with the bank's own reference. Every figure comes from recorded data; nothing
 * is auto-filled, auto-collected or generated here.
 */
export function PayoutReleaseCeremony({ poolId, onPayoutDisbursed }: PayoutReleaseCeremonyProps) {
  const { user } = useAuth()
  const role = user?.role ?? ""
  const canRequest = role === "pool_manager" || role === "finance_maker"
  const canDecide = role === "finance_checker"
  const canSettle = role === "finance_maker" || role === "finance_checker"

  const [data, setData] = useState<PayoutCeremonyReadiness | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rail, setRail] = useState("raast_rtgs")
  const [payoutDate, setPayoutDate] = useState(() => new Date().toISOString().split("T")[0])
  const [utr, setUtr] = useState("")
  const [busy, setBusy] = useState(false)
  const [receipt, setReceipt] = useState<PayoutReceiptData | null>(null)

  const load = useCallback(async () => {
    setIsLoading(true)
    try {
      setData(await fetchCeremonyReadiness(poolId))
      setError(null)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load payout readiness."))
    } finally {
      setIsLoading(false)
    }
  }, [poolId])

  useEffect(() => {
    void load()
  }, [load])

  async function run(action: () => Promise<unknown>, afterSuccess?: () => void) {
    setBusy(true)
    setError(null)
    try {
      await action()
      afterSuccess?.()
      await load()
    } catch (err) {
      const detail = (err as { response?: { data?: { error?: { details?: { preflight?: string[] } } } } }).response
        ?.data?.error?.details?.preflight
      setError(detail?.length ? detail.join(" • ") : extractErrorMessage(err, "The action failed."))
    } finally {
      setBusy(false)
    }
  }

  if (isLoading && !data) {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner />
        <span className="text-sm">Loading payout readiness...</span>
      </div>
    )
  }
  if (!data) return <p className="text-sm text-red-400">{error ?? "No data."}</p>

  const open: Payout | null = data.open_payout
  const isRequester = open ? String(open.requested_by) === String(user?.id) : false

  return (
    <div className="space-y-6">
      {error && <p className="rounded-md border border-red-500/30 bg-red-950/20 p-3 text-sm text-red-300">{error}</p>}

      <Card title={`Cycle ${data.cycle_number} — payout readiness`}>
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <p className="text-[11px] font-semibold uppercase text-ink-secondary">Recipient (current turn)</p>
            {data.next_recipient ? (
              <>
                <p className="mt-1 font-semibold text-ink-primary">
                  {data.next_recipient.member_name}{" "}
                  <span className="font-mono text-xs text-ink-secondary">{data.next_recipient.member_reference}</span>
                </p>
                <p className="text-xs text-ink-secondary">
                  Position {data.next_recipient.payout_position} · KYC {data.next_recipient.kyc_status}
                </p>
                <p className="font-mono text-xs text-ink-secondary">
                  {data.next_recipient.iban || "No IBAN on record"} {data.next_recipient.bank_name}
                </p>
              </>
            ) : (
              <p className="mt-1 text-sm text-ink-secondary">No eligible member (run the draw first).</p>
            )}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase text-ink-secondary">Collected pot</p>
            <p className="mt-1 font-mono text-lg font-semibold text-emerald-400">
              {money(data.pot_summary.total_collected_pot)}
            </p>
            <p className="text-xs text-ink-secondary">
              {data.pot_summary.received_count}/{data.pot_summary.total_active_members} members contributed
            </p>
            {data.pot_summary.pending_members.length > 0 && (
              <p className="text-xs text-amber-300">
                Pending: {data.pot_summary.pending_members.map((m) => m.name).join(", ")}
              </p>
            )}
          </div>
          <div>
            <p className="text-[11px] font-semibold uppercase text-ink-secondary">Shariah decision</p>
            <p className="mt-1 text-sm text-ink-primary">
              {data.shariah_decision ? `${data.shariah_decision.decision_code} — ${data.shariah_decision.title}` : "None in force"}
            </p>
            <p className="text-xs text-ink-secondary">The recipient receives the full pot - no fee, no uplift.</p>
          </div>
        </div>

        <ul className="mt-5 space-y-1.5">
          {data.checks.map((check) => (
            <li key={check.key} className="flex items-start gap-2 text-sm">
              <span className={check.passed ? "text-emerald-400" : "text-red-400"}>{check.passed ? "✓" : "✗"}</span>
              <span className="text-ink-primary">
                {check.label}
                {check.detail && <span className="ml-2 text-xs text-ink-secondary">{check.detail}</span>}
              </span>
            </li>
          ))}
        </ul>

        {canRequest && !open && data.next_recipient && (
          <div className="mt-5 flex flex-wrap items-end gap-3 border-t border-white/8 pt-4">
            <label className="text-xs text-ink-secondary">
              Settlement rail
              <select
                value={rail}
                onChange={(e) => setRail(e.target.value)}
                className="mt-1 block rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary"
              >
                {data.settlement_rails_options.map((option) => (
                  <option key={option.key} value={option.key}>
                    {option.title}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-xs text-ink-secondary">
              Payout date
              <input
                type="date"
                value={payoutDate}
                onChange={(e) => setPayoutDate(e.target.value)}
                className="mt-1 block rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary"
              />
            </label>
            <Button
              variant="primary"
              disabled={busy || !data.can_request}
              onClick={() =>
                run(() =>
                  requestPayout(poolId, {
                    member_id: data.next_recipient!.member_id,
                    settlement_rail: rail,
                    payout_date: payoutDate,
                  }),
                )
              }
            >
              Request payout for approval
            </Button>
          </div>
        )}
      </Card>

      {open && (
        <Card title="Payout awaiting action">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <p className="font-semibold text-ink-primary">
                {open.member_name} — <span className="font-mono text-emerald-400">{money(open.amount)}</span>
              </p>
              <p className="text-xs text-ink-secondary">
                Rail {open.settlement_rail} · date {open.payout_date}
              </p>
            </div>
            <Badge variant={STATUS_BADGE[open.status] ?? "neutral"}>{open.status}</Badge>
          </div>

          {open.status === "pending" && (
            <div className="mt-4 flex flex-wrap gap-3">
              {canDecide && !isRequester ? (
                <>
                  <Button variant="primary" disabled={busy} onClick={() => run(() => approvePayout(open.id))}>
                    Approve (second signature)
                  </Button>
                  <Button
                    variant="secondary"
                    disabled={busy}
                    onClick={() => {
                      const reason = window.prompt("Reason for rejecting this payout?")
                      if (reason) void run(() => rejectPayout(open.id, reason))
                    }}
                  >
                    Reject
                  </Button>
                </>
              ) : (
                <p className="text-sm text-ink-secondary">
                  Waiting for an independent Finance Checker (the requester cannot approve their own payout).
                </p>
              )}
            </div>
          )}

          {open.status === "approved" && (
            <div className="mt-4 flex flex-wrap items-end gap-3">
              <p className="w-full text-xs text-ink-secondary">
                Approved under decision {open.shariah_certificate_number}. After the bank confirms the transfer,
                record its settlement reference.
              </p>
              {canSettle ? (
                <>
                  <input
                    value={utr}
                    onChange={(e) => setUtr(e.target.value)}
                    placeholder={
                      open.settlement_rail === "internal_book" ? "Optional (internal reference is generated)" : "Bank UTR / RRN"
                    }
                    className="w-72 rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary"
                  />
                  <Button
                    variant="primary"
                    disabled={busy}
                    onClick={() =>
                      run(
                        () => settlePayout(open.id, { settlement_utr: utr }),
                        () => {
                          setUtr("")
                          onPayoutDisbursed?.()
                        },
                      )
                    }
                  >
                    Confirm settlement
                  </Button>
                </>
              ) : (
                <p className="text-sm text-ink-secondary">Awaiting settlement confirmation by Finance.</p>
              )}
            </div>
          )}
        </Card>
      )}

      <Card title="Payout history">
        {data.historical_payouts.length === 0 ? (
          <p className="text-sm text-ink-secondary">No payouts yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-white/8 text-[11px] uppercase text-ink-muted">
                <tr>
                  <th className="px-3 py-2">Cycle</th>
                  <th className="px-3 py-2">Recipient</th>
                  <th className="px-3 py-2">Amount</th>
                  <th className="px-3 py-2">Settlement ref</th>
                  <th className="px-3 py-2">Status</th>
                  <th className="px-3 py-2 text-right">Receipt</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {data.historical_payouts.map((p) => (
                  <tr key={p.id}>
                    <td className="px-3 py-2 font-mono text-emerald-400">#{p.cycle_number}</td>
                    <td className="px-3 py-2 text-ink-primary">{p.member_name || p.member}</td>
                    <td className="px-3 py-2 font-mono">{money(p.amount)}</td>
                    <td className="px-3 py-2 font-mono text-ink-muted">{p.settlement_utr || "—"}</td>
                    <td className="px-3 py-2">
                      <Badge variant={STATUS_BADGE[p.status] ?? "neutral"}>{p.status}</Badge>
                    </td>
                    <td className="px-3 py-2 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => void run(async () => setReceipt(await fetchPayoutReceipt(p.id)))}
                      >
                        View
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {receipt && (
        <Modal title={`Payout receipt — ${receipt.circle_code} cycle ${receipt.cycle_number}`} onClose={() => setReceipt(null)}>
          <dl className="grid grid-cols-2 gap-x-6 gap-y-2 text-sm">
            {(
              [
                ["Recipient", `${receipt.recipient_name} (${receipt.recipient_reference})`],
                ["Amount", money(receipt.amount)],
                ["Status", receipt.status],
                ["Rail", receipt.settlement_rail],
                ["Settlement ref", receipt.settlement_utr ?? "—"],
                ["Account", `${receipt.recipient_iban || "—"} ${receipt.recipient_bank}`],
                ["Requested by", receipt.requested_by ?? "—"],
                ["Approved by", receipt.secondary_approved_by ?? "—"],
                ["Settled by", receipt.settled_by ?? "—"],
                ["Shariah decision", receipt.shariah_certificate_number ?? "—"],
                ["Record hash", receipt.ceremony_hash ?? "—"],
              ] as Array<[string, string]>
            ).map(([label, value]) => (
              <div key={label} className="contents">
                <dt className="text-ink-secondary">{label}</dt>
                <dd className="break-all font-mono text-xs text-ink-primary">{value}</dd>
              </div>
            ))}
          </dl>
        </Modal>
      )}
    </div>
  )
}
