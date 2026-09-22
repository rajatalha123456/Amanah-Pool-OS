import { useEffect, useState } from "react"
import { Link, useLocation } from "react-router-dom"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { approveProduct, fetchProducts, submitProductForReview } from "../api/products"
import { extractErrorMessage } from "../api/errors"
import { NewProductModal } from "./NewProductModal"
import type { BadgeVariant, Product } from "../types"

type PageState = "loading" | "loaded" | "error"

const PRODUCT_STATUS_BADGE: Record<string, BadgeVariant> = {
  draft: "neutral",
  shariah_review: "gold",
  approved: "emerald",
  active: "emerald",
  retired: "navy",
}

function productStatusBadgeVariant(status: string): BadgeVariant {
  return PRODUCT_STATUS_BADGE[status] ?? "neutral"
}

export function ProductCatalogue() {
  const { user } = useAuth()
  const canApprove = user?.role === "shariah_board"
  const location = useLocation()
  const successMessage = (location.state as { successMessage?: string } | null)?.successMessage

  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [products, setProducts] = useState<Product[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [submittingId, setSubmittingId] = useState<string | null>(null)
  const [approvingId, setApprovingId] = useState<string | null>(null)
  const [rowError, setRowError] = useState("")

  function loadProducts() {
    setPageState("loading")
    fetchProducts()
      .then((data) => {
        setProducts(data)
        setPageState("loaded")
      })
      .catch(() => {
        setPageError("Failed to load data")
        setPageState("error")
      })
  }

  useEffect(() => {
    loadProducts()
  }, [])

  function handleCreated(product: Product) {
    setProducts((prev) => [product, ...prev])
    setIsModalOpen(false)
  }

  async function handleSubmitForReview(id: string) {
    setRowError("")
    setSubmittingId(id)
    try {
      const updated = await submitProductForReview(id)
      setProducts((prev) => prev.map((p) => (p.id === id ? updated : p)))
    } catch (err) {
      setRowError(extractErrorMessage(err, "Unable to submit product for review."))
    } finally {
      setSubmittingId(null)
    }
  }

  async function handleApprove(id: string) {
    setRowError("")
    setApprovingId(id)
    try {
      const updated = await approveProduct(id)
      setProducts((prev) => prev.map((p) => (p.id === id ? updated : p)))
    } catch (err) {
      setRowError(extractErrorMessage(err, "Unable to approve this product."))
    } finally {
      setApprovingId(null)
    }
  }

  const columns: TableColumn<Product>[] = [
    { header: "Name", accessor: (product) => product.name },
    { header: "Code", accessor: (product) => product.code },
    { header: "Operating Model", accessor: (product) => product.operating_model },
    {
      header: "Contract Template",
      accessor: (product) => product.contract_template_detail?.name ?? "—",
    },
    {
      header: "Status",
      accessor: (product) => (
        <Badge variant={productStatusBadgeVariant(product.status)}>{product.status}</Badge>
      ),
    },
    { header: "Updated At", accessor: (product) => product.updated_at },
    {
      header: "Action",
      accessor: (product) =>
        product.status === "draft" ? (
          <button
            type="button"
            onClick={() => handleSubmitForReview(product.id)}
            disabled={submittingId === product.id}
            className="text-sm font-medium text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
          >
            {submittingId === product.id ? "Submitting..." : "Submit for Review"}
          </button>
        ) : canApprove && product.status === "shariah_review" ? (
          <Button
            variant="primary"
            disabled={approvingId === product.id}
            onClick={() => handleApprove(product.id)}
          >
            {approvingId === product.id ? <Spinner className="h-4 w-4" /> : "Approve"}
          </Button>
        ) : null,
    },
  ]

  return (
    <div>
      <PageHeader
        title="Product Catalogue"
        subtitle="Approved, draft and retired Islamic products"
        actions={
          <div className="flex shrink-0 items-center gap-2">
            <Button variant="primary" onClick={() => setIsModalOpen(true)}>
              + New Product
            </Button>
          </div>
        }
      />

      <div className="mb-4 flex gap-4 border-b border-white/8 text-sm">
        <span className="border-b-2 border-emerald-500 px-1 pb-2 font-medium text-ink-primary">
          Products
        </span>
        <Link to="/pools" className="px-1 pb-2 text-ink-secondary hover:text-ink-primary">
          Pools
        </Link>
        <Link to="/contract-templates" className="px-1 pb-2 text-ink-secondary hover:text-ink-primary">
          Contract Templates
        </Link>
      </div>

      {successMessage && (
        <p className="mb-4 text-sm text-emerald-400">{successMessage}</p>
      )}

      {rowError && (
        <p className="mb-4 text-sm text-red-400">{rowError}</p>
      )}

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading products...</span>
        </div>
      )}

      {pageState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{pageError}</p>
        </Card>
      )}

      {pageState === "loaded" && (
        <Card>
          {products.length === 0 ? (
            <p className="text-sm text-ink-secondary">
              No products yet. Create your first product to get started.
            </p>
          ) : (
            <Table columns={columns} data={products} keyField={(product) => product.id} />
          )}
        </Card>
      )}

      {isModalOpen && (
        <NewProductModal onClose={() => setIsModalOpen(false)} onCreated={handleCreated} />
      )}
    </div>
  )
}
