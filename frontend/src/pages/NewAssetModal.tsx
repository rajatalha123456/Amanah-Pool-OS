import { useState, type FormEvent } from "react"
import { Modal } from "../components/Modal"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { createAsset } from "../api/assets"
import { extractErrorMessage } from "../api/errors"
import type { Asset } from "../types"

interface NewAssetModalProps {
  onClose: () => void
  onCreated: (asset: Asset) => void
}

const ASSET_TYPES = [
  { value: "murabahah", label: "Murabahah" },
  { value: "ijarah", label: "Ijarah" },
  { value: "diminishing_musharakah", label: "Diminishing Musharakah" },
  { value: "other", label: "Other" },
]

export function NewAssetModal({ onClose, onCreated }: NewAssetModalProps) {
  const [referenceCode, setReferenceCode] = useState("")
  const [assetType, setAssetType] = useState(ASSET_TYPES[0].value)
  const [description, setDescription] = useState("")
  const [faceValue, setFaceValue] = useState("")
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")
    setIsSubmitting(true)
    try {
      const asset = await createAsset({
        reference_code: referenceCode,
        asset_type: assetType,
        description,
        face_value: faceValue,
      })
      onCreated(asset)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to create asset."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="New Asset" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Reference Code
          </label>
          <input
            type="text"
            value={referenceCode}
            onChange={(e) => setReferenceCode(e.target.value)}
            required
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Asset Type
          </label>
          <select
            value={assetType}
            onChange={(e) => setAssetType(e.target.value)}
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          >
            {ASSET_TYPES.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Description
          </label>
          <input
            type="text"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            required
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Face Value
          </label>
          <input
            type="number"
            step="0.01"
            value={faceValue}
            onChange={(e) => setFaceValue(e.target.value)}
            required
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
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
