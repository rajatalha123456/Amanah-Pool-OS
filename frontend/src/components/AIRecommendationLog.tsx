import { useHasRole } from "./RoleGate"
import { useCallback, useEffect, useState } from "react"
import { Badge } from "./Badge"
import { Card } from "./Card"
import { extractErrorMessage } from "../api/errors"
import { disposeAIRecommendation, fetchAIMetrics, fetchAIRecommendations } from "../api/aiRecommendations"
import type { AIMetricsRow, AIRecommendation, BadgeVariant } from "../types"

const DISPOSITION: Record<string, BadgeVariant> = {
  pending: "gold",
  accepted: "emerald",
  rejected: "navy",
  overridden: "navy",
}
const pct = (v: number | null) => (v === null ? "—" : `${Math.round(v * 100)}%`)

/** Uniform record of every AI output (BR-009): source, confidence, reason and the human disposition. */
export function AIRecommendationLog() {
  // The auditor reads these records but stays independent of the decision (BRD section 3).
  const mayDecide = useHasRole("product_manager", "pool_manager", "shariah_secretariat", "shariah_board", "risk_compliance")
  const [rows, setRows] = useState<AIRecommendation[]>([])
  const [metrics, setMetrics] = useState<AIMetricsRow[]>([])
  const [filter, setFilter] = useState("")
  const [open, setOpen] = useState<string | null>(null)
  const [error, setError] = useState("")

  const load = useCallback(async () => {
    try {
      const [list, m] = await Promise.all([fetchAIRecommendations(filter), fetchAIMetrics()])
      setRows(list)
      setMetrics(m)
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load AI recommendations."))
    }
  }, [filter])

  useEffect(() => {
    void load()
  }, [load])

  async function decide(rec: AIRecommendation, disposition: "accepted" | "rejected" | "overridden") {
    const note = disposition === "accepted" ? "" : (window.prompt("Reason (required)") ?? "")
    if (disposition !== "accepted" && !note) return
    try {
      await disposeAIRecommendation(rec.id, disposition, note)
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to record the decision."))
    }
  }

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-red-400">{error}</p>}

      <Card title="Model performance (from recorded human decisions)">
        {metrics.length === 0 ? (
          <p className="text-sm text-ink-secondary">No AI output recorded yet.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead>
                <tr className="border-b border-white/8 text-[11px] uppercase tracking-wider text-ink-secondary">
                  <th className="px-3 py-2">Model</th>
                  <th className="px-3 py-2">Outputs</th>
                  <th className="px-3 py-2">Awaiting</th>
                  <th className="px-3 py-2">Acceptance</th>
                  <th className="px-3 py-2">Override / reject</th>
                  <th className="px-3 py-2">Fallback</th>
                  <th className="px-3 py-2">Avg confidence</th>
                  <th className="px-3 py-2">Avg latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {metrics.map((m) => (
                  <tr key={m.model_name}>
                    <td className="px-3 py-2 font-medium text-ink-primary">{m.model_name}</td>
                    <td className="px-3 py-2">{m.total}</td>
                    <td className="px-3 py-2">{m.pending}</td>
                    <td className="px-3 py-2">{pct(m.acceptance_rate)}</td>
                    <td className="px-3 py-2">{pct(m.override_rate)}</td>
                    <td className="px-3 py-2">{pct(m.fallback_rate)}</td>
                    <td className="px-3 py-2">{m.avg_confidence ?? "—"}</td>
                    <td className="px-3 py-2">{m.avg_latency_ms} ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Recommendation log">
        <div className="mb-3">
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="rounded-md border border-white/10 bg-navy-800 px-3 py-1.5 text-xs text-ink-primary"
          >
            <option value="">All</option>
            <option value="pending">Awaiting human decision</option>
            <option value="accepted">Accepted</option>
            <option value="rejected">Rejected</option>
            <option value="overridden">Overridden</option>
          </select>
        </div>
        <div className="space-y-3">
          {rows.map((rec) => (
            <div key={rec.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-xs">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <p className="font-semibold text-ink-primary">
                  {rec.feature} · {rec.model_name}
                  {rec.model_version ? ` v${rec.model_version}` : ""}
                </p>
                <div className="flex items-center gap-2">
                  {rec.is_fallback && <Badge variant="gold">fallback / rule-based</Badge>}
                  <Badge variant={DISPOSITION[rec.disposition] ?? "neutral"}>{rec.disposition}</Badge>
                </div>
              </div>
              <p className="mt-1 text-ink-secondary">
                {new Date(rec.created_at).toLocaleString()} · by {rec.requested_by_name ?? "—"} · confidence{" "}
                {rec.confidence ?? "n/a"} · {rec.latency_ms} ms
              </p>
              <p className="mt-1 text-ink-secondary">Why: {rec.reason}</p>
              <p className="text-ink-secondary">
                Sources: {rec.sources.length ? JSON.stringify(rec.sources).slice(0, 200) : "none cited"}
              </p>
              <button type="button" className="mt-1 text-emerald-400" onClick={() => setOpen(open === rec.id ? null : rec.id)}>
                {open === rec.id ? "Hide prompt & output" : "Show prompt & output"}
              </button>
              {open === rec.id && (
                <pre className="mt-2 max-h-64 overflow-auto rounded bg-navy-950 p-2 text-[10px] text-ink-secondary">
                  {`PROMPT (sha256 ${rec.prompt_hash.slice(0, 16)}...)\n${rec.prompt_text}\n\nOUTPUT\n${JSON.stringify(rec.output, null, 2)}`}
                </pre>
              )}
              {rec.disposition === "pending" && !mayDecide ? (
                <p className="mt-2 text-ink-secondary">Awaiting a human decision by the responsible reviewer.</p>
              ) : rec.disposition === "pending" ? (
                <div className="mt-2 flex gap-4">
                  <button type="button" className="text-emerald-400" onClick={() => void decide(rec, "accepted")}>
                    Accept
                  </button>
                  <button type="button" className="text-amber-300" onClick={() => void decide(rec, "overridden")}>
                    Override
                  </button>
                  <button type="button" className="text-red-400" onClick={() => void decide(rec, "rejected")}>
                    Reject
                  </button>
                </div>
              ) : (
                <p className="mt-2 text-ink-secondary">
                  Decision by {rec.disposed_by_name}: {rec.disposition_note || "no note"}
                </p>
              )}
            </div>
          ))}
          {rows.length === 0 && <p className="text-sm text-ink-secondary">Nothing recorded.</p>}
        </div>
      </Card>
    </div>
  )
}
