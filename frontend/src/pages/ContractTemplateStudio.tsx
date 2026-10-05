import { useEffect, useState, type FormEvent } from "react"
import { Link } from "react-router-dom"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { Modal } from "../components/Modal"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import {
  analyzeContractWithAI,
  approveContractTemplate,
  createContractTemplate,
  fetchClausesSchema,
  fetchContractTemplates,
  type ContractAnalysisResult,
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
  const canCreate = user?.role === "product_manager" || user?.role === "platform_super_admin"
  const [templates, setTemplates] = useState<ContractTemplate[]>([])
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [isAnalyzerOpen, setIsAnalyzerOpen] = useState(false)
  const [selectedTemplate, setSelectedTemplate] = useState<ContractTemplate | null>(null)
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
      if (selectedTemplate?.id === updated.id) {
        setSelectedTemplate(updated)
      }
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
      accessor: (template) => (
        <div className="flex items-center gap-2">
          <Button variant="secondary" onClick={() => setSelectedTemplate(template)}>
            View Clauses
          </Button>
          {canApprove && template.status === "draft" && (
            <Button
              variant="primary"
              disabled={approvingId === template.id}
              onClick={() => handleApprove(template)}
            >
              {approvingId === template.id ? <Spinner className="h-4 w-4" /> : "Approve"}
            </Button>
          )}
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        screenNumber="05"
        title="Contract Template Studio"
        subtitle="Controlled clauses and commercial parameters"
        actions={
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setIsAnalyzerOpen(true)}
              className="text-xs border border-emerald-500/40 text-emerald-400 bg-emerald-950/40 hover:bg-emerald-900/60"
            >
              ✨ AI Contract Analyzer
            </Button>
            {!isFormOpen && canCreate && (
              <Button variant="primary" onClick={() => setIsFormOpen(true)} className="text-xs">
                + NEW RECORD
              </Button>
            )}
          </div>
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

      {isAnalyzerOpen && (
        <AIContractAnalyzerModal onClose={() => setIsAnalyzerOpen(false)} />
      )}

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

      {selectedTemplate && (
        <ViewTemplateModal
          template={selectedTemplate}
          onClose={() => setSelectedTemplate(null)}
          canApprove={canApprove}
          isApproving={approvingId === selectedTemplate.id}
          onApprove={handleApprove}
        />
      )}
    </div>
  )
}

function ViewTemplateModal({
  template,
  onClose,
  canApprove,
  isApproving,
  onApprove,
}: {
  template: ContractTemplate
  onClose: () => void
  canApprove: boolean
  isApproving: boolean
  onApprove: (template: ContractTemplate) => void
}) {
  const clauseEntries = Object.entries(template.clauses || {})

  return (
    <Modal title={`Contract Template — ${template.name} v${template.version}`} onClose={onClose} maxWidth="max-w-2xl">
      <div className="space-y-4 max-h-[75vh] overflow-y-auto pr-1">
        <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
          <div className="flex items-center gap-2">
            <Badge variant={templateStatusBadgeVariant(template.status)}>
              {template.status.toUpperCase()}
            </Badge>
            <span className="rounded bg-navy-800 px-2.5 py-0.5 text-xs font-medium text-emerald-400 border border-emerald-500/20">
              {template.contract_type}
            </span>
          </div>
          <span className="text-xs text-ink-muted">
            Version: <strong>{template.version}</strong>
          </span>
        </div>

        <div className="rounded-lg border border-emerald-500/10 bg-emerald-500/5 p-3 text-xs">
          <span className="block font-semibold text-emerald-400 uppercase tracking-wider mb-1">
            Linked Shariah Decision / Fatwa
          </span>
          <p className="text-ink-primary font-medium">
            {template.shariah_decision_code ? (
              <span className="inline-flex items-center gap-1.5">
                <span className="rounded bg-emerald-500/20 px-2 py-0.5 text-emerald-300 font-mono">
                  {template.shariah_decision_code}
                </span>
                <span>(Official Shariah Board Approval)</span>
              </span>
            ) : (
              <span className="text-amber-400/90">No Shariah Decision linked yet.</span>
            )}
          </p>
        </div>

        <div>
          <span className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-2">
            Contract Clauses ({clauseEntries.length})
          </span>
          {clauseEntries.length === 0 ? (
            <p className="text-sm text-ink-secondary">No clauses defined.</p>
          ) : (
            <div className="divide-y divide-white/5 rounded-lg border border-white/8 bg-navy-800/40">
              {clauseEntries.map(([key, val]) => (
                <div key={key} className="p-3 text-xs flex flex-col sm:flex-row sm:items-start justify-between gap-1">
                  <span className="font-semibold text-ink-secondary font-mono capitalize">
                    {key.replace(/_/g, " ")}
                  </span>
                  <span className="text-ink-primary sm:text-right max-w-sm whitespace-pre-wrap">
                    {typeof val === "object" ? JSON.stringify(val) : String(val ?? "—")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center justify-end gap-2 pt-3 border-t border-white/10">
          <Button variant="secondary" onClick={onClose} disabled={isApproving}>
            Close
          </Button>
          {canApprove && template.status === "draft" && (
            <Button
              variant="primary"
              disabled={isApproving}
              onClick={() => onApprove(template)}
            >
              {isApproving ? <Spinner className="h-4 w-4" /> : "Approve Contract Template"}
            </Button>
          )}
        </div>
      </div>
    </Modal>
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

function AIContractAnalyzerModal({ onClose }: { onClose: () => void }) {
  const [contractText, setContractText] = useState("")
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [analysis, setAnalysis] = useState<ContractAnalysisResult | null>(null)
  const [error, setError] = useState("")

  async function handleAnalyze() {
    if (!contractText.trim()) return
    setIsAnalyzing(true)
    setError("")
    try {
      const res = await analyzeContractWithAI(contractText)
      setAnalysis(res)
    } catch (err) {
      setError(extractErrorMessage(err, "Failed to analyze contract."))
    } finally {
      setIsAnalyzing(false)
    }
  }

  return (
    <Modal title="AI Shariah Contract Analyzer (BRD Section 9)" onClose={onClose}>
      <div className="space-y-4">
        <p className="text-xs text-ink-secondary">
          Paste legal contract clauses or draft agreements. The AI will extract contract type, PSR ratios, and detect prohibited clauses (e.g., capital guarantees).
        </p>

        <div>
          <label className="mb-1 block text-xs font-semibold uppercase text-ink-secondary">
            Contract Terms / Draft Text *
          </label>
          <textarea
            rows={5}
            value={contractText}
            onChange={(e) => setContractText(e.target.value)}
            placeholder="e.g. The bank shall manage investor funds under Mudarabah principles. Profits shall be shared 70% to depositors and 30% to Mudarib. Capital loss is borne by capital provider..."
            className="w-full rounded-md border border-white/10 bg-navy-800 p-2.5 text-xs text-ink-primary focus:border-emerald-500 focus:outline-none"
          />
        </div>

        <div className="flex items-center justify-between">
          <Button
            type="button"
            variant="secondary"
            className="text-xs"
            onClick={() =>
              setContractText(
                "This Agreement governs an Unrestricted Mudarabah Investment Pool. The Rabb-ul-Mal deposits funds with the Bank as Mudarib. Profits realized shall be shared 75% to Depositors and 25% to Mudarib. In the event of capital loss, the entire financial loss shall be borne by the Rabb-ul-Mal pro-rata to capital, and the Mudarib shall receive zero profit.",
              )
            }
          >
            Load Sample Mudarabah
          </Button>
          <Button
            type="button"
            variant="primary"
            disabled={isAnalyzing || !contractText.trim()}
            onClick={handleAnalyze}
            className="text-xs"
          >
            {isAnalyzing ? <Spinner className="h-3 w-3" /> : "⚡ Analyze Contract with AI"}
          </Button>
        </div>

        {error && <p className="text-xs text-rose-400">{error}</p>}

        {analysis && (
          <div className="space-y-3 rounded-lg border border-white/10 bg-navy-950/60 p-4">
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold text-ink-primary uppercase tracking-wider">
                Analysis Verdict:
              </span>
              <Badge variant={analysis.shariah_verdict === "COMPLIANT" ? "emerald" : "gold"}>
                {analysis.shariah_verdict}
              </Badge>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="p-2 rounded bg-navy-900 border border-white/5">
                <span className="text-ink-muted block text-[10px]">Identified Archetype:</span>
                <span className="font-semibold text-emerald-400 capitalize">
                  {analysis.contract_type.replace(/_/g, " ")}
                </span>
              </div>
              <div className="p-2 rounded bg-navy-900 border border-white/5">
                <span className="text-ink-muted block text-[10px]">Confidence Score:</span>
                <span className="font-mono text-ink-primary">
                  {(analysis.confidence_score * 100).toFixed(0)}% Match
                </span>
              </div>
              <div className="p-2 rounded bg-navy-900 border border-white/5">
                <span className="text-ink-muted block text-[10px]">Depositor / Mudarib PSR:</span>
                <span className="font-semibold text-ink-primary">
                  {analysis.depositor_psr ? `${analysis.depositor_psr}% / ${analysis.mudarib_psr}%` : "Fee-based"}
                </span>
              </div>
              <div className="p-2 rounded bg-navy-900 border border-white/5">
                <span className="text-ink-muted block text-[10px]">Calculation Frequency:</span>
                <span className="text-ink-primary">{analysis.profit_calculation_frequency}</span>
              </div>
            </div>

            {analysis.prohibited_terms_detected.length > 0 && (
              <div className="rounded border border-rose-500/30 bg-rose-950/20 p-2.5 text-xs text-rose-300">
                <p className="font-semibold mb-1">⚠️ Non-Negotiable Shariah Flags:</p>
                <ul className="list-disc pl-4 space-y-0.5">
                  {analysis.prohibited_terms_detected.map((term, i) => (
                    <li key={i}>{term}</li>
                  ))}
                </ul>
              </div>
            )}

            <div className="text-[11px] text-ink-muted pt-1">
              <span className="font-semibold text-ink-secondary">Loss Clause:</span> {analysis.loss_absorption_mechanism}
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}
