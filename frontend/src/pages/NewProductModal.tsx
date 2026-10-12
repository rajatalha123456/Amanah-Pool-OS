import { useEffect, useState, type FormEvent } from "react"
import { Modal } from "../components/Modal"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { createProduct, fetchContractTemplates } from "../api/products"
import { extractErrorMessage } from "../api/errors"
import type { ContractTemplate, Product } from "../types"

interface NewProductModalProps {
  onClose: () => void
  onCreated: (product: Product) => void
}

const OPERATING_MODELS = [
  { value: "bank_pool", label: "Bank Pool" },
  { value: "investment_pool", label: "Investment Pool" },
  { value: "community_circle", label: "Community Circle" },
]

const ASSET_TYPES = [
  { value: "murabahah", label: "Murabahah" },
  { value: "ijarah", label: "Ijarah" },
  { value: "diminishing_musharakah", label: "Diminishing Musharakah" },
  { value: "other", label: "Other" },
]
const FIELD =
  "mt-1 w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

export function NewProductModal({ onClose, onCreated }: NewProductModalProps) {
  const [name, setName] = useState("")
  const [code, setCode] = useState("")
  const [operatingModel, setOperatingModel] = useState(OPERATING_MODELS[0].value)
  const [contractTemplateId, setContractTemplateId] = useState("")
  const [eligibleAssets, setEligibleAssets] = useState<string[]>([])
  const [minimumSubscription, setMinimumSubscription] = useState("")
  const [subscriptionCap, setSubscriptionCap] = useState("")
  const [tenureDays, setTenureDays] = useState("")
  const [kycTier, setKycTier] = useState("basic")
  const [maxParticipants, setMaxParticipants] = useState("")

  const [contractTemplates, setContractTemplates] = useState<ContractTemplate[]>([])
  const [isLoadingTemplates, setIsLoadingTemplates] = useState(true)
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    fetchContractTemplates()
      .then((templates) => {
        setContractTemplates(templates)
        if (templates.length > 0) {
          setContractTemplateId(templates[0].id)
        }
      })
      .catch(() => {
        setError("Failed to load contract templates")
      })
      .finally(() => setIsLoadingTemplates(false))
  }, [])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")
    setIsSubmitting(true)

    try {
      const product = await createProduct({
        name,
        code,
        operating_model: operatingModel,
        contract_template: contractTemplateId,
        eligible_asset_types: eligibleAssets,
        minimum_subscription: minimumSubscription || null,
        subscription_cap: subscriptionCap || null,
        minimum_tenure_days: tenureDays ? Number(tenureDays) : 0,
        required_kyc_tier: kycTier,
        max_participants: maxParticipants ? Number(maxParticipants) : null,
      })
      onCreated(product)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to create product."))
    } finally {
      setIsSubmitting(false)
    }
  }

  const noTemplatesAvailable = !isLoadingTemplates && contractTemplates.length === 0

  return (
    <Modal title="New Product" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label
            htmlFor="product-name"
            className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
          >
            Name
          </label>
          <input
            id="product-name"
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          />
        </div>

        <div>
          <label
            htmlFor="product-code"
            className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
          >
            Code
          </label>
          <input
            id="product-code"
            type="text"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            required
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          />
        </div>

        <fieldset>
          <legend className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
            Eligible asset types
          </legend>
          <div className="flex flex-wrap gap-4" data-testid="eligible-assets">
            {ASSET_TYPES.map((t) => (
              <label key={t.value} className="flex items-center gap-2 text-sm text-ink-primary">
                <input
                  type="checkbox"
                  checked={eligibleAssets.includes(t.value)}
                  onChange={(e) =>
                    setEligibleAssets(e.target.checked ? [...eligibleAssets, t.value] : eligibleAssets.filter((v) => v !== t.value))
                  }
                />
                {t.label}
              </label>
            ))}
          </div>
          <p className="mt-1 text-[11px] text-ink-muted">
            Only assets of the ticked types can be assigned to a pool of this product. Tick none to allow any type.
          </p>
        </fieldset>

        <fieldset className="rounded-lg border border-white/8 p-3">
          <legend className="px-1 text-xs font-semibold tracking-wide text-ink-secondary uppercase">Participation terms (optional)</legend>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <label className="text-xs text-ink-secondary">
              Minimum subscription (PKR)
              <input type="number" min="0" step="0.01" value={minimumSubscription} onChange={(e) => setMinimumSubscription(e.target.value)} className={FIELD} />
            </label>
            <label className="text-xs text-ink-secondary">
              Cap per account (PKR)
              <input type="number" min="0" step="0.01" value={subscriptionCap} onChange={(e) => setSubscriptionCap(e.target.value)} className={FIELD} />
            </label>
            <label className="text-xs text-ink-secondary">
              Minimum holding (days)
              <input type="number" min="0" value={tenureDays} onChange={(e) => setTenureDays(e.target.value)} className={FIELD} />
            </label>
            <label className="text-xs text-ink-secondary">
              Participants allowed per pool
              <input type="number" min="1" value={maxParticipants} onChange={(e) => setMaxParticipants(e.target.value)} className={FIELD} />
            </label>
            <label className="text-xs text-ink-secondary sm:col-span-2">
              KYC tier required
              <select value={kycTier} onChange={(e) => setKycTier(e.target.value)} className={FIELD}>
                <option value="basic">Basic</option>
                <option value="standard">Standard</option>
                <option value="enhanced">Enhanced</option>
              </select>
            </label>
          </div>
        </fieldset>

        <div>
          <label
            htmlFor="operating-model"
            className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
          >
            Operating Model
          </label>
          <select
            id="operating-model"
            value={operatingModel}
            onChange={(e) => setOperatingModel(e.target.value)}
            className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          >
            {OPERATING_MODELS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label
            htmlFor="contract-template"
            className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
          >
            Contract Template
          </label>
          {isLoadingTemplates ? (
            <div className="flex items-center gap-2 text-sm text-ink-secondary">
              <Spinner className="h-4 w-4" />
              Loading...
            </div>
          ) : noTemplatesAvailable ? (
            <p className="text-sm text-gold-400">
              No contract templates available. Create one first.
            </p>
          ) : (
            <select
              id="contract-template"
              value={contractTemplateId}
              onChange={(e) => setContractTemplateId(e.target.value)}
              className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
            >
              {contractTemplates.map((template) => (
                <option key={template.id} value={template.id}>
                  {template.name} v{template.version}
                </option>
              ))}
            </select>
          )}
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="primary"
            disabled={isSubmitting || noTemplatesAvailable}
          >
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
