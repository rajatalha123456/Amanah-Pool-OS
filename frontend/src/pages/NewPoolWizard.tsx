import { useEffect, useState, type ReactNode } from "react"
import { useNavigate, Link } from "react-router-dom"
import { Card } from "../components/Card"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { createPool, fetchApprovedProducts } from "../api/pools"
import { fetchLegalEntities } from "../api/tenants"
import { extractErrorMessage } from "../api/errors"
import type { LegalEntityRecord, Product } from "../types"

const STEPS = ["Model", "Contract", "Economics", "Assets", "Identity", "Review"] as const
const INPUT =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const CALENDARS = [
  { value: "daily", label: "Every day" },
  { value: "mon_fri", label: "Monday to Friday" },
  { value: "sun_thu", label: "Sunday to Thursday" },
]
const MODEL_LABEL: Record<string, string> = {
  bank_pool: "Islamic bank pool",
  investment_pool: "Investment pool",
  community_circle: "Community savings circle",
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="flex justify-between gap-4 border-b border-white/5 py-2 text-xs last:border-0">
      <span className="text-ink-muted">{label}</span>
      <span className="text-right font-semibold text-ink-primary">{children}</span>
    </div>
  )
}

/** Six steps as in the catalogue: model, contract, economics, assets, identity and a final review. */
export function NewPoolWizard() {
  const navigate = useNavigate()
  const [products, setProducts] = useState<Product[]>([])
  const [entities, setEntities] = useState<LegalEntityRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState("")

  const [step, setStep] = useState(0)
  const [productId, setProductId] = useState("")
  const [poolName, setPoolName] = useState("")
  const [poolCode, setPoolCode] = useState("")
  const [effectiveDate, setEffectiveDate] = useState(new Date().toISOString().split("T")[0])
  const [entityId, setEntityId] = useState("")
  const [branch, setBranch] = useState("")
  const [timezone, setTimezone] = useState("")
  const [calendar, setCalendar] = useState("daily")
  const [submitError, setSubmitError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    Promise.all([fetchApprovedProducts(), fetchLegalEntities().catch(() => [] as LegalEntityRecord[])])
      .then(([p, e]) => {
        setProducts(p)
        setEntities(e)
        if (p.length > 0) setProductId(p[0].id)
      })
      .catch((err) => setLoadError(extractErrorMessage(err, "Failed to load approved products.")))
      .finally(() => setIsLoading(false))
  }, [])

  const product = products.find((p) => p.id === productId)
  const entity = entities.find((e) => e.id === entityId)

  function stepProblem(index: number): string {
    if (index === 0 && !product) return "Choose an approved product."
    if (index === 4) {
      if (!poolName.trim()) return "Pool name is required."
      if (!poolCode.trim()) return "Pool code is required."
      if (!effectiveDate) return "An effective date is required."
    }
    return ""
  }

  function next() {
    const problem = stepProblem(step)
    if (problem) {
      setSubmitError(problem)
      return
    }
    setSubmitError("")
    setStep((s) => Math.min(STEPS.length - 1, s + 1))
  }

  async function create() {
    for (let i = 0; i < STEPS.length - 1; i++) {
      const problem = stepProblem(i)
      if (problem) {
        setSubmitError(problem)
        setStep(i)
        return
      }
    }
    setSubmitError("")
    setIsSubmitting(true)
    try {
      const pool = await createPool({
        name: poolName.trim(),
        code: poolCode.trim(),
        product: productId,
        effective_date: effectiveDate,
        legal_entity: entityId || null,
        branch: branch.trim(),
        timezone: timezone.trim(),
        calendar,
      })
      navigate(`/pools/${pool.id}`, { state: { successMessage: `Pool "${pool.name}" (${pool.code}) created successfully!` } })
    } catch (err) {
      setSubmitError(extractErrorMessage(err, "Failed to create pool."))
      setIsSubmitting(false)
    }
  }

  const eligible = product?.eligible_asset_types ?? []

  return (
    <div className="max-w-3xl">
      <PageHeader
        title="New Pool Setup"
        subtitle="Create a Shariah-governed pool from an approved product, in six steps"
      />

      {isLoading ? (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading approved products...</span>
        </div>
      ) : loadError ? (
        <Card>
          <p className="text-sm text-red-400">{loadError}</p>
        </Card>
      ) : products.length === 0 ? (
        <Card>
          <div className="space-y-3 p-2">
            <p className="text-sm font-medium text-gold-400">No approved products are available.</p>
            <p className="text-xs text-ink-secondary">
              A pool can only be created from an approved product. Create and approve one in the Product Catalogue first.
            </p>
            <Link to="/products-pools">
              <Button variant="primary" className="mt-2 text-xs">
                Go to Product Catalogue
              </Button>
            </Link>
          </div>
        </Card>
      ) : (
        <div className="space-y-6" data-testid="pool-wizard">
          <ol className="flex flex-wrap gap-2 text-xs" aria-label="Steps">
            {STEPS.map((label, i) => (
              <li
                key={label}
                aria-current={i === step ? "step" : undefined}
                className={`rounded-full border px-3 py-1 ${
                  i === step
                    ? "border-emerald-500 bg-emerald-500/10 text-emerald-300"
                    : i < step
                      ? "border-white/10 text-ink-secondary"
                      : "border-white/5 text-ink-muted"
                }`}
              >
                {i + 1}. {label}
              </li>
            ))}
          </ol>

          {step === 0 && (
            <Card title="1. Operating model and product">
              <label className="mb-1 block text-xs font-semibold uppercase text-ink-secondary">Approved product</label>
              <select value={productId} onChange={(e) => setProductId(e.target.value)} className={INPUT}>
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.code}) - {MODEL_LABEL[p.operating_model] ?? p.operating_model}
                  </option>
                ))}
              </select>
              {product && (
                <div className="mt-4 rounded-lg border border-white/5 bg-navy-950/60 p-4">
                  <Row label="Operating model">{MODEL_LABEL[product.operating_model] ?? product.operating_model}</Row>
                  <Row label="Base currency">{product.base_currency}</Row>
                </div>
              )}
            </Card>
          )}

          {step === 1 && product && (
            <Card title="2. Contract">
              <Row label="Contract template">
                {product.contract_template_detail?.name ?? "-"} (v{product.contract_template_detail?.version ?? "-"})
              </Row>
              <Row label="Contract type">{product.contract_template_detail?.contract_type?.replace(/_/g, " ") ?? "-"}</Row>
              <Row label="Template status">{product.contract_template_detail?.status ?? "-"}</Row>
              <p className="mt-3 text-xs text-ink-secondary">
                The Shariah decision behind this contract is checked when the pool is activated; a pool cannot open without an
                approved, in-force decision.
              </p>
            </Card>
          )}

          {step === 2 && product && (
            <Card title="3. Economics and participation terms">
              <Row label="Profit-sharing ratio and weightages">Approved after creation, before activation</Row>
              <Row label="Redemption notice">{product.redemption_notice_days ? `${product.redemption_notice_days} days` : "none"}</Row>
              <Row label="Redemption gate">{product.redemption_gate_pct ? `${product.redemption_gate_pct}% per 30 days` : "none"}</Row>
              <Row label="Minimum subscription">{product.minimum_subscription ? `PKR ${product.minimum_subscription}` : "no minimum"}</Row>
              <Row label="Cap per account">{product.subscription_cap ? `PKR ${product.subscription_cap}` : "no cap"}</Row>
              <Row label="Minimum holding">{product.minimum_tenure_days ? `${product.minimum_tenure_days} days` : "none"}</Row>
              <Row label="KYC tier required">{product.required_kyc_tier ?? "basic"}</Row>
              <Row label="Participants allowed">{product.max_participants ?? "no limit"}</Row>
              <p className="mt-3 text-xs text-ink-secondary">
                These come from the product and are sealed into the pool's configuration version when it is activated.
              </p>
            </Card>
          )}

          {step === 3 && product && (
            <Card title="4. Assets">
              <Row label="Eligible asset types">
                {eligible.length === 0 ? "any type" : eligible.map((t) => t.replace(/_/g, " ")).join(", ")}
              </Row>
              <p className="mt-3 text-xs text-ink-secondary">
                Assets are assigned to the pool after it is created. An asset of a type that is not eligible is refused, and one asset
                can belong to only one pool at a time.
              </p>
            </Card>
          )}

          {step === 4 && (
            <Card title="5. Identity and governance">
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase text-ink-secondary">Pool name *</label>
                  <input className={INPUT} value={poolName} onChange={(e) => setPoolName(e.target.value)} />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase text-ink-secondary">Pool code *</label>
                  <input className={INPUT} value={poolCode} onChange={(e) => setPoolCode(e.target.value)} />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase text-ink-secondary">Legal entity</label>
                  <select
                    className={INPUT}
                    value={entityId}
                    onChange={(e) => {
                      setEntityId(e.target.value)
                      const chosen = entities.find((x) => x.id === e.target.value)
                      if (chosen && !timezone) setTimezone(chosen.timezone)
                    }}
                  >
                    <option value="">Not set</option>
                    {entities.map((e) => (
                      <option key={e.id} value={e.id}>
                        {e.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase text-ink-secondary">Branch</label>
                  <input className={INPUT} value={branch} onChange={(e) => setBranch(e.target.value)} />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase text-ink-secondary">Timezone</label>
                  <input className={INPUT} value={timezone} onChange={(e) => setTimezone(e.target.value)} placeholder="e.g. Asia/Karachi" />
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase text-ink-secondary">Working calendar</label>
                  <select className={INPUT} value={calendar} onChange={(e) => setCalendar(e.target.value)}>
                    {CALENDARS.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-xs font-semibold uppercase text-ink-secondary">Effective date *</label>
                  <input type="date" className={INPUT} value={effectiveDate} onChange={(e) => setEffectiveDate(e.target.value)} />
                </div>
              </div>
            </Card>
          )}

          {step === 5 && product && (
            <Card title="6. Review">
              <Row label="Pool">
                {poolName} ({poolCode})
              </Row>
              <Row label="Product">
                {product.name} ({MODEL_LABEL[product.operating_model] ?? product.operating_model})
              </Row>
              <Row label="Contract">{product.contract_template_detail?.name ?? "-"}</Row>
              <Row label="Legal entity">{entity?.name ?? "not set"}</Row>
              <Row label="Branch">{branch || "not set"}</Row>
              <Row label="Timezone">{timezone || entity?.timezone || "not set"}</Row>
              <Row label="Calendar">{CALENDARS.find((c) => c.value === calendar)?.label}</Row>
              <Row label="Effective date">{effectiveDate}</Row>
              <p className="mt-3 text-xs text-ink-secondary">
                The pool is created as a draft. It still needs the Shariah Board's approval and an independent checker's activation, and
                every activation gate must pass.
              </p>
            </Card>
          )}

          {submitError && <p className="text-sm text-red-400">{submitError}</p>}

          <div className="flex items-center justify-between">
            <Button variant="secondary" disabled={step === 0 || isSubmitting} onClick={() => setStep((s) => Math.max(0, s - 1))}>
              Back
            </Button>
            {step < STEPS.length - 1 ? (
              <Button variant="primary" onClick={next}>
                Next: {STEPS[step + 1]}
              </Button>
            ) : (
              <Button variant="primary" disabled={isSubmitting} onClick={() => void create()}>
                {isSubmitting ? <Spinner className="h-4 w-4" /> : "Create pool"}
              </Button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
