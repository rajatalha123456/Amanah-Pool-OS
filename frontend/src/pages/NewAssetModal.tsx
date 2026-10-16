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
  const [obligorName, setObligorName] = useState("")
  const [obligorGroup, setObligorGroup] = useState("")
  const [sector, setSector] = useState("")
  const [isRelatedParty, setIsRelatedParty] = useState(false)
  const [creditRating, setCreditRating] = useState("")
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
        obligor_name: obligorName,
        obligor_group: obligorGroup,
        sector,
        is_related_party: isRelatedParty,
        credit_rating: creditRating,
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

        <p className="text-xs text-ink-secondary">For the concentration limits. Left empty, obligor and sector are inferred from the description and marked "(inferred)".</p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Obligor
            <input type="text" value={obligorName} onChange={(e) => setObligorName(e.target.value)} className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none mt-1" />
          </label>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Obligor group
            <input type="text" value={obligorGroup} onChange={(e) => setObligorGroup(e.target.value)} className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none mt-1" />
          </label>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Sector
            <select value={sector} onChange={(e) => setSector(e.target.value)} className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none mt-1">
              <option value="">Not recorded</option>
              <option value="sovereign">Sovereign &amp; public sector</option>
              <option value="real_estate">Real estate</option>
              <option value="power_energy">Power &amp; energy</option>
              <option value="textiles">Textiles</option>
              <option value="general">General commercial</option>
            </select>
          </label>
          <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Credit rating
            <input type="text" value={creditRating} onChange={(e) => setCreditRating(e.target.value)} className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none mt-1" />
          </label>
        </div>
        <label className="flex items-center gap-2 text-xs text-ink-secondary">
          <input type="checkbox" checked={isRelatedParty} onChange={(e) => setIsRelatedParty(e.target.checked)} />
          The obligor is a related party of the bank
        </label>

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
