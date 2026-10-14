import { useCallback, useEffect, useState } from "react"
import { useAuth } from "../../api/auth"
import { extractErrorMessage } from "../../api/errors"
import {
  confirmGLExport,
  createGLExport,
  downloadGLExport,
  fetchGLExports,
  fetchPendingBatchCount,
  fetchTrialBalance,
  rejectGLExport,
  type GLExport,
  type TrialBalance,
} from "../../api/glHandover"
import { DEFAULT_PAGE_SIZE } from "../../api/pagination"
import { fetchPools } from "../../api/pools"
import type { BadgeVariant, Pool } from "../../types"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Card } from "../Card"
import { Pager } from "../Pager"
import { Spinner } from "../Spinner"

const STATUS: Record<GLExport["status"], { label: string; variant: BadgeVariant }> = {
  generated: { label: "Awaiting GL answer", variant: "gold" },
  confirmed: { label: "Posted in GL", variant: "emerald" },
  rejected: { label: "Rejected by GL", variant: "neutral" },
}

const money = (value: string | number) => Number(value).toLocaleString(undefined, { minimumFractionDigits: 2 })

/**
 * Hand-over of posted journals to the enterprise general ledger (BRD 10 / 12). A finance maker generates a file of the
 * batches not sent yet; a different finance checker records the GL's answer. Below it, the pool's trial balance.
 */
export function GLHandover() {
  const { user } = useAuth()
  const isMaker = user?.role === "finance_maker"
  const isChecker = user?.role === "finance_checker"

  const [pools, setPools] = useState<Pool[]>([])
  const [poolId, setPoolId] = useState("")
  const [exports, setExports] = useState<GLExport[]>([])
  const [page, setPage] = useState(1)
  const [count, setCount] = useState(0)
  const [pending, setPending] = useState<number | null>(null)
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [asOf, setAsOf] = useState("")
  const [trial, setTrial] = useState<TrialBalance | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [notice, setNotice] = useState("")

  useEffect(() => {
    fetchPools()
      .then((data) => {
        setPools(data)
        const first = data.find((p) => p.product_detail?.operating_model !== "community_circle") ?? data[0]
        if (first) setPoolId(first.id)
      })
      .catch((err) => setError(extractErrorMessage(err, "Unable to load pools.")))
  }, [])

  const load = useCallback(async () => {
    if (!poolId) return
    setLoading(true)
    try {
      const [list, waiting, tb] = await Promise.all([
        fetchGLExports(poolId, page),
        fetchPendingBatchCount(poolId),
        fetchTrialBalance(poolId, asOf),
      ])
      setExports(list.results)
      setCount(list.count)
      setPending(waiting)
      setTrial(tb)
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load the GL hand-over."))
    } finally {
      setLoading(false)
    }
  }, [poolId, page, asOf])

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

  return (
    <div className="space-y-6">
      {error && <p className="text-sm text-red-400">{error}</p>}
      {notice && <p className="text-sm text-emerald-300">{notice}</p>}

      <Card title="Send journals to the general ledger">
        <p className="mb-3 text-xs text-ink-secondary">
          A file holds every posted batch of the pool that has not been sent yet, so no batch is sent twice. The file is kept
          exactly as sent. A different finance checker records the GL&apos;s answer: posted (with the GL reference) or rejected
          (the batches can then be sent again).
        </p>
        <div className="flex flex-wrap items-end gap-3 text-xs">
          <label className="text-ink-secondary">
            Pool
            <select
              value={poolId}
              onChange={(e) => {
                setPoolId(e.target.value)
                setPage(1)
              }}
              className="mt-1 block rounded border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary"
            >
              {pools.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} — {p.name}
                </option>
              ))}
            </select>
          </label>
          <label className="text-ink-secondary">
            From (optional)
            <input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} className="mt-1 block rounded border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary" />
          </label>
          <label className="text-ink-secondary">
            To (optional)
            <input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} className="mt-1 block rounded border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary" />
          </label>
          {isMaker && (
            <Button
              disabled={busy || !poolId || pending === 0}
              onClick={() => void act(() => createGLExport(poolId, dateFrom, dateTo), "Export generated. A finance checker records the GL's answer.")}
            >
              Generate export
            </Button>
          )}
          <span className="pb-2 text-ink-secondary">
            {pending === null ? "" : pending === 0 ? "Every posted batch has been sent." : `${pending} posted batch(es) not sent yet.`}
          </span>
        </div>
      </Card>

      <Card title={`Exports (${count})`}>
        {loading ? (
          <div className="flex items-center gap-2 py-6 text-ink-secondary">
            <Spinner /> <span className="text-sm">Loading...</span>
          </div>
        ) : exports.length === 0 ? (
          <p className="text-sm text-ink-secondary">Nothing has been sent to the GL for this pool yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase text-ink-muted">
                <tr className="border-b border-white/10">
                  <th className="px-2 py-2">Generated</th>
                  <th className="px-2 py-2">Batches / rows</th>
                  <th className="px-2 py-2">Debit</th>
                  <th className="px-2 py-2">Credit</th>
                  <th className="px-2 py-2">Status</th>
                  <th className="px-2 py-2">GL reference / reason</th>
                  <th className="px-2 py-2 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {exports.map((x) => (
                  <tr key={x.id}>
                    <td className="px-2 py-2 text-ink-primary">
                      {x.created_at.slice(0, 16).replace("T", " ")}
                      <span className="block text-ink-muted">by {x.exported_by_name ?? "—"}</span>
                    </td>
                    <td className="px-2 py-2">
                      {x.batch_count} / {x.row_count}
                    </td>
                    <td className="px-2 py-2 font-mono">{money(x.total_debit)}</td>
                    <td className="px-2 py-2 font-mono">{money(x.total_credit)}</td>
                    <td className="px-2 py-2">
                      <Badge variant={STATUS[x.status].variant}>{STATUS[x.status].label}</Badge>
                    </td>
                    <td className="px-2 py-2 text-ink-secondary">
                      {x.gl_reference || x.decision_note || "—"}
                      {x.decided_by_name && <span className="block text-ink-muted">by {x.decided_by_name}</span>}
                    </td>
                    <td className="px-2 py-2 text-right whitespace-nowrap">
                      <button type="button" className="text-emerald-400" onClick={() => void downloadGLExport(x)}>
                        Download
                      </button>
                      {isChecker && x.status === "generated" && (
                        <>
                          <button
                            type="button"
                            disabled={busy}
                            className="ml-3 text-emerald-400"
                            onClick={() => {
                              const ref = window.prompt("The GL's posting reference for this file")
                              if (ref) void act(() => confirmGLExport(x.id, ref), "Recorded as posted in the GL.")
                            }}
                          >
                            Confirm posted
                          </button>
                          <button
                            type="button"
                            disabled={busy}
                            className="ml-3 text-red-400"
                            onClick={() => {
                              const reason = window.prompt("Why did the GL reject the file?")
                              if (reason) void act(() => rejectGLExport(x.id, reason), "Recorded as rejected; the batches can be sent again.")
                            }}
                          >
                            Rejected
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <Pager page={page} pageSize={DEFAULT_PAGE_SIZE} count={count} onChange={setPage} disabled={loading} />
          </div>
        )}
      </Card>

      <Card
        title="Trial balance"
        actions={
          <label className="flex items-center gap-2 text-xs text-ink-secondary">
            As of
            <input type="date" value={asOf} onChange={(e) => setAsOf(e.target.value)} className="rounded border border-white/10 bg-navy-800 px-2 py-1 text-xs text-ink-primary" />
          </label>
        }
      >
        {!trial || trial.lines.length === 0 ? (
          <p className="text-sm text-ink-secondary">No posted journals for this pool{asOf ? " up to that date" : ""}.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase text-ink-muted">
                <tr className="border-b border-white/10">
                  <th className="px-2 py-2">GL code</th>
                  <th className="px-2 py-2">Account</th>
                  <th className="px-2 py-2 text-right">Debit</th>
                  <th className="px-2 py-2 text-right">Credit</th>
                  <th className="px-2 py-2 text-right">Balance</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {trial.lines.map((l) => (
                  <tr key={`${l.gl_code}-${l.account_name}`}>
                    <td className="px-2 py-2 font-mono text-ink-secondary">{l.gl_code || "not mapped"}</td>
                    <td className="px-2 py-2 text-ink-primary">{l.account_name}</td>
                    <td className="px-2 py-2 text-right font-mono">{money(l.debit)}</td>
                    <td className="px-2 py-2 text-right font-mono">{money(l.credit)}</td>
                    <td className="px-2 py-2 text-right font-mono">{money(l.balance)}</td>
                  </tr>
                ))}
                <tr className="font-semibold text-ink-primary">
                  <td className="px-2 py-2" colSpan={2}>
                    Total {trial.balanced ? "(balanced)" : "(NOT balanced)"}
                  </td>
                  <td className="px-2 py-2 text-right font-mono">{money(trial.total_debit)}</td>
                  <td className="px-2 py-2 text-right font-mono">{money(trial.total_credit)}</td>
                  <td className="px-2 py-2" />
                </tr>
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
