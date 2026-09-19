import { useState, type FormEvent } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { markDistributed } from "../../api/governance"
import { extractErrorMessage } from "../../api/errors"
import type { PurificationEntry } from "../../types"

interface MarkDistributedModalProps {
  entry: PurificationEntry
  onClose: () => void
  onDone: (updated: PurificationEntry) => void
}

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

export function MarkDistributedModal({ entry, onClose, onDone }: MarkDistributedModalProps) {
  const [charityRecipient, setCharityRecipient] = useState("")
  const [distributedDate, setDistributedDate] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!charityRecipient.trim() || !distributedDate) {
      setError("Charity recipient and distributed date are both required.")
      return
    }

    setError("")
    setIsSubmitting(true)
    try {
      const updated = await markDistributed(entry.id, charityRecipient, distributedDate)
      onDone(updated)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to mark this entry as distributed."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="Mark Distributed" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="charity-recipient" className={labelClasses}>
            Charity Recipient
          </label>
          <input
            id="charity-recipient"
            type="text"
            value={charityRecipient}
            onChange={(e) => setCharityRecipient(e.target.value)}
            required
            className={inputClasses}
          />
        </div>

        <div>
          <label htmlFor="distributed-date" className={labelClasses}>
            Distributed Date
          </label>
          <input
            id="distributed-date"
            type="date"
            value={distributedDate}
            onChange={(e) => setDistributedDate(e.target.value)}
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
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Mark Distributed"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
