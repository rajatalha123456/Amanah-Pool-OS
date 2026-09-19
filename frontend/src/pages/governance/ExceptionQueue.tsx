import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card } from "../../components/Card"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { Table, type TableColumn } from "../../components/Table"
import { useAuth } from "../../api/auth"
import { fetchExceptions, updateExceptionAssignee } from "../../api/governance"
import { extractErrorMessage } from "../../api/errors"
import type { BadgeVariant, ExceptionCase } from "../../types"

type PageState = "loading" | "loaded" | "error"

const STATUS_OPTIONS = ["open", "investigating", "resolved", "dismissed"]
const SEVERITY_OPTIONS = ["low", "medium", "high", "critical"]

const STATUS_BADGE: Record<string, BadgeVariant> = {
  open: "gold",
  investigating: "gold",
  resolved: "emerald",
  dismissed: "navy",
}

function statusBadgeVariant(status: string): BadgeVariant {
  return STATUS_BADGE[status] ?? "neutral"
}

const SEVERITY_BADGE: Record<string, BadgeVariant> = {
  low: "neutral",
  medium: "gold",
  high: "gold",
  critical: "navy",
}

function severityBadgeVariant(severity: string): BadgeVariant {
  return SEVERITY_BADGE[severity] ?? "neutral"
}

const selectClasses =
  "rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

export function ExceptionQueue() {
  const { user } = useAuth()
  const navigate = useNavigate()
  const canAct = user?.role === "risk_compliance"

  const [statusFilter, setStatusFilter] = useState("")
  const [severityFilter, setSeverityFilter] = useState("")
  const [cases, setCases] = useState<ExceptionCase[]>([])
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [assignErrors, setAssignErrors] = useState<Record<string, string>>({})

  function loadCases() {
    setPageState("loading")
    setPageError("")
    fetchExceptions({
      status: statusFilter || undefined,
      severity: severityFilter || undefined,
    })
      .then((data) => {
        setCases(data)
        setPageState("loaded")
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load exceptions."))
        setPageState("error")
      })
  }

  useEffect(() => {
    loadCases()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, severityFilter])

  async function handleAssignToMe(exceptionCase: ExceptionCase) {
    if (!user) return
    setAssignErrors((prev) => ({ ...prev, [exceptionCase.id]: "" }))
    try {
      const updated = await updateExceptionAssignee(exceptionCase.id, user.id)
      setCases((prev) => prev.map((c) => (c.id === updated.id ? updated : c)))
    } catch (err) {
      setAssignErrors((prev) => ({
        ...prev,
        [exceptionCase.id]: extractErrorMessage(err, "Unable to assign."),
      }))
    }
  }

  const columns: TableColumn<ExceptionCase>[] = [
    { header: "Title", accessor: (c) => c.title },
    { header: "Source Module", accessor: (c) => c.source_module },
    {
      header: "Severity",
      accessor: (c) => <Badge variant={severityBadgeVariant(c.severity)}>{c.severity}</Badge>,
    },
    {
      header: "Status",
      accessor: (c) => <Badge variant={statusBadgeVariant(c.status)}>{c.status}</Badge>,
    },
    { header: "Pool", accessor: (c) => c.pool ?? "—" },
    { header: "Created", accessor: (c) => new Date(c.created_at).toLocaleDateString() },
    {
      header: "Action",
      accessor: (c) =>
        canAct && (c.status === "open" || c.status === "investigating") ? (
          <Button
            variant="secondary"
            onClick={(event) => {
              event.stopPropagation()
              handleAssignToMe(c)
            }}
          >
            Assign to me
          </Button>
        ) : null,
    },
  ]

  return (
    <div>
      <div className="mb-4 flex flex-wrap gap-3">
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          className={selectClasses}
        >
          <option value="">All statuses</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>

        <select
          value={severityFilter}
          onChange={(e) => setSeverityFilter(e.target.value)}
          className={selectClasses}
        >
          <option value="">All severities</option>
          {SEVERITY_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      </div>

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading exceptions...</span>
        </div>
      )}

      {pageState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{pageError}</p>
        </Card>
      )}

      {pageState === "loaded" && (
        <div className="space-y-3">
          {cases.length === 0 ? (
            <Card>
              <p className="text-sm text-ink-secondary">No exceptions match these filters.</p>
            </Card>
          ) : (
            <Card>
              <Table
                columns={columns}
                data={cases}
                keyField={(c) => c.id}
                onRowClick={(c) => navigate(`/exceptions/${c.id}`)}
              />
            </Card>
          )}

          {Object.values(assignErrors).some(Boolean) && (
            <p className="text-sm text-red-400">
              {Object.values(assignErrors).find(Boolean)}
            </p>
          )}
        </div>
      )}
    </div>
  )
}
