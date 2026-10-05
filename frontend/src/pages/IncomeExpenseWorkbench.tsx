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
import { StatCard } from "../components/StatCard"
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

const CATEGORY_OPTIONS = [
  "profit_income",
  "operational_expense",
  "provision_reversal",
  "asset_financing_yield",
  "mudarib_share",
  "wakalah_fee",
  "takaful_contribution",
]

const selectClasses =
  "rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

export function IncomeExpenseWorkbench() {
  const { user } = useAuth()
  const canCreate =
    !user?.role ||
    ["finance_maker", "platform_super_admin", "pool_manager", "superadmin"].includes(user.role)
  const canPost =
    !user?.role ||
    ["finance_checker", "platform_super_admin", "superadmin"].includes(user.role)

  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState("")
  const [events, setEvents] = useState<IncomeExpenseEvent[]>([])
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [successMessage, setSuccessMessage] = useState("")
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
    setSuccessMessage("Performance event logged successfully.")
  }

  async function handlePost(event: IncomeExpenseEvent) {
    setRowError("")
    setSuccessMessage("")
    setPostingId(event.id)
    try {
      const updated = await postIncomeExpenseEvent(event.id)
      setEvents((prev) => prev.map((item) => (item.id === updated.id ? updated : item)))
      setSuccessMessage(`Event posted successfully to pool ledger.`)
    } catch (err) {
      setRowError(extractErrorMessage(err, "Unable to post this event. Checker authorization required."))
    } finally {
      setPostingId(null)
    }
  }

  const totalIncome = events
    .filter((e) => e.event_type === "income")
    .reduce((sum, e) => sum + Number(e.amount || 0), 0)

  const totalExpense = events
    .filter((e) => e.event_type === "expense")
    .reduce((sum, e) => sum + Number(e.amount || 0), 0)

  const netYield = totalIncome - totalExpense
  const pendingCount = events.filter((e) => e.status === "pending").length

  const columns: TableColumn<IncomeExpenseEvent>[] = [
    {
      header: "Type",
      accessor: (event) => <Badge variant={EVENT_TYPE_BADGE[event.event_type]}>{event.event_type.toUpperCase()}</Badge>,
    },
    { header: "Category", accessor: (event) => event.category.replace(/_/g, " ") },
    {
      header: "Amount (PKR)",
      accessor: (event) => (
        <span className={event.event_type === "income" ? "text-emerald-400 font-semibold" : "text-amber-400 font-semibold"}>
          {Number(event.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    { header: "Event Date", accessor: (event) => event.event_date },
    {
      header: "Description",
      accessor: (event) => <span className="text-xs text-ink-secondary">{event.description}</span>,
    },
    {
      header: "Status",
      accessor: (event) => <Badge variant={STATUS_BADGE[event.status]}>{event.status.toUpperCase()}</Badge>,
    },
    {
      header: "Action",
      accessor: (event) =>
        event.status === "pending" ? (
          canPost ? (
            <Button
              variant="primary"
              className="py-1 px-3 text-xs"
              disabled={postingId === event.id}
              onClick={() => handlePost(event)}
            >
              {postingId === event.id ? <Spinner className="h-3 w-3" /> : "Authorize & Post"}
            </Button>
          ) : (
            <span className="text-xs text-gold-400">Pending Checker</span>
          )
        ) : (
          <span className="text-xs text-emerald-400">✓ Posted</span>
        ),
    },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-white/8 bg-navy-900/60 p-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-ink-secondary">Select Pool:</span>
          <select
            value={selectedPoolId}
            onChange={(event) => setSelectedPoolId(event.target.value)}
            className={selectClasses + " max-w-sm"}
          >
            {pools.map((pool) => (
              <option key={pool.id} value={pool.id}>
                {pool.code} — {pool.name}
              </option>
            ))}
          </select>
        </div>
        {canCreate && selectedPoolId && (
          <Button variant="primary" onClick={() => setIsNewOpen(true)}>
            + New Income / Expense Record
          </Button>
        )}
      </div>

      {(pageError || rowError) && (
        <div className="rounded border border-red-500/30 bg-red-950/20 p-3 text-sm text-red-400">
          {pageError || rowError}
        </div>
      )}

      {successMessage && (
        <div className="rounded border border-emerald-500/30 bg-emerald-950/20 p-3 text-sm text-emerald-400">
          {successMessage}
        </div>
      )}

      {/* Summary KPI Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <StatCard
          label="Total Pool Income"
          value={`PKR ${totalIncome.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          deltaTone="positive"
        />
        <StatCard
          label="Total Pool Expense"
          value={`PKR ${totalExpense.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          deltaTone="neutral"
        />
        <StatCard
          label="Net Operating Spread"
          value={`PKR ${netYield.toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
          deltaTone={netYield >= 0 ? "positive" : "negative"}
        />
        <StatCard
          label="Pending Authorizations"
          value={String(pendingCount)}
          deltaTone={pendingCount > 0 ? "negative" : "positive"}
        />
      </div>

      {pools.length === 0 && pageState === "loaded" && (
        <Card>
          <p className="text-sm text-ink-secondary">No operational pools available. Create or activate a pool first.</p>
        </Card>
      )}

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-8 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading performance events...</span>
        </div>
      )}

      {pageState === "loaded" && pools.length > 0 && (
        <Card title="Performance Events & Daily Feeds">
          {events.length === 0 ? (
            <div className="py-8 text-center">
              <p className="text-sm text-ink-secondary">No income or expense events logged for this pool yet.</p>
              <p className="mt-1 text-xs text-ink-muted">
                Add an operational expense, financing yield, or management fee event using the button above.
              </p>
            </div>
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
    amount: "150000.00",
    event_date: new Date().toISOString().split("T")[0],
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
    <Modal title="New Income / Expense Record" onClose={onClose}>
      <form onSubmit={submit} className="space-y-3">
        <div>
          <label className={labelClasses}>Type *</label>
          <select
            value={form.event_type}
            onChange={(event) => setForm({ ...form, event_type: event.target.value as "income" | "expense" })}
            className={inputClasses}
          >
            <option value="income">Income (Pool Inflow)</option>
            <option value="expense">Expense (Direct Permitted Expense)</option>
          </select>
        </div>
        <div>
          <label className={labelClasses}>Category *</label>
          <select
            required
            value={form.category}
            onChange={(event) => setForm({ ...form, category: event.target.value })}
            className={inputClasses}
          >
            {CATEGORY_OPTIONS.map((option) => (
              <option key={option} value={option}>
                {option.replace(/_/g, " ")}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className={labelClasses}>Amount (PKR) *</label>
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
          <label className={labelClasses}>Event Date *</label>
          <input
            required
            type="date"
            value={form.event_date}
            onChange={(event) => setForm({ ...form, event_date: event.target.value })}
            className={inputClasses}
          />
        </div>
        <div>
          <label className={labelClasses}>Description & Reference *</label>
          <textarea
            required
            rows={3}
            placeholder="e.g. Financing asset profit distribution from Diminishing Musharakah facility #DM-04"
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
          <Button type="submit" variant="primary" disabled={isSubmitting}>
            {isSubmitting ? <Spinner className="h-4 w-4" /> : "Save Record"}
          </Button>
        </div>
      </form>
    </Modal>
  )
}
