import { useState, type FormEvent } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { createShariahDecision } from "../../api/shariahGovernance"
import { extractErrorMessage } from "../../api/errors"
import type { ShariahDecision, ShariahDecisionType } from "../../types"

interface NewShariahDecisionModalProps {
  onClose: () => void
  onCreated: (decision: ShariahDecision) => void
  /** Approved rulings this one may supersede. */
  approved?: ShariahDecision[]
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

export function NewShariahDecisionModal({ onClose, onCreated, approved = [] }: NewShariahDecisionModalProps) {
  const [decisionCode, setDecisionCode] = useState("")
  const [decisionType, setDecisionType] = useState<ShariahDecisionType>("product_approval")
  const [title, setTitle] = useState("")
  const [meetingReference, setMeetingReference] = useState("")
  const [scholarsSignatories, setScholarsSignatories] = useState("")
  const [fiqhReference, setFiqhReference] = useState("")
  const [fatwaArabicText, setFatwaArabicText] = useState("")
  const [description, setDescription] = useState("")
  const [mandatoryCaveats, setMandatoryCaveats] = useState("")
  const [effectiveDate, setEffectiveDate] = useState("")
  const [expiryDate, setExpiryDate] = useState("")
  const [documentUrl, setDocumentUrl] = useState("")
  const [scope, setScope] = useState("")
  const [supersedes, setSupersedes] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")
    setIsSubmitting(true)
    try {
      const decision = await createShariahDecision({
        decision_code: decisionCode,
        decision_type: decisionType,
        title,
        meeting_reference: meetingReference.trim() || undefined,
        scholars_signatories: scholarsSignatories.trim() || undefined,
        fiqh_reference: fiqhReference.trim() || undefined,
        fatwa_arabic_text: fatwaArabicText.trim() || undefined,
        description,
        mandatory_caveats: mandatoryCaveats.trim() || undefined,
        effective_date: effectiveDate,
        expiry_date: expiryDate.trim() || undefined,
        document_url: documentUrl.trim() || undefined,
        scope: scope.trim(),
        supersedes: supersedes || null,
      })
      onCreated(decision)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to create Shariah decision."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="Draft New Shariah Decision / Fatwa" onClose={onClose} maxWidth="max-w-2xl">
      <form onSubmit={handleSubmit} className="space-y-4 max-h-[80vh] overflow-y-auto pr-1">
        <div className="rounded-md border border-emerald-500/20 bg-emerald-500/5 p-3 text-xs text-ink-secondary">
          <p className="font-semibold text-emerald-400">Maker-Checker Compliance Rule (SBP & AAOIFI Standards)</p>
          <p className="mt-0.5">
            This fatwa ruling will be saved in <strong>Draft</strong> status. Under Islamic banking governance segregation, only an independent <strong>Shariah Board Member</strong> can formally review and approve it.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="decision-code" className={labelClasses}>
              Decision / Fatwa Code *
            </label>
            <input
              id="decision-code"
              type="text"
              value={decisionCode}
              onChange={(e) => setDecisionCode(e.target.value)}
              placeholder="e.g. FTW-2026-001 or SBD-2026-044"
              required
              className={inputClasses}
            />
          </div>

          <div>
            <label htmlFor="decision-type" className={labelClasses}>
              Ruling Category *
            </label>
            <select
              id="decision-type"
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
          <label htmlFor="scope" className={labelClasses}>
            Scope (what this ruling covers)
          </label>
          <input id="scope" value={scope} onChange={(e) => setScope(e.target.value)} className={inputClasses} placeholder="e.g. Retail Mudarabah and Wakalah pools" />
        </div>

        {approved.length > 0 && (
          <div>
            <label htmlFor="supersedes" className={labelClasses}>
              Supersedes (optional)
            </label>
            <select id="supersedes" value={supersedes} onChange={(e) => setSupersedes(e.target.value)} className={inputClasses}>
              <option value="">Does not replace an earlier ruling</option>
              {approved.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.decision_code} - {d.title}
                </option>
              ))}
            </select>
            <p className="mt-1 text-[11px] text-ink-muted">When this ruling is approved the earlier one is marked superseded and contracts follow the new ruling.</p>
          </div>
        )}

        <div>
          <label htmlFor="title" className={labelClasses}>
            Subject / Title *
          </label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="e.g. Mudarabah Retail Deposit Structure & PER Policy"
            required
            className={inputClasses}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="meeting-ref" className={labelClasses}>
              Board Meeting Reference
            </label>
            <input
              id="meeting-ref"
              type="text"
              value={meetingReference}
              onChange={(e) => setMeetingReference(e.target.value)}
              placeholder="e.g. SSB-54th-Meeting-Min-3.2"
              className={inputClasses}
            />
          </div>

          <div>
            <label htmlFor="scholars-signatories" className={labelClasses}>
              Signatory Scholars
            </label>
            <input
              id="scholars-signatories"
              type="text"
              value={scholarsSignatories}
              onChange={(e) => setScholarsSignatories(e.target.value)}
              placeholder="e.g. Mufti M. Taqi Usmani, Dr. Imran Usmani"
              className={inputClasses}
            />
          </div>
        </div>

        <div>
          <label htmlFor="fiqh-reference" className={labelClasses}>
            Fiqh & Regulatory Standard Reference
          </label>
          <input
            id="fiqh-reference"
            type="text"
            value={fiqhReference}
            onChange={(e) => setFiqhReference(e.target.value)}
            placeholder="e.g. AAOIFI Shariah Standard No. 13 (Mudarabah), SBP IBD Circular No. 02/2008"
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="fatwa-arabic-text" className={labelClasses}>
            Arabic Text / Nass al-Fatwa (نص الفتوى الشرعية)
          </label>
          <textarea
            id="fatwa-arabic-text"
            value={fatwaArabicText}
            onChange={(e) => setFatwaArabicText(e.target.value)}
            rows={2}
            dir="rtl"
            placeholder="يجوز شرعاً التعامل بهذا العقد وفقاً للضوابط الشرعية المعتمدة..."
            className={`${inputClasses} font-serif text-right`}
          />
        </div>

        <div>
          <label htmlFor="description" className={labelClasses}>
            Operative Shariah Ruling / Description *
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            rows={3}
            placeholder="Detailed description of the approval, structure, and operational requirements..."
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="mandatory-caveats" className={labelClasses}>
            Mandatory Caveats & Special Conditions
          </label>
          <textarea
            id="mandatory-caveats"
            value={mandatoryCaveats}
            onChange={(e) => setMandatoryCaveats(e.target.value)}
            rows={2}
            placeholder="e.g. 1. Quarterly Shariah audit mandatory. 2. Reserve allocation must not exceed 10% without prior Board re-approval."
            className={inputClasses}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label htmlFor="effective-date" className={labelClasses}>
              Effective Date *
            </label>
            <input
              id="effective-date"
              type="date"
              value={effectiveDate}
              onChange={(e) => setEffectiveDate(e.target.value)}
              required
              className={inputClasses}
            />
          </div>

          <div>
            <label htmlFor="expiry-date" className={labelClasses}>
              Expiry / Review Date (Optional)
            </label>
            <input
              id="expiry-date"
              type="date"
              value={expiryDate}
              onChange={(e) => setExpiryDate(e.target.value)}
              className={inputClasses}
            />
          </div>
        </div>

        <div>
          <label htmlFor="document-url" className={labelClasses}>
            Signed Fatwa Document Link (PDF / Document Repository)
          </label>
          <input
            id="document-url"
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
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Save Draft Ruling"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
