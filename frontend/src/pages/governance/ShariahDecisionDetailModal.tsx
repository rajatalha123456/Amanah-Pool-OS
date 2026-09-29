import { useState } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Badge } from "../../components/Badge"
import { Spinner } from "../../components/Spinner"
import { useAuth } from "../../api/auth"
import { approveShariahDecision } from "../../api/shariahGovernance"
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

export function ShariahDecisionDetailModal({
  decision,
  onClose,
  onApproved,
  onEdit,
  onDelete,
}: ShariahDecisionDetailModalProps) {
  const { user } = useAuth()
  const [isApproving, setIsApproving] = useState(false)
  const [error, setError] = useState("")

  const isBoardMember = user?.role === "shariah_board"
  const canManage =
    user?.role === "shariah_board" ||
    user?.role === "shariah_secretariat" ||
    user?.role === "platform_super_admin"
  const isDraft = decision.status === "draft"
  const isMaker = Boolean(decision.created_by && user?.id && decision.created_by === user.id)
  const canApprove = isBoardMember && isDraft && !isMaker
  const canDelete =
    isDraft
      ? canManage
      : user?.role === "shariah_board" || user?.role === "platform_super_admin"

  async function handleApprove() {
    setError("")
    setIsApproving(true)
    try {
      const updated = await approveShariahDecision(decision.id)
      onApproved(updated)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to approve this decision."))
    } finally {
      setIsApproving(false)
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

        {/* Fiqh / Regulatory Standards */}
        {decision.fiqh_reference && (
          <div className="rounded-lg border border-emerald-500/10 bg-emerald-500/5 p-3 text-xs">
            <span className="block font-semibold text-emerald-400 uppercase tracking-wider mb-1">
              Fiqh & Regulatory Standard Basis
            </span>
            <p className="text-ink-secondary">{decision.fiqh_reference}</p>
          </div>
        )}

        {/* Arabic Nass al-Fatwa */}
        {decision.fatwa_arabic_text && (
          <div className="rounded-lg border border-white/10 bg-navy-950/60 p-4 text-right" dir="rtl">
            <span className="block font-serif text-xs text-ink-muted mb-1 text-left" dir="ltr">
              نص القرار الشرعي (Arabic Text)
            </span>
            <p className="font-serif text-sm leading-relaxed text-emerald-200">
              {decision.fatwa_arabic_text}
            </p>
          </div>
        )}

        {/* Description / Ruling Text */}
        <div>
          <span className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1">
            Operative Shariah Ruling
          </span>
          <div className="rounded-lg border border-white/8 bg-navy-800/40 p-3 text-sm text-ink-primary whitespace-pre-wrap leading-relaxed">
            {decision.description}
          </div>
        </div>

        {/* Caveats & Conditions Precedent */}
        {decision.mandatory_caveats && (
          <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-3 text-xs">
            <span className="block font-semibold text-amber-400 uppercase tracking-wider mb-1">
              Mandatory Caveats & Special Conditions
            </span>
            <p className="text-ink-secondary whitespace-pre-wrap leading-relaxed">{decision.mandatory_caveats}</p>
          </div>
        )}

        {/* Document URL */}
        {decision.document_url && (
          <div className="text-xs">
            <span className="text-ink-muted">Signed Document Repository: </span>
            <a
              href={decision.document_url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-emerald-400 underline hover:text-emerald-300 break-all"
            >
              {decision.document_url}
            </a>
          </div>
        )}

        {/* Maker-Checker Audit Trail */}
        <div className="rounded-lg border border-white/8 bg-navy-950/40 p-3 text-xs space-y-1.5">
          <span className="block font-semibold text-ink-muted uppercase tracking-wider">
            Governance & Audit Sign-Off
          </span>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-ink-secondary pt-1">
            <div>
              <span className="text-ink-muted">Drafted By (Maker): </span>
              <span className="font-medium text-ink-primary">{decision.created_by_name || "System"}</span>
              <span className="block text-[11px] text-ink-muted">
                {new Date(decision.created_at).toLocaleString()}
              </span>
            </div>
            <div>
              <span className="text-ink-muted">Approved By (Checker): </span>
              {decision.approved_by_name ? (
                <>
                  <span className="font-medium text-emerald-400">{decision.approved_by_name}</span>
                  {decision.approved_at && (
                    <span className="block text-[11px] text-ink-muted">
                      {new Date(decision.approved_at).toLocaleString()}
                    </span>
                  )}
                </>
              ) : (
                <span className="font-medium text-amber-400">Pending Board Approval</span>
              )}
            </div>
          </div>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        {/* Maker Notice if logged in user is the maker */}
        {isMaker && isDraft && (
          <p className="text-xs text-amber-300/80 bg-amber-500/10 border border-amber-500/20 rounded p-2">
            Maker-Checker Segregation: You drafted this decision. As required by banking governance, another Shariah Board member must review and approve it.
          </p>
        )}

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
            {canApprove && (
              <Button variant="primary" disabled={isApproving} onClick={handleApprove}>
                {isApproving ? <Spinner className="h-4 w-4" /> : "Approve Fatwa Ruling"}
              </Button>
            )}
          </div>
        </div>
      </div>
    </Modal>
  )
}
