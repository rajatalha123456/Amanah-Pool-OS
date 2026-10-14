import { useCallback, useEffect, useState, type FormEvent } from "react"
import { useAuth } from "../../api/auth"
import { extractErrorMessage } from "../../api/errors"
import { DEFAULT_PAGE_SIZE } from "../../api/pagination"
import { fetchPools } from "../../api/pools"
import {
  decideSuspense,
  fetchClearableAccounts,
  fetchSuspenseAgeing,
  fetchSuspenseItems,
  proposeSuspenseClearing,
  proposeSuspenseItem,
  type PoolAccount,
  type SuspenseAgeing,
  type SuspenseItem,
  type SuspenseSide,
} from "../../api/suspense"
import type { BadgeVariant, Pool } from "../../types"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Card } from "../Card"
import { Pager } from "../Pager"
import { Spinner } from "../Spinner"

const STATUS: Record<SuspenseItem["status"], { label: string; variant: BadgeVariant }> = {
  proposed: { label: "Proposed", variant: "gold" },
  open: { label: "Open in suspense", variant: "navy" },
  clearing_proposed: { label: "Clearing proposed", variant: "gold" },
  cleared: { label: "Cleared", variant: "emerald" },
  rejected: { label: "Rejected", variant: "neutral" },
}

const SIDE: Record<SuspenseSide, string> = {
  unidentified_receipt: "Money in, owner not known",
  unexplained_shortfall: "Money missing, reason not known",
}

const money = (value: string | number) => Number(value).toLocaleString(undefined, { minimumFractionDigits: 2 })
const input = "mt-1 block w-full rounded border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary"

/**
 * Suspense (BRD 4 / 6.2 / 10): an amount that cannot be placed yet is held as a named item, never as an anonymous plug.
 * A finance maker proposes to park or to clear it; a different finance checker approves and only then is it journalled.
 */
export function SuspenseItems() {
  const { user } = useAuth()
  const isMaker = user?.role === "finance_maker"
  const isChecker = user?.role === "finance_checker"
  const me = String(user?.id ?? "")

  const [pools, setPools] = useState<Pool[]>([])
  const [poolId, setPoolId] = useState("")
  const [accounts, setAccounts] = useState<PoolAccount[]>([])
  const [items, setItems] = useState<SuspenseItem[]>([])
  const [page, setPage] = useState(1)
  const [count, setCount] = useState(0)
  const [ageing, setAgeing] = useState<SuspenseAgeing | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  const [form, setForm] = useState({ side: "unidentified_receipt" as SuspenseSide, amount: "", description: "", reference: "" })
  const [clearing, setClearing] = useState<{ id: string; account: string; reason: string } | null>(null)

  useEffect(() => {
    Promise.all([fetchPools(), fetchClearableAccounts()])
      .then(([poolList, accountList]) => {
        setPools(poolList)
        setAccounts(accountList)
        // A live pool first: a draft (e.g. one just made in the wizard) has no journals yet.
        const first =
          poolList.find((p) => !["draft", "pending_approval"].includes(p.status) && p.product_detail?.operating_model !== "community_circle") ??
          poolList[0]
        if (first) setPoolId(first.id)
      })
      .catch((err) => setError(extractErrorMessage(err, "Unable to load pools.")))
  }, [])

  const load = useCallback(async () => {
    if (!poolId) return
    setLoading(true)
    try {
      const [list, report] = await Promise.all([fetchSuspenseItems(poolId, page), fetchSuspenseAgeing(poolId)])
      setItems(list.results)
      setCount(list.count)
      setAgeing(report)
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load suspense."))
    } finally {
      setLoading(false)
    }
  }, [poolId, page])

  useEffect(() => {
    void load()
  }, [load])

  async function act(run: () => Promise<unknown>, done: string) {
    setBusy(true)
    setNotice("")
    try {
      await run()
      setNotice(done)
      setError("")
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "The action was refused."))
    } finally {
      setBusy(false)
    }
  }

  function submitProposal(e: FormEvent) {
    e.preventDefault()
    void act(async () => {
      await proposeSuspenseItem({ pool: poolId, ...form })
      setForm({ side: "unidentified_receipt", amount: "", description: "", reference: "" })
    }, "Proposed. A finance checker approves it before anything is posted.")
  }

  const ageById = new Map((ageing?.items ?? []).map((row) => [row.id, row]))
  const accountName = (key: string) => accounts.find((a) => a.key === key)?.name ?? key

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-red-400">{error}</p>}
      {notice && <p className="text-sm text-emerald-300">{notice}</p>}

      <Card
        title="Suspense position"
        actions={
          <label className="flex items-center gap-2 text-xs text-ink-secondary">
            Pool
            <select
              value={poolId}
              onChange={(e) => {
                setPoolId(e.target.value)
                setPage(1)
              }}
              className="rounded border border-white/10 bg-navy-800 px-2 py-1 text-xs text-ink-primary"
            >
              {pools.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code}
                </option>
              ))}
            </select>
          </label>
        }
      >
        {!ageing ? (
          <Spinner />
        ) : (
          <div className="grid grid-cols-2 gap-4 text-xs sm:grid-cols-4">
            <div>
              <p className="text-ink-muted uppercase">Open items</p>
              <p className="text-lg font-bold text-ink-primary">{ageing.open_items}</p>
              <p className={ageing.overdue_items ? "text-red-400" : "text-ink-secondary"}>
                {ageing.overdue_items} older than {ageing.max_age_days} days
              </p>
            </div>
            <div>
              <p className="text-ink-muted uppercase">Suspense ledger</p>
              <p className="text-lg font-bold text-ink-primary">PKR {money(ageing.ledger_balance)}</p>
              <Badge variant={ageing.itemized ? "emerald" : "gold"}>
                {ageing.itemized ? "Every amount is a named item" : `Items total ${money(ageing.items_net)}: does not match`}
              </Badge>
            </div>
            <div className="col-span-2">
              <p className="text-ink-muted uppercase">By age (days)</p>
              <div className="mt-1 flex flex-wrap gap-3 text-ink-primary">
                {Object.entries(ageing.buckets).map(([bucket, amount]) => (
                  <span key={bucket}>
                    {bucket}: <span className="font-mono">{money(amount)}</span>
                  </span>
                ))}
              </div>
              <p className="mt-1 text-ink-secondary">A period cannot be closed while an item is older than {ageing.max_age_days} days.</p>
            </div>
          </div>
        )}
      </Card>

      {isMaker && (
        <Card title="Park an amount in suspense">
          <form onSubmit={submitProposal} className="grid grid-cols-1 gap-3 text-xs sm:grid-cols-4">
            <label className="text-ink-secondary">
              What happened
              <select value={form.side} onChange={(e) => setForm({ ...form, side: e.target.value as SuspenseSide })} className={input}>
                {Object.entries(SIDE).map(([key, label]) => (
                  <option key={key} value={key}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-ink-secondary">
              Amount (PKR)
              <input type="number" step="0.01" min="0.01" required value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} className={input} />
            </label>
            <label className="text-ink-secondary">
              Bank / statement reference
              <input value={form.reference} onChange={(e) => setForm({ ...form, reference: e.target.value })} className={input} />
            </label>
            <label className="text-ink-secondary sm:col-span-4">
              What is known about it
              <input required value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} className={input} />
            </label>
            <div className="sm:col-span-4">
              <Button type="submit" disabled={busy || !poolId}>
                Propose
              </Button>
            </div>
          </form>
        </Card>
      )}

      <Card title={`Suspense items (${count})`}>
        {loading ? (
          <div className="flex items-center gap-2 py-6 text-ink-secondary">
            <Spinner /> <span className="text-sm">Loading...</span>
          </div>
        ) : items.length === 0 ? (
          <p className="text-sm text-ink-secondary">Nothing has been held in suspense for this pool.</p>
        ) : (
          <div className="space-y-3">
            {items.map((item) => {
              const age = ageById.get(item.id)
              return (
                <div key={item.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-xs">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <p className="font-semibold text-ink-primary">
                      PKR {money(item.amount)} · {SIDE[item.side]}
                      {item.reference && <span className="ml-2 font-mono text-ink-muted">{item.reference}</span>}
                    </p>
                    <span className="flex items-center gap-2">
                      {age && <span className={age.overdue ? "text-red-400" : "text-ink-secondary"}>{age.age_days} days</span>}
                      <Badge variant={STATUS[item.status].variant}>{STATUS[item.status].label}</Badge>
                    </span>
                  </div>
                  <p className="mt-1 text-ink-secondary">{item.description}</p>
                  <p className="mt-1 text-ink-muted">
                    Opened {item.opened_on} · proposed by {item.proposed_by_name ?? "—"}
                    {item.opened_by_name && ` · approved by ${item.opened_by_name}`}
                    {item.status === "cleared" && ` · cleared to ${accountName(item.clear_account_key)} on ${item.cleared_on} by ${item.cleared_by_name ?? "—"}`}
                    {item.status === "clearing_proposed" && ` · clearing to ${accountName(item.clear_account_key)}: ${item.clear_reason}`}
                    {item.decision_note && ` · note: ${item.decision_note}`}
                  </p>

                  <div className="mt-2 flex flex-wrap gap-3">
                    {isChecker && item.status === "proposed" && String(item.proposed_by) !== me && (
                      <>
                        <button type="button" disabled={busy} className="text-emerald-400" onClick={() => void act(() => decideSuspense(item.id, "approve"), "Approved and posted to suspense.")}>
                          Approve and post
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          className="text-red-400"
                          onClick={() => {
                            const reason = window.prompt("Why is this refused?")
                            if (reason) void act(() => decideSuspense(item.id, "reject", reason), "Refused.")
                          }}
                        >
                          Refuse
                        </button>
                      </>
                    )}
                    {isMaker && item.status === "open" && (
                      <button type="button" className="text-emerald-400" onClick={() => setClearing({ id: item.id, account: "", reason: "" })}>
                        Propose clearing
                      </button>
                    )}
                    {isChecker && item.status === "clearing_proposed" && String(item.clear_proposed_by) !== me && (
                      <>
                        <button type="button" disabled={busy} className="text-emerald-400" onClick={() => void act(() => decideSuspense(item.id, "approve-clear"), "Cleared and posted.")}>
                          Approve clearing
                        </button>
                        <button
                          type="button"
                          disabled={busy}
                          className="text-red-400"
                          onClick={() => {
                            const reason = window.prompt("Why is the clearing refused?")
                            if (reason) void act(() => decideSuspense(item.id, "reject-clear", reason), "Clearing refused; the item stays open.")
                          }}
                        >
                          Refuse clearing
                        </button>
                      </>
                    )}
                  </div>

                  {clearing?.id === item.id && (
                    <form
                      className="mt-3 grid grid-cols-1 gap-2 sm:grid-cols-3"
                      onSubmit={(e) => {
                        e.preventDefault()
                        void act(async () => {
                          await proposeSuspenseClearing(item.id, clearing.account, clearing.reason)
                          setClearing(null)
                        }, "Clearing proposed. A finance checker approves it.")
                      }}
                    >
                      <label className="text-ink-secondary">
                        Where it belongs
                        <select required value={clearing.account} onChange={(e) => setClearing({ ...clearing, account: e.target.value })} className={input}>
                          <option value="">Choose an account</option>
                          {accounts.map((a) => (
                            <option key={a.key} value={a.key}>
                              {a.name}
                            </option>
                          ))}
                        </select>
                      </label>
                      <label className="text-ink-secondary sm:col-span-2">
                        How that was established
                        <input required value={clearing.reason} onChange={(e) => setClearing({ ...clearing, reason: e.target.value })} className={input} />
                      </label>
                      <div className="flex gap-2 sm:col-span-3">
                        <Button type="submit" size="sm" disabled={busy}>
                          Propose
                        </Button>
                        <Button type="button" size="sm" variant="secondary" onClick={() => setClearing(null)}>
                          Cancel
                        </Button>
                      </div>
                    </form>
                  )}
                </div>
              )
            })}
            <Pager page={page} pageSize={DEFAULT_PAGE_SIZE} count={count} onChange={setPage} disabled={loading} />
          </div>
        )}
      </Card>
    </div>
  )
}
