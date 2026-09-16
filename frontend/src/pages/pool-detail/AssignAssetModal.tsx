import { useEffect, useState, type FormEvent } from "react"
import { Modal } from "../../components/Modal"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { assignAsset, fetchAssets } from "../../api/assets"
import { extractErrorMessage } from "../../api/errors"
import type { Asset, AssetAssignment } from "../../types"

interface AssignAssetModalProps {
  poolId: string
  onClose: () => void
  onAssigned: (assignment: AssetAssignment) => void
}

export function AssignAssetModal({ poolId, onClose, onAssigned }: AssignAssetModalProps) {
  const [availableAssets, setAvailableAssets] = useState<Asset[]>([])
  const [isLoadingAssets, setIsLoadingAssets] = useState(true)
  const [selectedAssetId, setSelectedAssetId] = useState("")
  const [assignedDate, setAssignedDate] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    fetchAssets()
      .then((assets) => {
        const available = assets.filter((asset) => asset.status === "available")
        setAvailableAssets(available)
        if (available.length > 0) {
          setSelectedAssetId(available[0].id)
        }
      })
      .catch(() => setError("Failed to load assets"))
      .finally(() => setIsLoadingAssets(false))
  }, [])

  const noAssetsAvailable = !isLoadingAssets && availableAssets.length === 0

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")
    setIsSubmitting(true)
    try {
      const assignment = await assignAsset({
        asset: selectedAssetId,
        pool: poolId,
        assigned_date: assignedDate,
      })
      onAssigned(assignment)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to assign asset."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="Assign Asset" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Asset
          </label>
          {isLoadingAssets ? (
            <div className="flex items-center gap-2 text-sm text-ink-secondary">
              <Spinner className="h-4 w-4" />
              Loading...
            </div>
          ) : noAssetsAvailable ? (
            <p className="text-sm text-gold-400">No available assets to assign.</p>
          ) : (
            <select
              value={selectedAssetId}
              onChange={(e) => setSelectedAssetId(e.target.value)}
              className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
            >
              {availableAssets.map((asset) => (
                <option key={asset.id} value={asset.id}>
                  {asset.reference_code} ({asset.asset_type})
                </option>
              ))}
            </select>
          )}
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Assigned Date
          </label>
          <input
            type="date"
            value={assignedDate}
            onChange={(e) => setAssignedDate(e.target.value)}
            required
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting || noAssetsAvailable}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Assign"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
