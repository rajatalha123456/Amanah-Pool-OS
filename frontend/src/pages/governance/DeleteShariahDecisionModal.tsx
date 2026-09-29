import { useState } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { deleteShariahDecision } from "../../api/shariahGovernance"
import { extractErrorMessage } from "../../api/errors"
import type { ShariahDecision } from "../../types"

interface DeleteShariahDecisionModalProps {
  decision: ShariahDecision
  onClose: () => void
  onDeleted: (deletedId: string) => void
}

export function DeleteShariahDecisionModal({
  decision,
  onClose,
  onDeleted,
}: DeleteShariahDecisionModalProps) {
  const [isDeleting, setIsDeleting] = useState(false)
  const [error, setError] = useState("")

  async function handleDelete() {
    setError("")
    setIsDeleting(true)
    try {
      await deleteShariahDecision(decision.id)
      onDeleted(decision.id)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to delete this Shariah decision."))
    } finally {
      setIsDeleting(false)
    }
  }

  return (
    <Modal title="Delete Shariah Ruling / Fatwa" onClose={onClose} maxWidth="max-w-md">
      <div className="space-y-4">
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-3.5 text-xs text-red-200">
          <p className="font-semibold text-red-400">Warning: Permanent Deletion</p>
          <p className="mt-1">
            You are about to delete <strong>{decision.decision_code}</strong> (&ldquo;{decision.title}&rdquo;).
          </p>
          <p className="mt-1 text-ink-muted">
            If this fatwa is actively linked to any Contract Templates, the system will block deletion to preserve contract referential integrity. An audit entry will be logged.
          </p>
        </div>

        {error && (
          <div className="rounded-md border border-red-500/40 bg-red-500/15 p-3 text-xs text-red-300">
            {error}
          </div>
        )}

        <div className="flex items-center justify-end gap-2 pt-2 border-t border-white/10">
          <Button variant="secondary" onClick={onClose} disabled={isDeleting}>
            Cancel
          </Button>
          <button
            type="button"
            disabled={isDeleting}
            onClick={handleDelete}
            className="inline-flex items-center justify-center rounded-lg bg-red-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-red-500 disabled:opacity-50 disabled:pointer-events-none"
          >
            {isDeleting ? <Spinner className="h-4 w-4" /> : "Confirm Delete"}
          </button>
        </div>
      </div>
    </Modal>
  )
}
