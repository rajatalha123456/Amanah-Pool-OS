import { useEffect, useState, type FormEvent } from "react"
import { Link } from "react-router-dom"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import {
  approveContractTemplate,
  createContractTemplate,
  fetchClausesSchema,
  fetchContractTemplates,
} from "../api/products"
import { fetchShariahDecisions } from "../api/shariahGovernance"
import { extractErrorMessage } from "../api/errors"
import type {
  BadgeVariant,
  ContractClauseSchemaField,
  ContractTemplate,
  ShariahDecision,
} from "../types"

type PageState = "loading" | "loaded" | "error"

const CONTRACT_TYPES = [
  { value: "mudarabah_unrestricted", label: "Mudarabah (Unrestricted)" },
  { value: "mudarabah_restricted", label: "Mudarabah (Restricted)" },
  { value: "musharakah", label: "Musharakah" },
  { value: "wakalah", label: "Wakalah" },
  { value: "qard", label: "Qard" },
]

const TEMPLATE_STATUS_BADGE: Record<string, BadgeVariant> = {
  draft: "neutral",
  approved: "emerald",
  retired: "navy",
}

function templateStatusBadgeVariant(status: string): BadgeVariant {
  return TEMPLATE_STATUS_BADGE[status] ?? "neutral"
}

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

export function ContractTemplateStudio() {
  const { user } = useAuth()
  const canApprove = user?.role === "shariah_board"
  const [templates, setTemplates] = useState<ContractTemplate[]>([])
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [approvingId, setApprovingId] = useState<string | null>(null)

  function loadTemplates() {
    setPageState("loading")
    fetchContractTemplates()
      .then((data) => {
        setTemplates(data)
        setPageState("loaded")
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load contract templates."))
        setPageState("error")
      })
  }

  useEffect(() => {
    loadTemplates()
  }, [])

  function handleCreated(template: ContractTemplate) {
    setTemplates((prev) => [template, ...prev])
    setIsFormOpen(false)
  }

  async function handleApprove(template: ContractTemplate) {
    setPageError("")
    setApprovingId(template.id)
    try {
      const updated = await approveContractTemplate(template.id)
      setTemplates((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setPageError(extractErrorMessage(err, "Unable to approve this contract template."))
    } finally {
      setApprovingId(null)
    }
  }

  const columns: TableColumn<ContractTemplate>[] = [
    { header: "Name", accessor: (template) => template.name },
    { header: "Contract Type", accessor: (template) => template.contract_type },
    { header: "Version", accessor: (template) => template.version },
    {
      header: "Status",
      accessor: (template) => (
        <Badge variant={templateStatusBadgeVariant(template.status)}>{template.status}</Badge>
      ),
    },
    { header: "Shariah Decision", accessor: (template) => template.shariah_decision_code ?? "—" },
    {
      header: "Action",
      accessor: (template) =>
        canApprove && template.status === "draft" ? (
          <Button
            variant="primary"
            disabled={approvingId === template.id}
            onClick={() => handleApprove(template)}
          >
            {approvingId === template.id ? <Spinner className="h-4 w-4" /> : "Approve"}
          </Button>
        ) : null,
    },
  ]

  return (
    <div>
      <PageHeader
        title="Product Catalogue"
        subtitle="Standard contract templates used by products"
        actions={
          !isFormOpen ? (
            <Button variant="primary" onClick={() => setIsFormOpen(true)}>
              + New Template
            </Button>
          ) : undefined
        }
      />

      <div className="mb-4 flex gap-4 border-b border-white/8 text-sm">
        <Link to="/products-pools" className="px-1 pb-2 text-ink-secondary hover:text-ink-primary">
          Products
        </Link>
        <Link to="/pools" className="px-1 pb-2 text-ink-secondary hover:text-ink-primary">
          Pools
        </Link>
        <span className="border-b-2 border-emerald-500 px-1 pb-2 font-medium text-ink-primary">
          Contract Templates
        </span>
      </div>

      {isFormOpen && (
        <NewContractTemplateForm
          existingTemplateId={templates[0]?.id}
          onClose={() => setIsFormOpen(false)}
          onCreated={handleCreated}
        />
      )}

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading contract templates...</span>
        </div>
      )}

      {pageState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{pageError}</p>
        </Card>
      )}

      {pageState === "loaded" && (
        <Card>
          {templates.length === 0 ? (
            <p className="text-sm text-ink-secondary">
              No contract templates yet. Create your first template to get started.
            </p>
          ) : (
            <Table columns={columns} data={templates} keyField={(template) => template.id} />
          )}
        </Card>
      )}
    </div>
  )
}

interface ClauseRow {
  key: string
  value: string
}

function NewContractTemplateForm({
  existingTemplateId,
  onClose,
  onCreated,
}: {
  existingTemplateId?: string
  onClose: () => void
  onCreated: (template: ContractTemplate) => void
}) {
  const [name, setName] = useState("")
  const [contractType, setContractType] = useState(CONTRACT_TYPES[0].value)
  const [version, setVersion] = useState("1.0")
  const [shariahDecisionId, setShariahDecisionId] = useState("")
  const [clauseRows, setClauseRows] = useState<ClauseRow[]>([{ key: "", value: "" }])

  const [approvedDecisions, setApprovedDecisions] = useState<ShariahDecision[]>([])
  const [clauseSchema, setClauseSchema] = useState<ContractClauseSchemaField[]>(CLAUSE_SCHEMA_FALLBACK)
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    fetchShariahDecisions()
      .then((decisions) => setApprovedDecisions(decisions.filter((d) => d.status === "approved")))
      .catch(() => setApprovedDecisions([]))
  }, [])

  useEffect(() => {
    // The clauses schema is currently the same static list for every
    // template (see the backend note), so any existing template id works
    // here - but a brand-new template has no id yet, so we fetch it from
    // the most recently created template if one exists, falling back to
    // the static list (kept in sync with the backend's) when the
    // catalogue is empty.
    if (!existingTemplateId) return
    fetchClausesSchema(existingTemplateId)
      .then((schema) => setClauseSchema(schema))
      .catch(() => setClauseSchema(CLAUSE_SCHEMA_FALLBACK))
  }, [existingTemplateId])

  function addClauseRow() {
    setClauseRows((prev) => [...prev, { key: "", value: "" }])
  }

  function removeClauseRow(index: number) {
    setClauseRows((prev) => prev.filter((_, i) => i !== index))
  }

  function updateClauseRow(index: number, field: "key" | "value", value: string) {
    setClauseRows((prev) => prev.map((row, i) => (i === index ? { ...row, [field]: value } : row)))
  }

  function addSuggestedClause(field: ContractClauseSchemaField) {
    if (clauseRows.some((row) => row.key === field.key)) return
    setClauseRows((prev) => {
      const hasEmptyRow = prev.length === 1 && prev[0].key === "" && prev[0].value === ""
      const base = hasEmptyRow ? [] : prev
      return [...base, { key: field.key, value: "" }]
    })
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError("")

    const clauses: Record<string, string> = {}
    for (const row of clauseRows) {
      if (!row.key.trim()) continue
      clauses[row.key.trim()] = row.value
    }
    if (Object.keys(clauses).length === 0) {
      setError("At least one clause is required.")
      return
    }

    setIsSubmitting(true)
    try {
      const template = await createContractTemplate({
        name,
        contract_type: contractType,
        version,
        clauses,
        shariah_decision: shariahDecisionId || null,
      })
      onCreated(template)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to create contract template."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Card title="New Contract Template" className="mb-6">
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <div>
            <label htmlFor="template-name" className={labelClasses}>
              Name
            </label>
            <input
              id="template-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              required
              className={inputClasses}
            />
          </div>

          <div>
            <label htmlFor="template-version" className={labelClasses}>
              Version
            </label>
            <input
              id="template-version"
              type="text"
              value={version}
              onChange={(e) => setVersion(e.target.value)}
              required
              className={inputClasses}
            />
          </div>

          <div>
            <label htmlFor="contract-type" className={labelClasses}>
              Contract Type
            </label>
            <select
              id="contract-type"
              value={contractType}
              onChange={(e) => setContractType(e.target.value)}
              className={inputClasses}
            >
              {CONTRACT_TYPES.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div>
          <label htmlFor="shariah-decision" className={labelClasses}>
            Shariah Decision (optional)
          </label>
          <select
            id="shariah-decision"
            value={shariahDecisionId}
            onChange={(e) => setShariahDecisionId(e.target.value)}
            className={inputClasses}
          >
            <option value="">None</option>
            {approvedDecisions.map((decision) => (
              <option key={decision.id} value={decision.id}>
                {decision.decision_code} — {decision.title}
              </option>
            ))}
          </select>
          {approvedDecisions.length === 0 && (
            <p className="mt-1 text-xs text-ink-secondary">No approved Shariah decisions available yet.</p>
          )}
        </div>

        <div>
          <p className={labelClasses}>Standard clause fields</p>
          <div className="flex flex-wrap gap-2">
            {clauseSchema.map((field) => (
              <button
                key={field.key}
                type="button"
                onClick={() => addSuggestedClause(field)}
                title={field.description}
                className="rounded-full border border-white/10 px-3 py-1 text-xs text-ink-secondary hover:border-emerald-500 hover:text-ink-primary"
              >
                + {field.label}
              </button>
            ))}
          </div>
        </div>

        <div>
          <p className={labelClasses}>Clauses</p>
          <div className="space-y-2">
            {clauseRows.map((row, index) => (
              <div key={index} className="flex gap-2">
                <input
                  type="text"
                  placeholder="Clause key (e.g. profit_ratio)"
                  value={row.key}
                  onChange={(e) => updateClauseRow(index, "key", e.target.value)}
                  className={inputClasses}
                />
                <input
                  type="text"
                  placeholder="Value"
                  value={row.value}
                  onChange={(e) => updateClauseRow(index, "value", e.target.value)}
                  className={inputClasses}
                />
                <Button type="button" variant="outline" onClick={() => removeClauseRow(index)}>
                  Remove
                </Button>
              </div>
            ))}
          </div>
          <Button type="button" variant="secondary" className="mt-2" onClick={addClauseRow}>
            + Add Clause
          </Button>
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Create Template"}
          </Button>
        </div>
      </form>
    </Card>
  )
}

const CLAUSE_SCHEMA_FALLBACK: ContractClauseSchemaField[] = [
  { key: "profit_ratio", label: "Profit Ratio", description: "The depositor/mudarib profit-sharing split." },
  { key: "late_payment_policy", label: "Late Payment Policy", description: "How overdue payments are treated (no interest/penalty under Shariah)." },
  { key: "notice_period", label: "Notice Period", description: "Required notice before withdrawal or termination." },
  { key: "loss_bearing_clause", label: "Loss Bearing Clause", description: "How capital losses are allocated among participants." },
  { key: "early_termination_terms", label: "Early Termination Terms", description: "Conditions and consequences of ending the contract early." },
  { key: "collateral_requirements", label: "Collateral Requirements", description: "Any security/collateral required, if applicable." },
  { key: "dispute_resolution", label: "Dispute Resolution", description: "Mechanism for resolving disagreements (e.g. Shariah arbitration)." },
  { key: "purification_clause", label: "Purification Clause", description: "How incidental non-Shariah-compliant income is handled." },
]
