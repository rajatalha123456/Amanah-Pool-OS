import { useState } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Badge } from "../../components/Badge"
import { Spinner } from "../../components/Spinner"
import { useAuth } from "../../api/auth"
import { approveShariahDecision, castShariahQuorumVote } from "../../api/shariahGovernance"
import { extractErrorMessage } from "../../api/errors"
import type { BadgeVariant, ShariahDecision } from "../../types"

interface ShariahDecisionDetailModalProps {
  decision: ShariahDecision
  onClose: () => void
  onApproved: (updated: ShariahDecision) => void
  onEdit?: (decision: ShariahDecision) => void
  onDelete?: (decision: ShariahDecision) => void
}

function decisionStatusBadgeVariant(status: string): BadgeVariant {
  switch (status) {
    case "approved":
      return "emerald"
    case "draft":
      return "gold"
    case "superseded":
      return "neutral"
    default:
      return "neutral"
  }
}

function formatCategoryLabel(type: string): string {
  switch (type) {
    case "product_approval":
      return "Product Approval"
    case "policy_ruling":
      return "Policy Ruling"
    case "annual_review":
      return "Annual Review"
    case "purification_directive":
      return "Purification Directive"
    case "exemption":
      return "Exemption"
    default:
      return type
  }
}

const SCHOLAR_PRESETS = [
  { name: "Mufti Muhammad Taqi Usmani", title: "Chairman Shariah Board" },
  { name: "Mufti Muhammad Zubair Usmani", title: "Resident Shariah Board Member (RSBM)" },
  { name: "Dr. Muhammad Imran Ashraf Usmani", title: "Member Shariah Board" },
]

export function ShariahDecisionDetailModal({
  decision: initialDecision,
  onClose,
  onApproved,
  onEdit,
  onDelete,
}: ShariahDecisionDetailModalProps) {
  const { user } = useAuth()
  const [decision, setDecision] = useState<ShariahDecision>(initialDecision)
  const [isApproving, setIsApproving] = useState(false)
  const [isCastingVote, setIsCastingVote] = useState(false)
  const [showSignForm, setShowSignForm] = useState(false)
  const [error, setError] = useState("")

  // Sign Form State
  const [selectedScholar, setSelectedScholar] = useState(SCHOLAR_PRESETS[1])
  const [fiqhNotes, setFiqhNotes] = useState("Concurred under AAOIFI FAS 13 & SBP Shariah Governance Framework.")
  const [voteDecision, setVoteDecision] = useState<"approve" | "reject">("approve")

  const isBoardMember = user?.role === "shariah_board"
  const canManage =
    user?.role === "shariah_board" ||
    user?.role === "shariah_secretariat" ||
    user?.role === "platform_super_admin"
  const isDraft = decision.status === "draft"
  const canDelete =
    isDraft
      ? canManage
      : user?.role === "shariah_board" || user?.role === "platform_super_admin"

  const quorumSummary = decision.quorum_summary ?? {
    required_votes: 2,
    approvals: decision.quorum_votes?.filter((v) => v.decision_vote === "approve").length ?? 0,
    rejections: decision.quorum_votes?.filter((v) => v.decision_vote === "reject").length ?? 0,
    is_quorum_met: decision.status === "approved",
    status_label: `${decision.quorum_votes?.filter((v) => v.decision_vote === "approve").length ?? 0}/2 Signatures Collected`,
  }

  async function handleLegacyApprove() {
    setError("")
    setIsApproving(true)
    try {
      const updated = await approveShariahDecision(decision.id)
      setDecision(updated)
      onApproved(updated)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to approve this decision."))
    } finally {
      setIsApproving(false)
    }
  }

  async function handleCastSignature() {
    setError("")
    setIsCastingVote(true)
    try {
      const updated = await castShariahQuorumVote(decision.id, {
        scholar_name: selectedScholar.name,
        scholar_title: selectedScholar.title,
        vote: voteDecision,
        fiqh_opinion_notes: fiqhNotes,
      })
      setDecision(updated)
      setShowSignForm(false)
      onApproved(updated)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to record Shariah quorum signature."))
    } finally {
      setIsCastingVote(false)
    }
  }

  return (
    <Modal title={`Fatwa Ruling — ${decision.decision_code}`} onClose={onClose} maxWidth="max-w-2xl">
      <div className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
        {/* Header Status & Classification */}
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <Badge variant={decisionStatusBadgeVariant(decision.status)}>
              {decision.status.toUpperCase()}
            </Badge>
            <span className="rounded bg-navy-800 px-2.5 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/20">
              {formatCategoryLabel(decision.decision_type)}
            </span>
          </div>
          <span className="text-xs text-ink-muted">
            Effective: <strong>{decision.effective_date}</strong>
            {decision.expiry_date && ` • Expiry: ${decision.expiry_date}`}
          </span>
        </div>

        {/* Title */}
        <div>
          <h3 className="text-base font-semibold text-ink-primary">{decision.title}</h3>
        </div>

        {/* Meeting & Signatories */}
        {(decision.meeting_reference || decision.scholars_signatories) && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 rounded-lg border border-white/5 bg-navy-800/60 p-3 text-xs">
            {decision.meeting_reference && (
              <div>
                <span className="block text-ink-muted font-medium uppercase tracking-wider">Board Meeting Ref</span>
                <span className="text-ink-primary">{decision.meeting_reference}</span>
              </div>
            )}
            {decision.scholars_signatories && (
              <div>
                <span className="block text-ink-muted font-medium uppercase tracking-wider">Signatory Scholars</span>
                <span className="text-ink-primary">{decision.scholars_signatories}</span>
              </div>
            )}
          </div>
        )}

        {/* Arabic Fatwa Text */}
        {decision.fatwa_arabic_text && (
          <div className="rounded-lg border border-white/10 bg-navy-900/80 p-3 text-right">
            <span className="block text-left text-[11px] font-medium text-ink-muted uppercase tracking-wider mb-1">
              Arabic Fatwa Pronouncement
            </span>
            <p className="text-sm font-serif leading-loose text-emerald-300" dir="rtl">
              {decision.fatwa_arabic_text}
            </p>
          </div>
        )}

        {/* Description */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-muted mb-1">Ruling Description</h4>
          <p className="text-xs text-ink-secondary leading-relaxed bg-navy-800/30 p-3 rounded border border-white/5 whitespace-pre-wrap">
            {decision.description}
          </p>
        </div>

        {/* Fiqh / Regulatory Standards */}
        {decision.fiqh_reference && (
          <div className="rounded-lg border border-emerald-500/10 bg-emerald-500/5 p-3 text-xs">
            <span className="block font-medium text-emerald-400 uppercase tracking-wider mb-0.5">
              Governing Fiqh & AAOIFI Standards
            </span>
            <p className="text-ink-primary">{decision.fiqh_reference}</p>
          </div>
        )}

        {/* ========================================================================= */}
        {/* SBP SHARIAH BOARD MULTI-MUFTI QUORUM VOTING TRACKER (BRD MODULE 10)       */}
        {/* ========================================================================= */}
        <div className="rounded-xl border border-emerald-500/30 bg-navy-950 p-4 space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-white/8">
            <div>
              <span className="text-[10px] font-bold tracking-widest text-emerald-400 uppercase">
                SBP SHARIAH GOVERNANCE FRAMEWORK
              </span>
              <h4 className="text-xs font-bold text-white">Board Quorum Sign-Off Tracker</h4>
            </div>
            <Badge variant={decision.status === "approved" ? "emerald" : "gold"}>
              {decision.status === "approved" ? "QUORUM RATIFIED & SEALED" : quorumSummary.status_label}
            </Badge>
          </div>

          {/* Quorum Progress Bar */}
          <div>
            <div className="flex justify-between text-[11px] text-ink-muted mb-1">
              <span>Required Quorum: 2 of 3 Resident/External Scholars</span>
              <span className="font-mono text-emerald-400">{quorumSummary.approvals}/2 Signatures</span>
            </div>
            <div className="w-full h-2 rounded-full bg-navy-800 overflow-hidden border border-white/5">
              <div
                className="h-full bg-emerald-500 transition-all duration-500"
                style={{ width: `${Math.min(100, (quorumSummary.approvals / 2) * 100)}%` }}
              />
            </div>
          </div>

          {/* Recorded Scholar Signatures */}
          <div className="space-y-2 pt-1">
            {decision.quorum_votes && decision.quorum_votes.length > 0 ? (
              decision.quorum_votes.map((vote) => (
                <div
                  key={vote.id}
                  className="rounded-lg border border-white/8 bg-navy-900/90 p-3 text-xs space-y-1.5"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="font-bold text-white">{vote.scholar_name}</span>
                      <span className="block text-[10px] text-ink-muted">{vote.scholar_title}</span>
                    </div>
                    <Badge variant={vote.decision_vote === "approve" ? "emerald" : "navy"}>
                      {vote.decision_vote.toUpperCase()}
                    </Badge>
                  </div>
                  {vote.fiqh_concurrence_notes && (
                    <p className="text-[11px] text-ink-secondary italic bg-navy-950 p-2 rounded border border-white/5">
                      "{vote.fiqh_concurrence_notes}"
                    </p>
                  )}
                  <div className="flex items-center justify-between text-[10px] text-ink-muted pt-1 border-t border-white/5 font-mono">
                    <span className="truncate max-w-[280px]" title={vote.digital_signature_hash}>
                      SHA256: {vote.digital_signature_hash.slice(0, 16)}...{vote.digital_signature_hash.slice(-8)}
                    </span>
                    <span>{new Date(vote.voted_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))
            ) : (
              <p className="text-xs text-ink-muted py-2 text-center">
                No scholar quorum signatures recorded yet. Minimum 2 signatures required to seal this ruling.
              </p>
            )}
          </div>

          {/* Cast Scholar Signature Form / CTA */}
          {decision.status !== "approved" && isBoardMember && (
            <div className="pt-2 border-t border-white/8">
              {!showSignForm ? (
                <Button
                  variant="gold"
                  className="w-full text-xs font-semibold py-2"
                  onClick={() => setShowSignForm(true)}
                >
                  ✍️ Cast Scholar Digital Signature for Quorum
                </Button>
              ) : (
                <div className="rounded-lg border border-amber-500/30 bg-navy-900 p-3 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-amber-300">
                      Sign As Shariah Board Scholar
                    </span>
                    <button
                      type="button"
                      onClick={() => setShowSignForm(false)}
                      className="text-ink-muted hover:text-white text-xs"
                    >
                      ✕ Cancel
                    </button>
                  </div>

                  <div>
                    <label className="block text-[10px] uppercase font-semibold text-ink-muted mb-1">
                      Select Signatory Scholar Identity:
                    </label>
                    <select
                      className="w-full rounded border border-white/10 bg-navy-800 p-2 text-xs text-white"
                      value={selectedScholar.name}
                      onChange={(e) => {
                        const chosen = SCHOLAR_PRESETS.find((s) => s.name === e.target.value)
                        if (chosen) setSelectedScholar(chosen)
                      }}
                    >
                      {SCHOLAR_PRESETS.map((s) => (
                        <option key={s.name} value={s.name}>
                          {s.name} — {s.title}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-[10px] uppercase font-semibold text-ink-muted mb-1">
                      Fiqh Concurrence Notes / Dissenting Opinion:
                    </label>
                    <textarea
                      rows={2}
                      className="w-full rounded border border-white/10 bg-navy-800 p-2 text-xs text-ink-primary"
                      value={fiqhNotes}
                      onChange={(e) => setFiqhNotes(e.target.value)}
                    />
                  </div>

                  <div className="flex items-center justify-between pt-1">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setVoteDecision("approve")}
                        className={`px-2.5 py-1 text-xs rounded font-semibold ${
                          voteDecision === "approve"
                            ? "bg-emerald-500 text-white"
                            : "bg-navy-800 text-ink-muted"
                        }`}
                      >
                        ✓ Concur (Approve)
                      </button>
                      <button
                        type="button"
                        onClick={() => setVoteDecision("reject")}
                        className={`px-2.5 py-1 text-xs rounded font-semibold ${
                          voteDecision === "reject"
                            ? "bg-rose-500 text-white"
                            : "bg-navy-800 text-ink-muted"
                        }`}
                      >
                        ✕ Dissent (Reject)
                      </button>
                    </div>

                    <Button
                      variant="primary"
                      className="text-xs"
                      disabled={isCastingVote}
                      onClick={handleCastSignature}
                    >
                      {isCastingVote ? <Spinner className="h-4 w-4" /> : "⚡ Cryptographically Sign & Seal"}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {/* Footer Actions */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-3 border-t border-white/10">
          <div className="flex items-center gap-2">
            {canDelete && onDelete && (
              <button
                type="button"
                onClick={() => onDelete(decision)}
                className="text-xs text-red-400 hover:text-red-300 transition-colors px-2.5 py-1.5 rounded hover:bg-red-500/10 border border-red-500/20"
              >
                Delete Ruling
              </button>
            )}
            {canManage && onEdit && (
              <Button variant="secondary" onClick={() => onEdit(decision)}>
                Edit Ruling
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button variant="secondary" onClick={onClose} disabled={isApproving}>
              Close
            </Button>
            {decision.status === "draft" && isBoardMember && (
              <Button variant="primary" className="text-xs font-semibold px-3 py-1.5" disabled={isApproving} onClick={handleLegacyApprove}>
                {isApproving ? <Spinner className="h-4 w-4" /> : "✓ Approve Ruling"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  )
}
