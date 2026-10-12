import { useCallback, useEffect, useState } from "react"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Card } from "../Card"
import { extractErrorMessage } from "../../api/errors"
import { castMyVote, fetchMyProposals, type MyProposal } from "../../api/memberCircles"

/** A member votes on their circle's proposals with their own login (BRD 13: "vote/consent"). */
export function CircleVoting() {
  const [rows, setRows] = useState<MyProposal[]>([])
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      setRows(await fetchMyProposals())
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load proposals."))
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function vote(id: string, decision: string) {
    if (!window.confirm(`Record your vote: ${decision}? A vote cannot be changed.`)) return
    setBusy(true)
    setError("")
    try {
      await castMyVote(id, decision)
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "Your vote could not be recorded."))
    } finally {
      setBusy(false)
    }
  }

  if (rows.length === 0 && !error) return null
  return (
    <Card title="Circle proposals and voting">
      <div className="space-y-3 text-sm" data-testid="circle-voting">
        {error && <p className="text-red-400">{error}</p>}
        {rows.map((p) => (
          <div key={p.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span className="font-semibold text-ink-primary">{p.title}</span>
              <Badge variant={p.status === "open" ? "gold" : "neutral"}>{p.status.replace("_", " ")}</Badge>
            </div>
            <p className="mt-1 text-xs text-ink-secondary">
              {p.pool_name} · vote by {p.voting_deadline}
            </p>
            <p className="mt-1 text-xs text-ink-secondary">{p.description}</p>
            {p.my_vote && <p className="mt-2 text-xs text-emerald-300">You voted: {p.my_vote}</p>}
            {p.can_vote && (
              <div className="mt-2 flex gap-2">
                {["approve", "reject", "abstain"].map((d) => (
                  <Button key={d} size="sm" variant={d === "approve" ? "primary" : "secondary"} disabled={busy} onClick={() => void vote(p.id, d)}>
                    {d[0].toUpperCase() + d.slice(1)}
                  </Button>
                ))}
              </div>
            )}
            {p.tally && (
              <p className="mt-2 text-xs text-ink-muted">
                Result: {Object.entries(p.tally).map(([k, v]) => `${k} ${v}`).join(" · ")}
              </p>
            )}
          </div>
        ))}
      </div>
    </Card>
  )
}
