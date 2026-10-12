import { useCallback, useEffect, useState } from "react"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Card } from "../Card"
import { RoleGate } from "../RoleGate"
import { fetchPools } from "../../api/pools"
import { extractErrorMessage } from "../../api/errors"
import { fetchDailyCloses, prepareDailyClose, signDailyClose, type DailyCloseRecord } from "../../api/dailyClose"
import type { Pool } from "../../types"

const STATUS_BADGE = { open: "gold", prepared: "navy", signed: "emerald" } as const

/** BRD 6.2: the maker prepares the day (the server computes the gates); an independent checker signs it. */
export function DailyClosePanel() {
  const [pools, setPools] = useState<Pool[]>([])
  const [poolId, setPoolId] = useState("")
  const [closes, setCloses] = useState<DailyCloseRecord[]>([])
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10))
  const [notes, setNotes] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    fetchPools()
      .then((rows) => {
        const eligible = rows.filter((p) => ["open", "allocation", "frozen"].includes(p.status) && p.product_detail?.operating_model !== "community_circle")
        setPools(eligible)
        if (eligible.length > 0) setPoolId(eligible[0].id)
      })
      .catch((err) => setError(extractErrorMessage(err, "Unable to load pools.")))
  }, [])

  const load = useCallback(async () => {
    if (!poolId) return
    try {
      setCloses(await fetchDailyCloses(poolId))
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load daily closes."))
    }
  }, [poolId])

  useEffect(() => {
    void load()
  }, [load])

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

  return (
    <div className="space-y-6" data-testid="daily-close">
      <Card title="Daily close">
        <p className="mb-3 text-xs text-ink-secondary">
          The maker prepares the day; the server checks the balances, open exceptions and reconciliation. A different
          person (the checker) signs it. A signed day refuses new balance imports and income / expense entries.
        </p>
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
        <div className="flex flex-wrap items-end gap-3">
          <label className="text-xs text-ink-secondary">
            Pool
            <select
              className="mt-1 block rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary"
              value={poolId}
              onChange={(e) => setPoolId(e.target.value)}
            >
              {pools.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.code} - {p.name}
                </option>
              ))}
            </select>
          </label>
          <RoleGate roles={["finance_maker"]}>
            <label className="text-xs text-ink-secondary">
              Date
              <input
                type="date"
                className="mt-1 block rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
            </label>
            <input
              placeholder="Notes (optional)"
              className="rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary"
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <Button variant="primary" disabled={busy || !poolId} onClick={() => void act(() => prepareDailyClose(poolId, date, notes))}>
              Prepare day
            </Button>
          </RoleGate>
        </div>
      </Card>

      {closes.length === 0 ? (
        <p className="text-sm text-ink-secondary">No daily close has been prepared for this pool yet.</p>
      ) : (
        closes.map((c) => (
          <Card key={c.id} title={`${c.value_date} - ${c.pool_code}`}>
            <div className="mb-2 flex items-center gap-3">
              <Badge variant={STATUS_BADGE[c.status]}>{c.status.toUpperCase()}</Badge>
              <span className="text-xs text-ink-secondary">
                Prepared by {c.prepared_by_name ?? "-"}
                {c.signed_by_name ? ` · signed by ${c.signed_by_name}` : ""}
              </span>
              {c.status === "prepared" && (
                <RoleGate roles={["finance_checker"]}>
                  <Button size="sm" variant="primary" disabled={busy} onClick={() => void act(() => signDailyClose(c.id))}>
                    Sign day
                  </Button>
                </RoleGate>
              )}
            </div>
            <ul className="space-y-1 text-xs">
              {c.gates.map((g) => (
                <li key={g.key} className={g.passed ? "text-emerald-300" : "text-amber-300"}>
                  {g.passed ? "✓" : "✗"} {g.label}
                  {g.detail ? ` - ${g.detail}` : ""}
                </li>
              ))}
            </ul>
          </Card>
        ))
      )}
    </div>
  )
}
