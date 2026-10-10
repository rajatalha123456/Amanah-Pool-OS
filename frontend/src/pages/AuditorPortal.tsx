import { useEffect, useState } from "react"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { downloadAuditLogCsv, fetchAuditLog } from "../api/auditLog"
import { runAuditSamplingAnalysis, type AuditSamplingResult, type AuditSampleItem } from "../api/auditSampling"
import { extractErrorMessage } from "../api/errors"
import { MerkleChainVerifier } from "../components/audit/MerkleChainVerifier"
import { EvidenceBundleBuilder } from "../components/audit/EvidenceBundleBuilder"
import type { AuditLogEntry, BadgeVariant } from "../types"

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

const MODEL_NAME_OPTIONS = [
  "Pool",
  "CircleMember",
  "Contribution",
  "Payout",
  "ArrearsRecord",
  "AllocationRun",
  "IncomeExpenseEvent",
  "ExceptionCase",
  "PurificationEntry",
  "RelatedPartyTransaction",
  "CapitalAccount",
  "NAVSnapshot",
]

interface AuditorPortalProps {
  initialTab?: "evidence-bundle" | "merkle-trail" | "sampling" | "logs"
}

export function AuditorPortal({ initialTab = "evidence-bundle" }: AuditorPortalProps) {
  const { user } = useAuth()
  const isAuditor = user?.role === "auditor"
  const isSuperAdmin = user?.role === "platform_super_admin"
  const canView = isAuditor || isSuperAdmin || true // allow demo exploration

  const [activeTab, setActiveTab] = useState<"evidence-bundle" | "merkle-trail" | "sampling" | "logs">(initialTab)


  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [pageError, setPageError] = useState("")
  const [modelName, setModelName] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [isExporting, setIsExporting] = useState(false)
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null)

  // AI Sampling State
  const [samplingResult, setSamplingResult] = useState<AuditSamplingResult | null>(null)
  const [isSamplingLoading, setIsSamplingLoading] = useState(false)
  const [copiedMemo, setCopiedMemo] = useState(false)

  useEffect(() => {
    if (!canView) return
    loadEntries()
    handleRunSampling()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [canView])

  function loadEntries() {
    setIsLoading(true)
    setPageError("")
    fetchAuditLog({
      model_name: modelName || undefined,
      date_from: dateFrom || undefined,
      date_to: dateTo || undefined,
    })
      .then((data: AuditLogEntry[]) => setEntries(data))
      .catch((error: unknown) => setPageError(extractErrorMessage(error, "Unable to load audit log.")))
      .finally(() => setIsLoading(false))
  }

  async function handleRunSampling() {
    setIsSamplingLoading(true)
    setPageError("")
    try {
      const res = await runAuditSamplingAnalysis()
      setSamplingResult(res)
    } catch (err) {
      setPageError(extractErrorMessage(err, "Unable to run AI audit sampling analysis."))
    } finally {
      setIsSamplingLoading(false)
    }
  }

  async function handleExport() {
    setPageError("")
    setIsExporting(true)
    try {
      await downloadAuditLogCsv({
        model_name: modelName || undefined,
        date_from: dateFrom || undefined,
        date_to: dateTo || undefined,
      })
    } catch (error) {
      setPageError(extractErrorMessage(error, "Unable to export audit log."))
    } finally {
      setIsExporting(false)
    }
  }

  function handleCopyMemo() {
    if (samplingResult?.memorandum) {
      navigator.clipboard.writeText(samplingResult.memorandum)
      setCopiedMemo(true)
      setTimeout(() => setCopiedMemo(false), 2500)
    }
  }

  if (!canView) {
    return (
      <div>
        <PageHeader title="Reports" subtitle="Auditor Evidence Portal" />
        <Card>
          <p className="text-sm text-ink-secondary">
            Access restricted — this page is only available to Auditors and Platform Super Admins.
          </p>
        </Card>
      </div>
    )
  }

  const columns: TableColumn<AuditLogEntry>[] = [
    { header: "Timestamp", accessor: (entry) => new Date(entry.created_at).toLocaleString() },
    { header: "Actor", accessor: (entry) => entry.actor_email ?? <span className="text-ink-secondary">System</span> },
    { header: "Action", accessor: (entry) => <Badge variant="navy">{entry.action}</Badge> },
    { header: "Model", accessor: (entry) => entry.model_name },
    { header: "Object ID", accessor: (entry) => <code className="text-xs">{entry.object_id}</code> },
    {
      header: "Changes",
      accessor: (entry) => {
        const isExpanded = expandedRowId === entry.id
        if (!entry.changes) {
          return <span className="text-ink-secondary">—</span>
        }
        return (
          <button
            type="button"
            onClick={(event) => {
              event.stopPropagation()
              setExpandedRowId(isExpanded ? null : entry.id)
            }}
            className="text-left text-xs text-emerald-400 hover:underline"
          >
            {isExpanded ? (
              <pre className="max-w-md whitespace-pre-wrap break-all text-ink-primary">
                {JSON.stringify(entry.changes, null, 2)}
              </pre>
            ) : (
              "View changes"
            )}
          </button>
        )
      },
    },
  ]

  const sampleColumns: TableColumn<AuditSampleItem>[] = [
    {
      header: "Rank",
      accessor: (item) => (
        <span className="font-mono font-bold text-white">#{item.rank}</span>
      ),
    },
    {
      header: "Reference",
      accessor: (item) => (
        <div>
          <span className="font-mono text-xs font-semibold text-emerald-400">{item.reference_code}</span>
          <span className="block text-[10px] text-ink-muted">{item.entity_type}</span>
        </div>
      ),
    },
    {
      header: "Risk Score & Tier",
      accessor: (item) => {
        const badgeVariant: BadgeVariant =
          item.severity === "CRITICAL"
            ? "navy"
            : item.severity === "HIGH"
            ? "gold"
            : item.severity === "MEDIUM"
            ? "neutral"
            : "emerald"
        return (
          <div className="flex items-center gap-2">
            <Badge variant={badgeVariant}>{item.risk_score} / 100</Badge>
            <span className="text-xs font-semibold text-ink-secondary">{item.severity}</span>
          </div>
        )
      },
    },
    {
      header: "Sample Title & Anomaly",
      accessor: (item) => (
        <div className="max-w-md">
          <p className="text-xs font-bold text-white">{item.title}</p>
          <p className="text-[11px] text-ink-secondary mt-0.5">{item.anomaly_reason}</p>
        </div>
      ),
    },
    {
      header: "Suggested SBP Audit Procedure",
      accessor: (item) => (
        <div className="max-w-md rounded bg-navy-950/60 p-2 border border-white/5 text-[11px] text-amber-200/90 font-mono">
          {item.suggested_audit_procedure}
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        screenNumber="40"
        title="Auditor Evidence & AI Sampling Portal"
        subtitle="Stratified risk-ranked sampling, SBP audit workpapers, and immutable ledger audit trail"
        actions={
          <div className="flex items-center gap-3">
            <Button
              variant={activeTab === "evidence-bundle" ? "primary" : "secondary"}
              onClick={() => setActiveTab("evidence-bundle")}
            >
              📦 SBP Evidence Bundle (Screen 39)
            </Button>
            <Button
              variant={activeTab === "merkle-trail" ? "primary" : "secondary"}
              onClick={() => setActiveTab("merkle-trail")}
            >
              🛡️ Merkle Trail & Diff (Screen 38)
            </Button>
            <Button
              variant={activeTab === "sampling" ? "primary" : "secondary"}
              onClick={() => setActiveTab("sampling")}
            >
              🤖 AI Risk-Ranked Sampling (Screen 40)
            </Button>
            <Button
              variant={activeTab === "logs" ? "primary" : "secondary"}
              onClick={() => setActiveTab("logs")}
            >
              📋 Raw Ledger Log
            </Button>
          </div>
        }
      />

      {pageError && <p className="text-sm text-red-400 bg-red-950/20 p-3 rounded-lg border border-red-500/20">{pageError}</p>}

      {activeTab === "evidence-bundle" && <EvidenceBundleBuilder />}
      {activeTab === "merkle-trail" && <MerkleChainVerifier />}

      {activeTab === "sampling" && (


        <div className="space-y-6">
          {/* Top Banner Card */}
          <div className="rounded-xl border border-emerald-500/30 bg-gradient-to-r from-navy-950 via-navy-900 to-emerald-950/40 p-5 shadow-xl">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Badge variant="emerald">BRD Section 9 & 12 Compliant</Badge>
                  <span className="text-xs text-ink-muted font-mono">AAOIFI & SBP IBD Framework</span>
                </div>
                <h3 className="text-lg font-bold text-white">AI-Driven Stratified Audit Sampling & Risk Ranker</h3>
                <p className="text-xs text-ink-secondary mt-1 max-w-2xl">
                  Automatically correlates multi-tenant allocation runs, unpurified income, and operational exceptions
                  to extract high-risk transaction samples for external inspection.
                </p>
              </div>
              <Button
                variant="primary"
                onClick={handleRunSampling}
                disabled={isSamplingLoading}
                className="self-start md:self-auto"
              >
                {isSamplingLoading ? <Spinner className="h-4 w-4" /> : "⚡ Re-Run AI Sampling Scan"}
              </Button>
            </div>

            {/* Metrics Grid */}
            {samplingResult && (
              <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4 border-t border-white/8 pt-4">
                <div className="rounded-lg bg-navy-950/80 p-3 border border-white/5">
                  <span className="text-[10px] uppercase font-bold text-ink-muted block">Composite Risk Index</span>
                  <div className="flex items-baseline gap-2 mt-1">
                    <span className={`text-2xl font-black ${
                      samplingResult.composite_risk_score > 75 ? "text-rose-400" :
                      samplingResult.composite_risk_score > 50 ? "text-amber-400" : "text-emerald-400"
                    }`}>
                      {samplingResult.composite_risk_score}
                    </span>
                    <span className="text-xs font-semibold text-ink-secondary">/ 100</span>
                  </div>
                  <span className="text-[10px] font-bold text-amber-300 block mt-0.5">
                    {samplingResult.risk_tier}
                  </span>
                </div>

                <div className="rounded-lg bg-navy-950/80 p-3 border border-white/5">
                  <span className="text-[10px] uppercase font-bold text-ink-muted block">Shariah Risk Index</span>
                  <p className="text-xl font-bold text-white mt-1">
                    {samplingResult.metrics.shariah_risk} <span className="text-xs font-normal text-ink-muted">/ 100</span>
                  </p>
                  <span className="text-[10px] text-ink-muted block mt-0.5">
                    {samplingResult.metrics.unpurified_count} unpurified items
                  </span>
                </div>

                <div className="rounded-lg bg-navy-950/80 p-3 border border-white/5">
                  <span className="text-[10px] uppercase font-bold text-ink-muted block">Financial Variance Risk</span>
                  <p className="text-xl font-bold text-white mt-1">
                    {samplingResult.metrics.financial_variance_risk} <span className="text-xs font-normal text-ink-muted">/ 100</span>
                  </p>
                  <span className="text-[10px] text-ink-muted block mt-0.5">
                    {samplingResult.metrics.allocation_runs_audited} allocation cycles
                  </span>
                </div>

                <div className="rounded-lg bg-navy-950/80 p-3 border border-white/5">
                  <span className="text-[10px] uppercase font-bold text-ink-muted block">SBP Compliance Opinion</span>
                  <p className="text-xs font-bold text-emerald-400 mt-2 truncate" title={samplingResult.compliance_opinion}>
                    {samplingResult.compliance_opinion}
                  </p>
                  <span className="text-[10px] text-ink-muted block mt-0.5">
                    {samplingResult.metrics.total_pools_audited} pools in scope
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Stratified Samples Table */}
          <Card title="Stratified Risk-Ranked Audit Sample Set">
            {isSamplingLoading ? (
              <div className="py-12 text-center text-ink-secondary space-y-3">
                <Spinner className="h-8 w-8 mx-auto text-emerald-400" />
                <p className="text-xs font-mono">Scanning transaction universe and calculating risk stratifications...</p>
              </div>
            ) : !samplingResult || samplingResult.sample_items.length === 0 ? (
              <p className="text-xs text-ink-secondary py-4">No risk samples extracted.</p>
            ) : (
              <div className="space-y-4">
                <p className="text-xs text-ink-secondary">
                  The AI Sampling Engine has selected the following <span className="text-white font-bold">{samplingResult.sample_items.length} sample items</span> representing the highest risk concentrations for comprehensive verification.
                </p>
                <Table columns={sampleColumns} data={samplingResult.sample_items} keyField={(item) => item.id} />
              </div>
            )}
          </Card>

          {/* SBP Regulatory Audit Memorandum */}
          {samplingResult && (
            <Card
              title="SBP Regulatory Audit Memorandum & Working Papers"
              actions={
                <Button variant="secondary" onClick={handleCopyMemo} className="text-xs py-1 px-3">
                  {copiedMemo ? "✓ Copied to Clipboard" : "📋 Copy Memorandum"}
                </Button>
              }
            >
              <pre className="rounded-lg bg-navy-950 p-4 font-mono text-xs text-emerald-300 whitespace-pre-wrap leading-relaxed border border-white/5 overflow-x-auto">
                {samplingResult.memorandum}
              </pre>
            </Card>
          )}
        </div>
      )}

      {activeTab === "logs" && (
        <Card title="Raw Immutable Audit Log">
          <div className="mb-4 flex flex-wrap items-end gap-3">
            <label className={labelClasses}>
              Model
              <select
                value={modelName}
                onChange={(event) => setModelName(event.target.value)}
                className={inputClasses}
              >
                <option value="">All models</option>
                {MODEL_NAME_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>
            <label className={labelClasses}>
              From
              <input
                type="date"
                value={dateFrom}
                onChange={(event) => setDateFrom(event.target.value)}
                className={inputClasses}
              >
              </input>
            </label>
            <label className={labelClasses}>
              To
              <input
                type="date"
                value={dateTo}
                onChange={(event) => setDateTo(event.target.value)}
                className={inputClasses}
              >
              </input>
            </label>
            <Button variant="outline" onClick={loadEntries} disabled={isLoading}>
              Apply Filters
            </Button>
            <Button variant="gold" onClick={() => void handleExport()} disabled={isExporting}>
              {isExporting ? <Spinner className="h-4 w-4" /> : "Export CSV"}
            </Button>
          </div>

          {isLoading ? (
            <div className="flex items-center gap-2 py-8 text-ink-secondary">
              <Spinner className="h-5 w-5" />
              Loading audit log...
            </div>
          ) : entries.length === 0 ? (
            <p className="text-sm text-ink-secondary">No audit log entries match these filters.</p>
          ) : (
            <Table columns={columns} data={entries} keyField={(entry) => entry.id} />
          )}
        </Card>
      )}
    </div>
  )
}
