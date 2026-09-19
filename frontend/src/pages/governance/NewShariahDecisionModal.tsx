import { useState, type FormEvent } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { createShariahDecision } from "../../api/shariahGovernance"
import { extractErrorMessage } from "../../api/errors"
import type { ShariahDecision } from "../../types"

interface NewShariahDecisionModalProps {
  onClose: () => void
  onCreated: (decision: ShariahDecision) => void
}

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

export function NewShariahDecisionModal({ onClose, onCreated }: NewShariahDecisionModalProps) {
  const [decisionCode, setDecisionCode] = useState("")
  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [effectiveDate, setEffectiveDate] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")
    setIsSubmitting(true)
    try {
      const decision = await createShariahDecision({
        decision_code: decisionCode,
        title,
        description,
        effective_date: effectiveDate,
      })
      onCreated(decision)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to create Shariah decision."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="New Shariah Decision" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="decision-code" className={labelClasses}>
            Decision Code
          </label>
          <input
            id="decision-code"
            type="text"
            value={decisionCode}
            onChange={(e) => setDecisionCode(e.target.value)}
            required
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="title" className={labelClasses}>
            Title
          </label>
          <input
            id="title"
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="description" className={labelClasses}>
            Description
          </label>
          <textarea
            id="description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            rows={3}
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="effective-date" className={labelClasses}>
            Effective Date
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

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
