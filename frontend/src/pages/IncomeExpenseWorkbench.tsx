import { useEffect, useState, type FormEvent } from "react"
import { useAuth } from "../api/auth"
import { fetchPools } from "../api/pools"
import { createIncomeExpenseEvent, fetchIncomeExpenseEvents, postIncomeExpenseEvent } from "../api/accounting"
import { extractErrorMessage } from "../api/errors"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { Modal } from "../components/Modal"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import type { BadgeVariant, IncomeExpenseEvent, Pool } from "../types"

type PageState = "loading" | "loaded" | "error"

const EVENT_TYPE_BADGE: Record<string, BadgeVariant> = {
  income: "emerald",
  expense: "gold",
}

const STATUS_BADGE: Record<string, BadgeVariant> = {
  pending: "gold",
  posted: "emerald",
}

const CATEGORY_OPTIONS = ["profit_income", "operational_expense", "provision_reversal"]

const selectClasses =
  "rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

export function IncomeExpenseWorkbench() {
  const { user } = useAuth()
  const canCreate = user?.role === "finance_maker"
  const canPost = user?.role === "finance_checker"

  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState("")
  const [events, setEvents] = useState<IncomeExpenseEvent[]>([])
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [isNewOpen, setIsNewOpen] = useState(false)
  const [postingId, setPostingId] = useState<string | null>(null)
  const [rowError, setRowError] = useState("")

  useEffect(() => {
    fetchPools()
      .then((data) => {
        setPools(data)
        if (data.length > 0) {
          setSelectedPoolId(data[0].id)
        } else {
          setPageState("loaded")
        }
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load pools."))
        setPageState("error")
      })
  }, [])

  function loadEvents(poolId: string) {
    setPageState("loading")
    setPageError("")
    fetchIncomeExpenseEvents(poolId)
      .then((data) => {
        setEvents(data)
        setPageState("loaded")
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load income/expense events."))
        setPageState("error")
      })
  }

  useEffect(() => {
    if (selectedPoolId) {
      loadEvents(selectedPoolId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedPoolId])

  function handleCreated(event: IncomeExpenseEvent) {
    setEvents((prev) => [event, ...prev])
    setIsNewOpen(false)
  }

  async function handlePost(event: IncomeExpenseEvent) {
    setRowError("")
    setPostingId(event.id)
    try {
      const updated = await postIncomeExpenseEvent(event.id)
      setEvents((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setRowError(extractErrorMessage(err, "Unable to post this event."))
    } finally {
      setPostingId(null)
    }
  }

  const columns: TableColumn<IncomeExpenseEvent>[] = [
    {
      header: "Type",
      accessor: (event) => <Badge variant={EVENT_TYPE_BADGE[event.event_type]}>{event.event_type}</Badge>,
    },
    { header: "Category", accessor: (event) => event.category },
    { header: "Amount", accessor: (event) => event.amount },
    { header: "Event Date", accessor: (event) => event.event_date },
    {
      header: "Status",
      accessor: (event) => <Badge variant={STATUS_BADGE[event.status]}>{event.status}</Badge>,
    },
    {
      header: "Action",
      accessor: (event) =>
        canPost && event.status === "pending" ? (
          <Button variant="primary" disabled={postingId === event.id} onClick={() => handlePost(event)}>
            {postingId === event.id ? <Spinner className="h-4 w-4" /> : "Post"}
          </Button>
        ) : null,
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <select
          value={selectedPoolId}
          onChange={(event) => setSelectedPoolId(event.target.value)}
          className={selectClasses + " max-w-xs"}
        >
          <option value="">Select pool</option>
          {pools.map((pool) => (
            <option key={pool.id} value={pool.id}>
              {pool.name} ({pool.code})
            </option>
          ))}
        </select>
        {canCreate && selectedPoolId && <Button onClick={() => setIsNewOpen(true)}>+ New Event</Button>}
      </div>

      {(pageError || rowError) && <p className="text-sm text-red-400">{pageError || rowError}</p>}
      {pools.length === 0 && pageState === "loaded" && (
        <Card>
          <p className="text-sm text-ink-secondary">No pools available.</p>
        </Card>
      )}
      {pageState === "loading" && <Spinner className="h-5 w-5" />}
      {pageState === "loaded" && pools.length > 0 && (
        <Card>
          {events.length === 0 ? (
            <p className="text-sm text-ink-secondary">No income/expense events for this pool yet.</p>
          ) : (
            <Table columns={columns} data={events} keyField={(event) => event.id} />
          )}
        </Card>
      )}

      {isNewOpen && (
        <NewEventModal
          poolId={selectedPoolId}
          onClose={() => setIsNewOpen(false)}
          onCreated={handleCreated}
        />
      )}
    </div>
  )
}

function NewEventModal({
  poolId,
  onClose,
  onCreated,
}: {
  poolId: string
  onClose: () => void
  onCreated: (event: IncomeExpenseEvent) => void
}) {
  const [form, setForm] = useState({
    event_type: "income" as "income" | "expense",
    category: CATEGORY_OPTIONS[0],
    amount: "",
    event_date: "",
    description: "",
  })
  const [error, setError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setError("")
    setIsSubmitting(true)
    try {
      const created = await createIncomeExpenseEvent({ pool: poolId, ...form })
      onCreated(created)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to create event."))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <Modal title="New Income/Expense Event" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className={labelClasses}>Type</label>
          <select
            value={form.event_type}
            onChange={(event) => setForm({ ...form, event_type: event.target.value as "income" | "expense" })}
            className={inputClasses}
          >
            <option value="income">Income</option>
            <option value="expense">Expense</option>
          </select>
        </div>
        <div>
          <label className={labelClasses}>Category</label>
          <input
            list="category-options"
            required
            value={form.category}
            onChange={(event) => setForm({ ...form, category: event.target.value })}
            className={inputClasses}
          />
          <datalist id="category-options">
            {CATEGORY_OPTIONS.map((option) => (
              <option key={option} value={option} />
            ))}
          </datalist>
        </div>
        <div>
          <label className={labelClasses}>Amount</label>
          <input
            required
            type="number"
            min="0"
            step="0.01"
            value={form.amount}
            onChange={(event) => setForm({ ...form, amount: event.target.value })}
            className={inputClasses}
          />
        </div>
        <div>
          <label className={labelClasses}>Event Date</label>
          <input
            required
            type="date"
            value={form.event_date}
            onChange={(event) => setForm({ ...form, event_date: event.target.value })}
            className={inputClasses}
          />
        </div>
        <div>
          <label className={labelClasses}>Description</label>
          <textarea
            required
            rows={3}
            value={form.description}
            onChange={(event) => setForm({ ...form, description: event.target.value })}
            className={inputClasses}
          />
        </div>
        {error && <p className="text-sm text-red-400">{error}</p>}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Create"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
