import { useState, type FormEvent } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { createPurificationEntry } from "../../api/governance"
import { extractErrorMessage } from "../../api/errors"
import type { PurificationEntry } from "../../types"

interface NewPurificationEntryModalProps {
  poolId: string
  onClose: () => void
  onCreated: (entry: PurificationEntry) => void
}

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

export function NewPurificationEntryModal({ poolId, onClose, onCreated }: NewPurificationEntryModalProps) {
  const [sourceDescription, setSourceDescription] = useState("")
  const [amount, setAmount] = useState("")
  const [identifiedDate, setIdentifiedDate] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")
    setIsSubmitting(true)
    try {
      const entry = await createPurificationEntry({
        pool: poolId,
        source_description: sourceDescription,
        amount,
        identified_date: identifiedDate,
      })
      onCreated(entry)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to create purification entry."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="New Purification Entry" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="source-description" className={labelClasses}>
            Source Description
          </label>
          <input
            id="source-description"
            type="text"
            value={sourceDescription}
            onChange={(e) => setSourceDescription(e.target.value)}
            required
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="amount" className={labelClasses}>
            Amount
          </label>
          <input
            id="amount"
            type="number"
            step="0.01"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            required
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="identified-date" className={labelClasses}>
            Identified Date
          </label>
          <input
            id="identified-date"
            type="date"
            value={identifiedDate}
            onChange={(e) => setIdentifiedDate(e.target.value)}
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
