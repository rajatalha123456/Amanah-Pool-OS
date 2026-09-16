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

export function NewProductModal({ onClose, onCreated }: NewProductModalProps) {
  const [name, setName] = useState("")
  const [code, setCode] = useState("")
  const [operatingModel, setOperatingModel] = useState(OPERATING_MODELS[0].value)
  const [contractTemplateId, setContractTemplateId] = useState("")

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
