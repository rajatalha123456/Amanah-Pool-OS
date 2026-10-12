import { useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { useAuth } from "../../api/auth"
import { castShariahQuorumVote } from "../../api/shariahGovernance"
import { extractErrorMessage } from "../../api/errors"
import type { ShariahDecision } from "../../types"

interface ShariahQuorumCeremonyProps {
  decisions: ShariahDecision[]
  onDecisionUpdated: (updated: ShariahDecision) => void
}

const INPUT =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

/**
 * Shariah Board quorum. Each vote is the logged-in Board member's own (the server takes the name from the
 * login); the drafter of a ruling cannot vote on it, and the ruling is approved when two thirds of the
 * tenant's active Board members have approved it.
 */
export function ShariahQuorumCeremony({ decisions, onDecisionUpdated }: ShariahQuorumCeremonyProps) {
  const { user } = useAuth()
  const isBoard = user?.role === "shariah_board"
  const [selectedDecisionId, setSelectedDecisionId] = useState<string>(
    () => decisions.find((d) => d.status === "draft")?.id ?? decisions[0]?.id ?? "",
  )
  const [vote, setVote] = useState<"approve" | "reject">("approve")
  const [notes, setNotes] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  const decision = decisions.find((d) => d.id === selectedDecisionId)
  const votes = decision?.quorum_votes ?? []
  const summary = decision?.quorum_summary
  const alreadyVoted = votes.some((v) => v.signatory_user_name === user?.full_name || v.scholar_name === user?.full_name)

  async function submit() {
    if (!decision) return
    setBusy(true)
    setError("")
    try {
      const updated = await castShariahQuorumVote(decision.id, { vote, fiqh_opinion_notes: notes })
      onDecisionUpdated(updated)
      setNotes("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to record your vote."))
    } finally {
      setBusy(false)
    }
  }

  if (decisions.length === 0) {
    return (
      <Card>
        <p className="py-12 text-center text-sm text-ink-muted">No rulings yet. Draft one in the Fatwa Register first.</p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <Card title="Shariah Board quorum">
        <select value={selectedDecisionId} onChange={(e) => setSelectedDecisionId(e.target.value)} className={`${INPUT} mb-4`}>
          {decisions.map((d) => (
            <option key={d.id} value={d.id}>
              [{d.decision_code}] {d.title} ({d.status})
            </option>
          ))}
        </select>
        {decision && (
          <div className="space-y-2 text-sm">
            <div className="flex flex-wrap items-center gap-2">
              <span className="font-semibold text-ink-primary">{decision.title}</span>
              <Badge variant={decision.status === "approved" ? "emerald" : "gold"}>{decision.status}</Badge>
            </div>
            <p className="text-xs text-ink-secondary">{decision.description}</p>
            {summary && (
              <p className="text-xs text-ink-secondary">
                Approvals {summary.approvals} of {summary.required_votes} required
                {summary.board_size !== undefined ? ` (two thirds of ${summary.board_size} active Board members)` : ""}
                {summary.rejections ? ` · ${summary.rejections} against` : ""}
              </p>
            )}
          </div>
        )}
      </Card>

      <Card title="Votes cast">
        {votes.length === 0 ? (
          <p className="text-sm text-ink-secondary">No votes yet.</p>
        ) : (
          <div className="space-y-3">
            {votes.map((v) => (
              <div key={v.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-xs">
                <p className="text-ink-primary">
                  <span className="font-semibold">{v.scholar_name}</span> · {v.scholar_title} ·{" "}
                  <Badge variant={v.decision_vote === "approve" ? "emerald" : v.decision_vote === "reject" ? "navy" : "neutral"}>
                    {v.decision_vote}
                  </Badge>{" "}
                  · {new Date(v.voted_at).toLocaleString()}
                </p>
                {v.fiqh_concurrence_notes && <p className="mt-1 text-ink-secondary">{v.fiqh_concurrence_notes}</p>}
                <p className="mt-1 font-mono text-[10px] text-ink-muted">record hash {v.digital_signature_hash.slice(0, 24)}...</p>
              </div>
            ))}
          </div>
        )}
      </Card>

      {isBoard && decision?.status === "draft" && !alreadyVoted && (
        <Card title={`Your vote (${user?.full_name})`}>
          <div className="space-y-3">
            <select className={INPUT} value={vote} onChange={(e) => setVote(e.target.value as "approve" | "reject")}>
              <option value="approve">Approve</option>
              <option value="reject">Reject</option>
            </select>
            <textarea rows={3} className={INPUT} placeholder="Your reasoning (required)" value={notes} onChange={(e) => setNotes(e.target.value)} />
            {error && <p className="text-sm text-red-400">{error}</p>}
            <Button variant="primary" disabled={busy || !notes.trim()} onClick={() => void submit()}>
              Record my vote
            </Button>
          </div>
        </Card>
      )}
    </div>
  )
}
