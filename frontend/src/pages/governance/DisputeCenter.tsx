import { useEffect, useState, type FormEvent } from "react"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { Card } from "../../components/Card"
import { Modal } from "../../components/Modal"
import { Spinner } from "../../components/Spinner"
import { Table, type TableColumn } from "../../components/Table"
import { useAuth } from "../../api/auth"
import {
  assignSupportRequest,
  createSupportRequest,
  fetchSupportRequests,
  resolveSupportRequest,
} from "../../api/supportRequests"
import { extractErrorMessage } from "../../api/errors"
import type { BadgeVariant, SupportRequest } from "../../types"

type PageState = "loading" | "loaded" | "error"

const REQUEST_TYPE_OPTIONS = [
  { value: "statement_correction", label: "Statement Correction" },
  { value: "payout_inquiry", label: "Payout Inquiry" },
  { value: "kyc_issue", label: "KYC Issue" },
  { value: "general_complaint", label: "General Complaint" },
  { value: "other", label: "Other" },
]

const STATUS_OPTIONS = ["open", "in_progress", "resolved", "closed"]
const PRIORITY_OPTIONS = ["low", "medium", "high"]

const STATUS_BADGE: Record<string, BadgeVariant> = {
  open: "gold",
  in_progress: "gold",
  resolved: "emerald",
  closed: "navy",
}

function statusBadgeVariant(status: string): BadgeVariant {
  return STATUS_BADGE[status] ?? "neutral"
}

const PRIORITY_BADGE: Record<string, BadgeVariant> = {
  low: "neutral",
  medium: "gold",
  high: "navy",
}

function priorityBadgeVariant(priority: string): BadgeVariant {
  return PRIORITY_BADGE[priority] ?? "neutral"
}

const selectClasses =
  "rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

export function DisputeCenter() {
  const { user } = useAuth()
  const canAssign = user?.role === "risk_compliance" || user?.role === "pool_manager"

  const [statusFilter, setStatusFilter] = useState("")
  const [priorityFilter, setPriorityFilter] = useState("")
  const [requests, setRequests] = useState<SupportRequest[]>([])
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [isNewModalOpen, setIsNewModalOpen] = useState(false)
  const [selectedRequest, setSelectedRequest] = useState<SupportRequest | null>(null)

  function loadRequests() {
    setPageState("loading")
    setPageError("")
    fetchSupportRequests({
      status: statusFilter || undefined,
      priority: priorityFilter || undefined,
    })
      .then((data) => {
        setRequests(data)
        setPageState("loaded")
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load support requests."))
        setPageState("error")
      })
  }

  useEffect(() => {
    loadRequests()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter, priorityFilter])

  function handleCreated(request: SupportRequest) {
    setRequests((prev) => [request, ...prev])
    setIsNewModalOpen(false)
  }

  function handleUpdated(updated: SupportRequest) {
    setRequests((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
    setSelectedRequest(updated)
  }

  const columns: TableColumn<SupportRequest>[] = [
    { header: "Subject", accessor: (r) => r.subject },
    {
      header: "Type",
      accessor: (r) => REQUEST_TYPE_OPTIONS.find((o) => o.value === r.request_type)?.label ?? r.request_type,
    },
    {
      header: "Priority",
      accessor: (r) => <Badge variant={priorityBadgeVariant(r.priority)}>{r.priority}</Badge>,
    },
    {
      header: "Status",
      accessor: (r) => <Badge variant={statusBadgeVariant(r.status)}>{r.status}</Badge>,
    },
    { header: "Pool", accessor: (r) => r.pool ?? "—" },
    { header: "Assigned To", accessor: (r) => r.assigned_to ?? "—" },
  ]

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-3">
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className={selectClasses}>
            <option value="">All statuses</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            className={selectClasses}
          >
            <option value="">All priorities</option>
            {PRIORITY_OPTIONS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </div>
        <Button variant="primary" onClick={() => setIsNewModalOpen(true)}>
          + New Request
        </Button>
      </div>

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading support requests...</span>
        </div>
      )}

      {pageState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{pageError}</p>
        </Card>
      )}

      {pageState === "loaded" && (
        <Card>
          {requests.length === 0 ? (
            <p className="text-sm text-ink-secondary">No support requests match these filters.</p>
          ) : (
            <Table
              columns={columns}
              data={requests}
              keyField={(r) => r.id}
              onRowClick={(r) => setSelectedRequest(r)}
            />
          )}
        </Card>
      )}

      {isNewModalOpen && (
        <NewSupportRequestModal onClose={() => setIsNewModalOpen(false)} onCreated={handleCreated} />
      )}

      {selectedRequest && (
        <SupportRequestDetailModal
          request={selectedRequest}
          canAssign={canAssign}
          currentUserId={user?.id ?? null}
          onClose={() => setSelectedRequest(null)}
          onUpdated={handleUpdated}
        />
      )}
    </div>
  )
}

function NewSupportRequestModal({
  onClose,
  onCreated,
}: {
  onClose: () => void
  onCreated: (request: SupportRequest) => void
}) {
  const [formError, setFormError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setFormError("")
    setIsSubmitting(true)
    try {
      const request = await createSupportRequest({
        request_type: String(form.get("request_type")),
        subject: String(form.get("subject")),
        description: String(form.get("description")),
        raised_by_name: String(form.get("raised_by_name")),
        priority: String(form.get("priority")),
      })
      onCreated(request)
    } catch (err) {
      setFormError(extractErrorMessage(err, "Unable to create support request."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="New Support Request" onClose={onClose}>
      <form onSubmit={handleSubmit} className="space-y-4">
        <label className={labelClasses}>
          Request Type
          <select name="request_type" required className={inputClasses}>
            {REQUEST_TYPE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
        <label className={labelClasses}>
          Raised By (Name)
          <input name="raised_by_name" required className={inputClasses} />
        </label>
        <label className={labelClasses}>
          Subject
          <input name="subject" required className={inputClasses} />
        </label>
        <label className={labelClasses}>
          Description
          <textarea name="description" required rows={4} className={inputClasses} />
        </label>
        <label className={labelClasses}>
          Priority
          <select name="priority" defaultValue="medium" className={inputClasses}>
            {PRIORITY_OPTIONS.map((p) => (
              <option key={p} value={p}>
                {p}
              </option>
            ))}
          </select>
        </label>
        {formError && <p className="text-sm text-red-400">{formError}</p>}
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? <Spinner className="h-4 w-4" /> : "Create Request"}
        </Button>
      </form>
    </Modal>
  )
}

function SupportRequestDetailModal({
  request,
  canAssign,
  currentUserId,
  onClose,
  onUpdated,
}: {
  request: SupportRequest
  canAssign: boolean
  currentUserId: number | null
  onClose: () => void
  onUpdated: (request: SupportRequest) => void
}) {
  const [actionError, setActionError] = useState("")
  const [isSaving, setIsSaving] = useState(false)
  const [isResolveFormOpen, setIsResolveFormOpen] = useState(false)

  const canResolve =
    request.assigned_to === currentUserId || canAssign

  async function handleAssignToMe() {
    if (!currentUserId) return
    setActionError("")
    setIsSaving(true)
    try {
      const updated = await assignSupportRequest(request.id, currentUserId)
      onUpdated(updated)
    } catch (err) {
      setActionError(extractErrorMessage(err, "Unable to assign this request."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleResolve(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      const updated = await resolveSupportRequest(request.id, String(form.get("resolution_notes")))
      onUpdated(updated)
      setIsResolveFormOpen(false)
    } catch (err) {
      setActionError(extractErrorMessage(err, "Unable to resolve this request."))
    } finally {
      setIsSaving(false)
    }
  }

  const isOpenOrInProgress = request.status === "open" || request.status === "in_progress"

  return (
    <Modal title={request.subject} onClose={onClose}>
      <div className="space-y-4">
        <div className="flex flex-wrap gap-2">
          <Badge variant={priorityBadgeVariant(request.priority)}>{request.priority}</Badge>
          <Badge variant={statusBadgeVariant(request.status)}>{request.status}</Badge>
        </div>

        <div className="space-y-1 text-sm">
          <p className="text-ink-secondary">
            Type:{" "}
            <span className="text-ink-primary">
              {REQUEST_TYPE_OPTIONS.find((o) => o.value === request.request_type)?.label ?? request.request_type}
            </span>
          </p>
          <p className="text-ink-secondary">
            Raised By: <span className="text-ink-primary">{request.raised_by_name}</span>
          </p>
          {request.pool && (
            <p className="text-ink-secondary">
              Pool: <span className="text-ink-primary">{request.pool}</span>
            </p>
          )}
          <p className="text-ink-secondary">
            Assigned To: <span className="text-ink-primary">{request.assigned_to ?? "Unassigned"}</span>
          </p>
        </div>

        <div>
          <p className={labelClasses}>Description</p>
          <p className="text-sm text-ink-primary">{request.description}</p>
        </div>

        {request.resolution_notes && (
          <div>
            <p className={labelClasses}>Resolution Notes</p>
            <p className="text-sm text-ink-primary">{request.resolution_notes}</p>
          </div>
        )}

        {actionError && <p className="text-sm text-red-400">{actionError}</p>}

        {isOpenOrInProgress && (
          <div className="flex flex-wrap gap-2">
            {canAssign && (
              <Button variant="secondary" onClick={handleAssignToMe} disabled={isSaving}>
                {isSaving ? <Spinner className="h-4 w-4" /> : "Assign to Me"}
              </Button>
            )}
            {canResolve && !isResolveFormOpen && (
              <Button variant="gold" onClick={() => setIsResolveFormOpen(true)} disabled={isSaving}>
                Resolve
              </Button>
            )}
          </div>
        )}

        {isResolveFormOpen && (
          <form onSubmit={handleResolve} className="space-y-3">
            <label className={labelClasses}>
              Resolution Notes
              <textarea name="resolution_notes" required rows={3} className={inputClasses} />
            </label>
            <Button type="submit" variant="gold" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Confirm Resolve"}
            </Button>
          </form>
        )}
      </div>
    </Modal>
  )
}
