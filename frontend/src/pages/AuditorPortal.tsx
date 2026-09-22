import { useEffect, useState } from "react"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { downloadAuditLogCsv, fetchAuditLog } from "../api/auditLog"
import { extractErrorMessage } from "../api/errors"
import type { AuditLogEntry } from "../types"

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

export function AuditorPortal() {
  const { user } = useAuth()
  const isAuditor = user?.role === "auditor"
  const isSuperAdmin = user?.role === "platform_super_admin"
  const canView = isAuditor || isSuperAdmin

  const [entries, setEntries] = useState<AuditLogEntry[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [pageError, setPageError] = useState("")
  const [modelName, setModelName] = useState("")
  const [dateFrom, setDateFrom] = useState("")
  const [dateTo, setDateTo] = useState("")
  const [isExporting, setIsExporting] = useState(false)
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null)

  useEffect(() => {
    if (!canView) {
      return
    }
    loadEntries()
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
      .then((data) => setEntries(data))
      .catch((error) => setPageError(extractErrorMessage(error, "Unable to load audit log.")))
      .finally(() => setIsLoading(false))
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

  return (
    <div>
      <PageHeader title="Reports" subtitle="Auditor Evidence Portal" />

      <Card title="Audit Log">
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
            />
          </label>
          <label className={labelClasses}>
            To
            <input
              type="date"
              value={dateTo}
              onChange={(event) => setDateTo(event.target.value)}
              className={inputClasses}
            />
          </label>
          <Button variant="outline" onClick={loadEntries} disabled={isLoading}>
            Apply Filters
          </Button>
          <Button variant="gold" onClick={() => void handleExport()} disabled={isExporting}>
            {isExporting ? <Spinner className="h-4 w-4" /> : "Export CSV"}
          </Button>
        </div>

        {pageError && <p className="mb-4 text-sm text-red-400">{pageError}</p>}

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
    </div>
  )
}
