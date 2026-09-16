import { useEffect, useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { Card } from "../components/Card"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { createPool, fetchApprovedProducts } from "../api/pools"
import { extractErrorMessage } from "../api/errors"
import type { Product } from "../types"

const STEPS = ["Model", "Contract", "Economics", "Assets", "Governance", "Review"]

const INFORMATIONAL_STEP_COPY: Record<string, string> = {
  Contract:
    "This will be configurable after the pool is created (Weightage & PSR Setup, Asset Assignment screens).",
  Economics:
    "This will be configurable after the pool is created (Weightage & PSR Setup, Asset Assignment screens).",
  Assets:
    "This will be configurable after the pool is created (Weightage & PSR Setup, Asset Assignment screens).",
  Governance:
    "This will be configurable after the pool is created (Weightage & PSR Setup, Asset Assignment screens).",
}

function Stepper({ currentStep }: { currentStep: number }) {
  return (
    <div className="mb-6 flex flex-wrap gap-2">
      {STEPS.map((label, index) => {
        const stepNumber = index + 1
        const isCurrent = stepNumber === currentStep
        return (
          <span
            key={label}
            className={`inline-flex items-center rounded-full px-3 py-1.5 text-sm font-medium ${
              isCurrent
                ? "bg-emerald-600 text-white"
                : "bg-white/5 text-ink-secondary"
            }`}
          >
            {stepNumber} {label}
          </span>
        )
      })}
    </div>
  )
}

export function NewPoolWizard() {
  const navigate = useNavigate()
  const [step, setStep] = useState(1)

  const [products, setProducts] = useState<Product[]>([])
  const [isLoadingProducts, setIsLoadingProducts] = useState(true)
  const [productsError, setProductsError] = useState("")
  const [selectedProductId, setSelectedProductId] = useState("")

  const [poolName, setPoolName] = useState("")
  const [poolCode, setPoolCode] = useState("")
  const [effectiveDate, setEffectiveDate] = useState("")
  const [submitError, setSubmitError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    fetchApprovedProducts()
      .then((data) => {
        setProducts(data)
        if (data.length > 0) {
          setSelectedProductId(data[0].id)
        }
      })
      .catch(() => {
        setProductsError("Failed to load products")
      })
      .finally(() => setIsLoadingProducts(false))
  }, [])

  const selectedProduct = products.find((product) => product.id === selectedProductId)
  const noApprovedProducts = !isLoadingProducts && !productsError && products.length === 0

  function goNext() {
    setStep((current) => Math.min(current + 1, STEPS.length))
  }

  function goBack() {
    setStep((current) => Math.max(current - 1, 1))
  }

  async function handleCreatePool(event: FormEvent) {
    event.preventDefault()
    setSubmitError("")
    setIsSubmitting(true)

    try {
      const pool = await createPool({
        name: poolName,
        code: poolCode,
        product: selectedProductId,
        effective_date: effectiveDate,
      })
      navigate("/pools", {
        state: { successMessage: `Pool "${pool.name}" created successfully.` },
      })
    } catch (err) {
      setSubmitError(extractErrorMessage(err, "Unable to create pool."))
    } finally {
      setIsSubmitting(false)
    }
  }

  const currentStepLabel = STEPS[step - 1]

  return (
    <div>
      <PageHeader title="New Pool Wizard" subtitle="Contract-aware setup with Shariah gates" />

      <Stepper currentStep={step} />

      <Card>
        {step === 1 && (
          <div>
            <h3 className="mb-4 text-sm font-semibold text-ink-primary">Select an approved product</h3>

            {isLoadingProducts && (
              <div className="flex items-center gap-2 text-sm text-ink-secondary">
                <Spinner className="h-4 w-4" />
                Loading products...
              </div>
            )}

            {productsError && <p className="text-sm text-red-400">{productsError}</p>}

            {noApprovedProducts && (
              <p className="text-sm text-gold-400">
                No approved products available. Create and approve a product first.
              </p>
            )}

            {!isLoadingProducts && !productsError && products.length > 0 && (
              <select
                value={selectedProductId}
                onChange={(e) => setSelectedProductId(e.target.value)}
                className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
              >
                {products.map((product) => (
                  <option key={product.id} value={product.id}>
                    {product.name} ({product.code})
                  </option>
                ))}
              </select>
            )}

            <div className="mt-6 flex justify-end">
              <Button
                type="button"
                variant="primary"
                onClick={goNext}
                disabled={noApprovedProducts || isLoadingProducts || !selectedProductId}
              >
                Next
              </Button>
            </div>
          </div>
        )}

        {step >= 2 && step <= 5 && (
          <div>
            <h3 className="mb-2 text-sm font-semibold text-ink-primary">{currentStepLabel}</h3>
            <p className="text-sm text-ink-secondary">
              {INFORMATIONAL_STEP_COPY[currentStepLabel]}
            </p>
            <div className="mt-6 flex justify-between">
              <Button type="button" variant="secondary" onClick={goBack}>
                Back
              </Button>
              <Button type="button" variant="primary" onClick={goNext}>
                Next
              </Button>
            </div>
          </div>
        )}

        {step === 6 && (
          <form onSubmit={handleCreatePool}>
            <h3 className="mb-4 text-sm font-semibold text-ink-primary">Review</h3>

            {selectedProduct && (
              <div className="mb-4 rounded-md border border-white/8 bg-navy-800 p-3 text-sm text-ink-secondary">
                <p className="text-ink-primary">{selectedProduct.name}</p>
                <p>Code: {selectedProduct.code}</p>
                <p>Contract Template: {selectedProduct.contract_template_detail?.name}</p>
              </div>
            )}

            <div className="space-y-4">
              <div>
                <label
                  htmlFor="pool-name"
                  className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
                >
                  Pool Name
                </label>
                <input
                  id="pool-name"
                  type="text"
                  value={poolName}
                  onChange={(e) => setPoolName(e.target.value)}
                  required
                  className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="pool-code"
                  className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
                >
                  Pool Code
                </label>
                <input
                  id="pool-code"
                  type="text"
                  value={poolCode}
                  onChange={(e) => setPoolCode(e.target.value)}
                  required
                  className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div>
                <label
                  htmlFor="effective-date"
                  className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"
                >
                  Effective Date
                </label>
                <input
                  id="effective-date"
                  type="date"
                  value={effectiveDate}
                  onChange={(e) => setEffectiveDate(e.target.value)}
                  required
                  className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                />
              </div>
            </div>

            {submitError && <p className="mt-4 text-sm text-red-400">{submitError}</p>}

            <div className="mt-6 flex justify-between">
              <Button type="button" variant="secondary" onClick={goBack}>
                Back
              </Button>
              <Button type="submit" variant="primary" disabled={isSubmitting}>
                {isSubmitting ? <Spinner className="h-4 w-4" /> : "Create Pool"}
              </Button>
            </div>
          </form>
        )}
      </Card>
    </div>
  )
}
