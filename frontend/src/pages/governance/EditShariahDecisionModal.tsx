import { useState, type FormEvent } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { updateShariahDecision } from "../../api/shariahGovernance"
import { extractErrorMessage } from "../../api/errors"
import type { ShariahDecision, ShariahDecisionType } from "../../types"

interface EditShariahDecisionModalProps {
  decision: ShariahDecision
  onClose: () => void
  onUpdated: (decision: ShariahDecision) => void
}

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none transition-colors"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

const DECISION_TYPES: { value: ShariahDecisionType; label: string }[] = [
  { value: "product_approval", label: "Product Approval" },
  { value: "policy_ruling", label: "Policy Ruling" },
  { value: "annual_review", label: "Annual Review" },
  { value: "purification_directive", label: "Purification Directive" },
  { value: "exemption", label: "Exemption" },
]

export function EditShariahDecisionModal({ decision, onClose, onUpdated }: EditShariahDecisionModalProps) {
  const [decisionCode, setDecisionCode] = useState(decision.decision_code)
  const [decisionType, setDecisionType] = useState<ShariahDecisionType>(decision.decision_type)
  const [title, setTitle] = useState(decision.title)
  const [meetingReference, setMeetingReference] = useState(decision.meeting_reference || "")
  const [scholarsSignatories, setScholarsSignatories] = useState(decision.scholars_signatories || "")
  const [fiqhReference, setFiqhReference] = useState(decision.fiqh_reference || "")
  const [fatwaArabicText, setFatwaArabicText] = useState(decision.fatwa_arabic_text || "")
  const [description, setDescription] = useState(decision.description)
  const [mandatoryCaveats, setMandatoryCaveats] = useState(decision.mandatory_caveats || "")
  const [effectiveDate, setEffectiveDate] = useState(decision.effective_date)
  const [expiryDate, setExpiryDate] = useState(decision.expiry_date || "")
  const [documentUrl, setDocumentUrl] = useState(decision.document_url || "")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")
    setIsSubmitting(true)
    try {
      const updated = await updateShariahDecision(decision.id, {
        decision_code: decisionCode,
        decision_type: decisionType,
        title,
        meeting_reference: meetingReference.trim() || null,
        scholars_signatories: scholarsSignatories.trim() || null,
        fiqh_reference: fiqhReference.trim() || null,
        fatwa_arabic_text: fatwaArabicText.trim() || null,
        description,
        mandatory_caveats: mandatoryCaveats.trim() || null,
        effective_date: effectiveDate,
        expiry_date: expiryDate.trim() || null,
        document_url: documentUrl.trim() || null,
      })
      onUpdated(updated)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to update Shariah decision."))
    } finally {
      setIsSubmitting(false)
    }
  }

  const isApproved = decision.status === "approved"

  return (
    <Modal title={`Edit Shariah Ruling — ${decision.decision_code}`} onClose={onClose} maxWidth="max-w-2xl">
      <form onSubmit={handleSubmit} className="space-y-4 max-h-[80vh] overflow-y-auto pr-1">
        {isApproved ? (
          <div className="rounded-md border border-amber-500/20 bg-amber-500/10 p-3 text-xs text-amber-300">
            <p className="font-semibold">Notice: Editing an Approved Ruling</p>
            <p className="mt-0.5 text-amber-200/80">
              This fatwa has already been approved. All edits will be logged with an immutable audit trail in the Auditor Portal.
            </p>
          </div>
        ) : (
          <div className="rounded-md border border-blue-500/20 bg-blue-500/10 p-3 text-xs text-blue-300">
            <p className="font-semibold">Draft Status: Pre-Approval Revisions</p>
            <p className="mt-0.5 text-blue-200/80">
              Update any operative text, Arabic phrasing, or references before final Shariah Board sign-off.
            </p>
          </div>
        )}

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="edit-decision-code" className={labelClasses}>
              Decision / Fatwa Code *
            </label>
            <input
              id="edit-decision-code"
              type="text"
              value={decisionCode}
              onChange={(e) => setDecisionCode(e.target.value)}
              required
              className={inputClasses}
            />
          </div>

          <div>
            <label htmlFor="edit-decision-type" className={labelClasses}>
              Ruling Category *
            </label>
            <select
              id="edit-decision-type"
              value={decisionType}
              onChange={(e) => setDecisionType(e.target.value as ShariahDecisionType)}
              required
              className={inputClasses}
            >
              {DECISION_TYPES.map((dt) => (
                <option key={dt.value} value={dt.value}>
                  {dt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="edit-title" className={labelClasses}>
            Subject / Title *
          </label>
          <input
            id="edit-title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className={inputClasses}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="edit-meeting-ref" className={labelClasses}>
              Board Meeting Reference
            </label>
            <input
              id="edit-meeting-ref"
              type="text"
              value={meetingReference}
              onChange={(e) => setMeetingReference(e.target.value)}
              placeholder="e.g. SSB-54th-Meeting-Min-3.2"
              className={inputClasses}
            />
          </div>

          <div>
            <label htmlFor="edit-scholars-signatories" className={labelClasses}>
              Signatory Scholars
            </label>
            <input
              id="edit-scholars-signatories"
              type="text"
              value={scholarsSignatories}
              onChange={(e) => setScholarsSignatories(e.target.value)}
              placeholder="e.g. Mufti M. Taqi Usmani, Dr. Imran Usmani"
              className={inputClasses}
            />
          </div>
        </div>

        <div>
          <label htmlFor="edit-fiqh-reference" className={labelClasses}>
            Fiqh & Regulatory Standard Reference
          </label>
          <input
            id="edit-fiqh-reference"
            type="text"
            value={fiqhReference}
            onChange={(e) => setFiqhReference(e.target.value)}
            placeholder="e.g. AAOIFI Shariah Standard No. 13 (Mudarabah), SBP IBD Circular No. 02/2008"
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="edit-fatwa-arabic-text" className={labelClasses}>
            Arabic Text / Nass al-Fatwa (نص الفتوى الشرعية)
          </label>
          <textarea
            id="edit-fatwa-arabic-text"
            value={fatwaArabicText}
            onChange={(e) => setFatwaArabicText(e.target.value)}
            rows={2}
            dir="rtl"
            placeholder="يجوز شرعاً التعامل بهذا العقد وفقاً للضوابط الشرعية المعتمدة..."
            className={`${inputClasses} font-serif text-right`}
          />
        </div>

        <div>
          <label htmlFor="edit-description" className={labelClasses}>
            Operative Shariah Ruling / Description *
          </label>
          <textarea
            id="edit-description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            rows={3}
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="edit-mandatory-caveats" className={labelClasses}>
            Mandatory Caveats & Special Conditions
          </label>
          <textarea
            id="edit-mandatory-caveats"
            value={mandatoryCaveats}
            onChange={(e) => setMandatoryCaveats(e.target.value)}
            rows={2}
            className={inputClasses}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="edit-effective-date" className={labelClasses}>
              Effective Date *
            </label>
            <input
              id="edit-effective-date"
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
              required
              className={inputClasses}
            />
          </div>

          <div>
            <label htmlFor="edit-expiry-date" className={labelClasses}>
              Expiry / Review Date (Optional)
            </label>
            <input
              id="edit-expiry-date"
              type="date"
              value={expiryDate}
              onChange={(e) => setExpiryDate(e.target.value)}
              className={inputClasses}
            />
          </div>
        </div>

        <div>
          <label htmlFor="edit-document-url" className={labelClasses}>
            Signed Fatwa Document Link (PDF / Document Repository)
          </label>
          <input
            id="edit-document-url"
            type="url"
            value={documentUrl}
            onChange={(e) => setDocumentUrl(e.target.value)}
            placeholder="https://docs.bank.test/fatwas/FTW-2026-001.pdf"
            className={inputClasses}
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2 border-t border-white/10">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Save Changes"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
