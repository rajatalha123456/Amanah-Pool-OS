import { useEffect, useState, type FormEvent } from "react"
import { useNavigate, Link } from "react-router-dom"
import { Card } from "../components/Card"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { createPool, fetchApprovedProducts } from "../api/pools"
import { extractErrorMessage } from "../api/errors"
import type { Product } from "../types"

export function NewPoolWizard() {
  const navigate = useNavigate()
  const [products, setProducts] = useState<Product[]>([])
  const [isLoadingProducts, setIsLoadingProducts] = useState(true)
  const [productsError, setProductsError] = useState("")

  const [selectedProductId, setSelectedProductId] = useState("")
  const [poolName, setPoolName] = useState("")
  const [poolCode, setPoolCode] = useState("")
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().split("T")[0])
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
      .catch((err) => {
        setProductsError(extractErrorMessage(err, "Failed to load approved products from backend."))
      })
      .finally(() => setIsLoadingProducts(false))
  }, [])

  const selectedProduct = products.find((p) => p.id === selectedProductId)

  async function handleCreatePool(event: FormEvent) {
    event.preventDefault()
    if (!selectedProductId) {
      setSubmitError("Please select an approved product.")
      return
    }
    if (!poolName.trim()) {
      setSubmitError("Pool name is required.")
      return
    }
    if (!poolCode.trim()) {
      setSubmitError("Pool code is required.")
      return
    }

    setSubmitError("")
    setIsSubmitting(true)

    try {
      const pool = await createPool({
        name: poolName.trim(),
        code: poolCode.trim(),
        product: selectedProductId,
        effective_date: effectiveDate,
      })
      navigate(`/pools/${pool.id}`, {
        state: { successMessage: `Pool "${pool.name}" (${pool.code}) created successfully!` },
      })
    } catch (err) {
      setSubmitError(extractErrorMessage(err, "Failed to create pool."))
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-3xl">
      <PageHeader
        screenNumber="03"
        title="New Pool Setup"
        subtitle="Create and activate a new Shariah-governed pool instance linked to an approved product"
      />

      {isLoadingProducts ? (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading approved products from backend...</span>
        </div>
      ) : productsError ? (
        <Card>
          <p className="text-sm text-red-400">{productsError}</p>
        </Card>
      ) : products.length === 0 ? (
        <Card>
          <div className="space-y-3 p-2">
            <p className="text-sm text-gold-400 font-medium">
              No approved products available in the database.
            </p>
            <p className="text-xs text-ink-secondary">
              Under Shariah governance rules, a pool can only be created from an approved product.
              Please create and approve a product in the Product Catalogue first.
            </p>
            <Link to="/products-pools">
              <Button variant="primary" className="text-xs mt-2">
                Go to Product Catalogue
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <form onSubmit={handleCreatePool} className="space-y-6">
          <Card title="1. Select Approved Islamic Product">
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-ink-secondary uppercase mb-1">
                  Product
                </label>
                <select
                  value={selectedProductId}
                  onChange={(e) => setSelectedProductId(e.target.value)}
                  className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                >
                  {products.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.name} ({p.code}) — {p.operating_model}
                    </option>
                  ))}
                </select>
              </div>

              {selectedProduct && (
                <div className="rounded-lg border border-white/5 bg-navy-950/60 p-4 text-xs space-y-2">
                  <div className="flex justify-between">
                    <span className="text-ink-muted">Operating Model:</span>
                    <span className="font-semibold text-ink-primary">{selectedProduct.operating_model}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-muted">Contract Template:</span>
                    <span className="font-semibold text-emerald-400">
                      {selectedProduct.contract_template_detail?.name ?? "—"} (v{selectedProduct.contract_template_detail?.version ?? "1.0"})
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-ink-muted">Shariah Status:</span>
                    <span className="font-semibold text-emerald-400 uppercase">{selectedProduct.status}</span>
                  </div>
                </div>
              )}
            </div>
          </Card>

          <Card title="2. Pool Parameters">
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-ink-secondary uppercase mb-1">
                  Pool Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Retail Mudarabah Daily Depositor Pool"
                  value={poolName}
                  onChange={(e) => setPoolName(e.target.value)}
                  className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                />
              </div>

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="block text-xs font-semibold text-ink-secondary uppercase mb-1">
                    Pool Code *
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. POOL-MUD-2026"
                    value={poolCode}
                    onChange={(e) => setPoolCode(e.target.value)}
                    className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="block text-xs font-semibold text-ink-secondary uppercase mb-1">
                    Effective Date *
                  </label>
                  <input
                    type="date"
                    required
                    value={effectiveDate}
                    onChange={(e) => setEffectiveDate(e.target.value)}
                    className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>
            </div>
          </Card>

          {submitError && (
            <div className="rounded-md border border-red-500/30 bg-red-950/20 p-3 text-xs text-red-400">
              {submitError}
            </div>
          )}

          <div className="flex items-center justify-end gap-3">
            <Button variant="secondary" type="button" onClick={() => navigate("/pools")}>
              Cancel
            </Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>
              {isSubmitting ? <Spinner className="h-4 w-4" /> : "Create & Save Pool"}
            </Button>
          </div>
        </form>
      )}
    </div>
  )
}
