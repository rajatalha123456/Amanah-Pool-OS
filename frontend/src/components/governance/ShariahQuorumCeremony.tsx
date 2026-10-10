import { useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import { Modal } from "../Modal"
import { castShariahQuorumVote } from "../../api/shariahGovernance"
import { extractErrorMessage } from "../../api/errors"
import type { ShariahDecision, ShariahQuorumVote } from "../../types"

interface ShariahQuorumCeremonyProps {
  decisions: ShariahDecision[]
  onDecisionUpdated: (updated: ShariahDecision) => void
}

interface ScholarProfile {
  name: string
  title: string
  role: string
  institution: string
  avatar: string
}

const SSB_SCHOLARS: ScholarProfile[] = [
  {
    name: "Mufti Muhammad Taqi Usmani",
    title: "Chairman, Shariah Supervisory Board",
    role: "Chairman & Lead Jurist",
    institution: "Former Vice President, Darul Uloom Karachi & Chairman AAOIFI Shariah Board",
    avatar: "👳‍♂️",
  },
  {
    name: "Mufti Najeeb Khan",
    title: "Resident Shariah Board Member (RSBM)",
    role: "Resident Executive Jurist",
    institution: "Full-Time Shariah Oversight & Transaction Attestation",
    avatar: "📜",
  },
  {
    name: "Mufti Hassan Kaleem",
    title: "Independent External Shariah Scholar",
    role: "External Reviewer & Audit Jurist",
    institution: "Independent Member, SBP Shariah Advisory Committee",
    avatar: "⚖️",
  },
]

export function ShariahQuorumCeremony({ decisions, onDecisionUpdated }: ShariahQuorumCeremonyProps) {
  // Default to first draft decision or first decision
  const [selectedDecisionId, setSelectedDecisionId] = useState<string>(() => {
    const draft = decisions.find((d) => d.status === "draft")
    return draft ? draft.id : decisions[0]?.id || ""
  })

  // Vote Modal State
  const [votingScholar, setVotingScholar] = useState<ScholarProfile | null>(null)
  const [voteChoice, setVoteChoice] = useState<"approve" | "reject">("approve")
  const [fiqhNotes, setFiqhNotes] = useState(
    "Reviewed under AAOIFI Shariah Standard No. 13 (Clause 8/5) and SBP IBD Circular 03/2012. Shariah concurrence granted unconditionally.",
  )
  const [isSubmittingVote, setIsSubmittingVote] = useState(false)
  const [voteError, setVoteError] = useState<string | null>(null)
  const [copySuccess, setCopySuccess] = useState(false)

  const activeDecision = decisions.find((d) => d.id === selectedDecisionId)

  // Map existing votes
  const votes = activeDecision?.quorum_votes || []
  const votesByScholarName: Record<string, ShariahQuorumVote> = {}
  for (const v of votes) {
    votesByScholarName[v.scholar_name.toLowerCase()] = v
  }

  const approvalCount = votes.filter((v) => v.decision_vote === "approve").length
  const requiredVotes = activeDecision?.quorum_summary?.required_votes || 2
  const isQuorumAchieved = approvalCount >= requiredVotes || activeDecision?.status === "approved"

  const handleOpenVoteModal = (scholar: ScholarProfile) => {
    setVotingScholar(scholar)
    setVoteChoice("approve")
    setVoteError(null)
    setFiqhNotes(
      scholar.name.includes("Chairman") || scholar.name.includes("Taqi")
        ? "الحمد لله رب العالمين. بعد دراسة المعاملة والاطلاع على تفاصيلها الفنية، تقرر الهيئة إجازة هذه المعاملة وفق الضوابط الشرعية المعتمدة."
        : "Reviewed in detail. The mechanism avoids contractual obligation and conforms to Shariah principles. Concurrence recorded.",
    )
  }

  const handleSubmitVote = async () => {
    if (!activeDecision || !votingScholar) return
    setIsSubmittingVote(true)
    setVoteError(null)

    try {
      const updated = await castShariahQuorumVote(activeDecision.id, {
        scholar_name: votingScholar.name,
        scholar_title: votingScholar.title,
        vote: voteChoice,
        fiqh_opinion_notes: fiqhNotes,
      })
      onDecisionUpdated(updated)
      setVotingScholar(null)
    } catch (err) {
      setVoteError(extractErrorMessage(err, "Failed to record quorum vote."))
    } finally {
      setIsSubmittingVote(false)
    }
  }

  if (decisions.length === 0) {
    return (
      <Card>
        <div className="py-12 text-center text-sm text-ink-muted">
          No Shariah rulings or decisions found. Create a decision in the Fatwa Register to begin the Quorum ceremony.
        </div>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      {/* Top Selector & Quorum Gauge Card */}
      <Card
        title="Shariah Supervisory Board Quorum & Digital Fatwa Seal (Screen 24)"
        actions={
          <div className="flex items-center gap-3">
            <span className="text-xs text-ink-muted">Select Ruling:</span>
            <select
              value={selectedDecisionId}
              onChange={(e) => setSelectedDecisionId(e.target.value)}
              className="bg-navy-900 border border-white/15 rounded px-3 py-1.5 text-xs text-ink-primary font-medium focus:outline-none focus:border-emerald-500 max-w-xs"
            >
              {decisions.map((d) => (
                <option key={d.id} value={d.id}>
                  [{d.decision_code}] {d.title.slice(0, 45)}... ({d.status.toUpperCase()})
                </option>
              ))}
            </select>
          </div>
        }
      >
        {activeDecision && (
          <div className="space-y-4">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-4 rounded-lg bg-navy-950/70 border border-white/10">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-500/30">
                    {activeDecision.decision_code}
                  </span>
                  <span className="text-sm font-bold text-ink-primary">{activeDecision.title}</span>
                  {activeDecision.status === "approved" ? (
                    <Badge variant="emerald">FATWA SEALED & RATIFIED</Badge>
                  ) : (
                    <Badge variant="gold">QUORUM SIGNING IN PROGRESS</Badge>
                  )}
                </div>
                <div className="text-xs text-ink-secondary">
                  Fiqh Standard: <span className="text-ink-primary font-medium">{activeDecision.fiqh_reference || "AAOIFI Shariah Standards"}</span> | Meeting Ref: <span className="font-mono">{activeDecision.meeting_reference || "SSB-2026-Q3"}</span>
                </div>
                <p className="text-xs text-ink-muted mt-1 max-w-3xl line-clamp-2">
                  {activeDecision.description}
                </p>
              </div>

              <div className="flex flex-col items-end gap-1.5 min-w-[200px]">
                <div className="text-xs font-semibold text-ink-primary flex items-center gap-1.5">
                  <span>Quorum Status:</span>
                  <span className={isQuorumAchieved ? "text-emerald-400 font-bold" : "text-amber-400 font-bold"}>
                    {approvalCount} of {requiredVotes} Required Signatures
                  </span>
                </div>
                <div className="w-full bg-navy-900 rounded-full h-2 overflow-hidden border border-white/10">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      isQuorumAchieved ? "bg-emerald-500" : "bg-amber-400"
                    }`}
                    style={{ width: `${Math.min(100, (approvalCount / requiredVotes) * 100)}%` }}
                  />
                </div>
                <span className="text-[10px] text-ink-muted">
                  Consensus Rule: SBP 2/3 Super-Majority Required
                </span>
              </div>
            </div>
          </div>
        )}
      </Card>

      {/* 3 Mufti Quorum Board Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {SSB_SCHOLARS.map((scholar, idx) => {
          // Check if this scholar has already cast a vote
          const existingVote = votes.find(
            (v) =>
              v.scholar_name.toLowerCase().includes(scholar.name.toLowerCase().split(" ")[1] || "") ||
              scholar.name.toLowerCase().includes(v.scholar_name.toLowerCase()),
          )
          const hasVoted = Boolean(existingVote)
          const isApproved = existingVote?.decision_vote === "approve"

          return (
            <div
              key={idx}
              className={`rounded-xl border transition-all p-5 flex flex-col justify-between space-y-4 ${
                hasVoted
                  ? isApproved
                    ? "border-emerald-500/40 bg-emerald-950/10 shadow-lg shadow-emerald-950/20"
                    : "border-red-500/40 bg-red-950/10"
                  : "border-white/10 bg-navy-900 hover:border-white/20"
              }`}
            >
              <div className="space-y-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-3xl p-2 rounded-lg bg-navy-950 border border-white/10">{scholar.avatar}</span>
                    <div>
                      <h4 className="text-sm font-bold text-ink-primary">{scholar.name}</h4>
                      <p className="text-xs text-emerald-400 font-medium">{scholar.title}</p>
                    </div>
                  </div>
                  {hasVoted ? (
                    isApproved ? (
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                        ✓ APPROVED
                      </span>
                    ) : (
                      <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-bold bg-red-500/20 text-red-300 border border-red-500/30">
                        ✕ REJECTED
                      </span>
                    )
                  ) : (
                    <Badge variant="neutral">PENDING VOTE</Badge>
                  )}
                </div>

                <div className="text-[11px] text-ink-muted">
                  <div className="font-semibold text-ink-secondary">{scholar.role}</div>
                  <div>{scholar.institution}</div>
                </div>

                {hasVoted && existingVote ? (
                  <div className="p-3 rounded bg-navy-950/80 border border-white/5 space-y-2 text-xs">
                    <div className="flex items-center justify-between text-[10px] text-ink-muted">
                      <span>Digital Seal Timestamp:</span>
                      <span className="font-mono">{new Date(existingVote.voted_at).toLocaleString()}</span>
                    </div>
                    {existingVote.fiqh_concurrence_notes && (
                      <div className="text-[11px] text-ink-secondary italic bg-white/5 p-2 rounded border border-white/5">
                        "{existingVote.fiqh_concurrence_notes}"
                      </div>
                    )}
                    <div className="pt-1">
                      <div className="text-[10px] text-ink-muted uppercase">SHA-256 Signature Stamp:</div>
                      <div className="font-mono text-[10px] text-emerald-400 break-all select-all">
                        {existingVote.digital_signature_hash}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="p-3 rounded bg-navy-950/40 border border-dashed border-white/10 text-center py-6 text-xs text-ink-muted">
                    Awaiting Shariah concurrence and digital signature.
                  </div>
                )}
              </div>

              {!hasVoted && (
                <Button
                  variant="primary"
                  className="w-full text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                  onClick={() => handleOpenVoteModal(scholar)}
                >
                  ✍️ Cast Scholar Vote & Sign
                </Button>
              )}
            </div>
          )
        })}
      </div>

      {/* Official Sealed Fatwa Certificate Display (When Quorum Achieved) */}
      {isQuorumAchieved && activeDecision && (
        <Card title="Official Shariah Supervisory Board Fatwa Certificate (Seal of Approval)">
          <div className="p-6 rounded-xl bg-gradient-to-b from-navy-900 to-navy-950 border border-emerald-500/30 shadow-2xl space-y-6">
            {/* Calligraphic Bismillah */}
            <div className="text-center space-y-2">
              <div className="text-xl md:text-2xl font-serif text-emerald-400 font-bold tracking-widest font-arabic">
                بِسْمِ اللَّهِ الرَّحْمَٰنِ الرَّحِيمِ
              </div>
              <div className="text-xs uppercase tracking-widest text-ink-muted">
                State Bank of Pakistan • Islamic Banking Shariah Governance Framework (SGF-2015)
              </div>
              <h2 className="text-lg md:text-xl font-bold text-ink-primary">
                SHARIAH SUPERVISORY BOARD FATWA & RESOLUTION CERTIFICATE
              </h2>
              <div className="text-xs font-mono text-emerald-400">
                FATWA REFERENCE CODE: {activeDecision.decision_code}
              </div>
            </div>

            {/* Arabic Fatwa Text */}
            {activeDecision.fatwa_arabic_text && (
              <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-500/20 text-right leading-loose font-arabic text-sm md:text-base text-emerald-100 shadow-inner">
                {activeDecision.fatwa_arabic_text}
              </div>
            )}

            {/* English / Urdu Fiqh Ruling Description */}
            <div className="p-4 rounded-lg bg-white/5 border border-white/5 space-y-2 text-xs text-ink-secondary">
              <div className="font-bold text-ink-primary uppercase text-[11px] tracking-wider">
                Operative Ruling & Fiqh Concurrence:
              </div>
              <p className="leading-relaxed">{activeDecision.description}</p>
              {activeDecision.mandatory_caveats && (
                <div className="mt-3 pt-3 border-t border-white/10 space-y-1">
                  <div className="font-semibold text-amber-300">Mandatory Shariah Caveats & Governance Controls:</div>
                  <pre className="text-xs font-sans whitespace-pre-line text-ink-muted">
                    {activeDecision.mandatory_caveats}
                  </pre>
                </div>
              )}
            </div>

            {/* Quorum Signatories Matrix */}
            <div className="border-t border-b border-white/10 py-4">
              <div className="text-xs font-bold text-ink-primary uppercase tracking-wider mb-3">
                Certified Digital Signatories (Shariah Board Quorum):
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {SSB_SCHOLARS.map((s, i) => {
                  const voteMatch = votes.find(
                    (v) =>
                      v.scholar_name.toLowerCase().includes(s.name.toLowerCase().split(" ")[1] || "") ||
                      s.name.toLowerCase().includes(v.scholar_name.toLowerCase()),
                  )
                  return (
                    <div key={i} className="p-3 bg-navy-950 rounded border border-white/5 text-xs space-y-1">
                      <div className="font-semibold text-emerald-400">{s.name}</div>
                      <div className="text-[10px] text-ink-muted">{s.title}</div>
                      <div className="text-[10px] font-mono text-emerald-300/80 pt-1">
                        {voteMatch ? `Seal: ${voteMatch.digital_signature_hash.slice(0, 16)}...` : "Seal: CERT-EX-OFFICIO"}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            {/* Golden Shariah Seal Badge & Actions */}
            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
              <div className="flex items-center gap-3">
                <span className="text-4xl">🏛️</span>
                <div>
                  <div className="font-bold text-sm text-gold-400">ختم الهيئة الشرعية المعتمد</div>
                  <div className="text-[11px] text-ink-muted">
                    Officially Ratified under AAOIFI FAS-30 and SBP IBD Regulations
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-3">
                <Button
                  variant="secondary"
                  className="text-xs"
                  onClick={() => {
                    const textToCopy = `FATWA CERTIFICATE: ${activeDecision.decision_code}\nTitle: ${activeDecision.title}\nFiqh Reference: ${activeDecision.fiqh_reference}\nStatus: APPROVED BY SHARIAH QUORUM\nArabic Fatwa: ${activeDecision.fatwa_arabic_text}\nMandatory Caveats: ${activeDecision.mandatory_caveats}`
                    navigator.clipboard.writeText(textToCopy)
                    setCopySuccess(true)
                    setTimeout(() => setCopySuccess(false), 2000)
                  }}
                >
                  {copySuccess ? "✓ Copied Memorandum" : "📋 Copy Official Fatwa Memo"}
                </Button>
                <Button
                  variant="primary"
                  className="text-xs bg-emerald-600 hover:bg-emerald-500 text-white"
                  onClick={() => window.print()}
                >
                  🖨️ Print / Export Certificate
                </Button>
              </div>
            </div>
          </div>
        </Card>
      )}

      {/* Cast Quorum Vote Modal */}
      {votingScholar && (
        <Modal
          isOpen={Boolean(votingScholar)}
          onClose={() => setVotingScholar(null)}
          title={`Shariah Board Quorum Sign-Off: ${votingScholar.name}`}
        >
          <div className="space-y-4 text-xs">
            <div className="p-3 rounded bg-navy-950 border border-white/10">
              <div className="font-bold text-ink-primary">{activeDecision?.decision_code}: {activeDecision?.title}</div>
              <div className="text-[11px] text-emerald-400 mt-0.5">{votingScholar.title}</div>
            </div>

            {voteError && (
              <div className="p-3 rounded bg-red-950/30 border border-red-500/30 text-red-300">
                {voteError}
              </div>
            )}

            <div>
              <label className="block text-ink-secondary font-semibold uppercase mb-1">
                Quorum Decision Vote *
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  type="button"
                  onClick={() => setVoteChoice("approve")}
                  className={`p-3 rounded border text-left transition ${
                    voteChoice === "approve"
                      ? "border-emerald-500 bg-emerald-950/20 text-emerald-300 font-bold"
                      : "border-white/10 bg-navy-950 text-ink-muted hover:border-white/20"
                  }`}
                >
                  <div className="text-sm">✓ APPROVE (موافق عليه)</div>
                  <div className="text-[10px] text-ink-muted mt-0.5">Concurrence under Shariah standards</div>
                </button>
                <button
                  type="button"
                  onClick={() => setVoteChoice("reject")}
                  className={`p-3 rounded border text-left transition ${
                    voteChoice === "reject"
                      ? "border-red-500 bg-red-950/20 text-red-300 font-bold"
                      : "border-white/10 bg-navy-950 text-ink-muted hover:border-white/20"
                  }`}
                >
                  <div className="text-sm">✕ REJECT (مرفوض)</div>
                  <div className="text-[10px] text-ink-muted mt-0.5">Non-compliant; return to Secretariat</div>
                </button>
              </div>
            </div>

            <div>
              <label className="block text-ink-secondary font-semibold uppercase mb-1">
                Fiqh Opinion, Concurrence Notes & Caveats
              </label>
              <textarea
                rows={4}
                value={fiqhNotes}
                onChange={(e) => setFiqhNotes(e.target.value)}
                className="w-full rounded border border-white/15 bg-navy-950 p-2 text-ink-primary focus:outline-none focus:border-emerald-500 text-xs"
              />
            </div>

            <div className="p-3 rounded bg-white/5 border border-white/5 text-[11px] text-ink-muted">
              By submitting this vote, a cryptographic SHA-256 hash stamp is irrevocably bound to your scholar profile in the immutable Shariah governance ledger.
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-white/10">
              <Button variant="secondary" onClick={() => setVotingScholar(null)} disabled={isSubmittingVote}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleSubmitVote}
                disabled={isSubmittingVote}
                className="bg-emerald-600 hover:bg-emerald-500 text-white"
              >
                {isSubmittingVote ? <Spinner className="h-4 w-4" /> : "Commit Digital Shariah Signature"}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
