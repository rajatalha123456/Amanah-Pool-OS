import { useEffect, useState, type FormEvent } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { transferAsset } from "../../api/assets"
import { extractErrorMessage } from "../../api/errors"
import { fetchPools } from "../../api/pools"
import type { Pool } from "../../types"

const INPUT =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const LABEL = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

/** Effective-dated move of an asset to another pool (BRD asset transfer controls). */
export function TransferAssetModal({
  assignmentId,
  fromPoolId,
  onClose,
  onTransferred,
}: {
  assignmentId: string
  fromPoolId: string
  onClose: () => void
  onTransferred: () => void
}) {
  const [pools, setPools] = useState<Pool[]>([])
  const [toPool, setToPool] = useState("")
  const [effectiveDate, setEffectiveDate] = useState("")
  const [reason, setReason] = useState("")
  const [error, setError] = useState("")
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    fetchPools()
      .then((all) => setPools(all.filter((p) => p.id !== fromPoolId)))
      .catch(() => setError("Failed to load pools"))
  }, [fromPoolId])

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError("")
    try {
      await transferAsset(assignmentId, { to_pool: toPool, effective_date: effectiveDate, reason })
      onTransferred()
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to transfer the asset."))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title="Transfer Asset" onClose={onClose}>
      <form onSubmit={submit} className="space-y-4">
        <p className="text-xs text-ink-secondary">
          The asset leaves this pool the day before the effective date and joins the destination pool on it.
        </p>
        <div>
          <label className={LABEL}>Destination pool</label>
          <select required value={toPool} onChange={(e) => setToPool(e.target.value)} className={INPUT}>
            <option value="">Select a pool</option>
            {pools.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code} - {p.name}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={LABEL}>Effective date</label>
          <input required type="date" value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} className={INPUT} />
        </div>
        <div>
          <label className={LABEL}>Reason</label>
          <textarea required rows={2} value={reason} onChange={(e) => setReason(e.target.value)} className={INPUT} />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="flex justify-end gap-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={busy}>
            {busy ? "Transferring..." : "Transfer"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
