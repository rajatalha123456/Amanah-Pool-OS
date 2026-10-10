import { useEffect, useState } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import {
  fetchIncomeExpenseEvents,
  fetchPoolIncomeExpenseSummary,
  createIncomeExpenseEvent,
  postIncomeExpenseEvent,
  quarantineIncomeToCharity,
  reclassifyExpense,
  scanOverheadLeakage,
} from "../api/accounting"
import { fetchPools } from "../api/pools"
import type {
  CostClassification,
  CreateIncomeExpenseEventInput,
  IncomeExpenseEvent,
  Pool,
  PoolIncomeExpenseSummary,
} from "../types"

type FilterTab = "all" | "income" | "direct" | "overhead" | "charity"

export function IncomeExpenseWorkbench() {
  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState<string>("")
  const [events, setEvents] = useState<IncomeExpenseEvent[]>([])
  const [summary, setSummary] = useState<PoolIncomeExpenseSummary | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<FilterTab>("all")
  const [searchQuery, setSearchQuery] = useState("")

  // Scan status
  const [scanMessage, setScanMessage] = useState<string | null>(null)
  const [isScanning, setIsScanning] = useState(false)

  // Modal
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [modalError, setModalError] = useState<string | null>(null)
  const [form, setForm] = useState<CreateIncomeExpenseEventInput>({
    pool: "",
    event_type: "expense",
    cost_classification: "direct_permissible",
    category: "Asset Takaful",
    amount: "",
    event_date: new Date().toISOString().slice(0, 10),
    description: "",
    shariah_note: "",
  })

  // Load pools
  useEffect(() => {
    async function loadInitial() {
      try {
        const poolList = await fetchPools()
        setPools(poolList)
        if (poolList.length > 0) {
          const genPool = poolList.find((p) => p.code === "POOL-GEN-01") || poolList[0]
          setSelectedPoolId(genPool.id)
          setForm((prev) => ({ ...prev, pool: genPool.id }))
        }
      } catch (err) {
        console.error("Failed to load pools", err)
      }
    }
    loadInitial()
  }, [])

  // Load events & summary for selected pool
  async function loadData(poolId: string) {
    if (!poolId) return
    try {
      setIsLoading(true)
      const [eventsData, summaryData] = await Promise.all([
        fetchIncomeExpenseEvents(poolId),
        fetchPoolIncomeExpenseSummary(poolId),
      ])
      setEvents(eventsData)
      setSummary(summaryData)
    } catch (err) {
      console.error("Failed to load income/expense data", err)
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (selectedPoolId) {
      loadData(selectedPoolId)
    }
  }, [selectedPoolId])

  async function handleScanOverhead() {
    try {
      setIsScanning(true)
      setScanMessage(null)
      const res = await scanOverheadLeakage(selectedPoolId)
      setScanMessage(res.message)
      await loadData(selectedPoolId)
    } catch (err) {
      console.error("Scan failed", err)
    } finally {
      setIsScanning(false)
    }
  }

  async function handlePostEvent(id: string) {
    try {
      await postIncomeExpenseEvent(id)
      await loadData(selectedPoolId)
    } catch (err) {
      console.error("Failed to post event", err)
    }
  }

  async function handleQuarantine(id: string) {
    const reason = prompt("Enter Shariah reason for quarantining to Charity:")
    if (!reason) return
    try {
      await quarantineIncomeToCharity(id, reason)
      await loadData(selectedPoolId)
    } catch (err) {
      console.error("Failed to quarantine", err)
    }
  }

  async function handleToggleOverhead(event: IncomeExpenseEvent) {
    const targetClass =
      event.cost_classification === "indirect_overhead"
        ? "direct_permissible"
        : "indirect_overhead"
    const note =
      targetClass === "indirect_overhead"
        ? "Classified as indirect overhead: Absorbed 100% by Bank P&L per SBP IBD 03/2012."
        : "Verified as direct pool asset expense: Approved for deduction from Gross Pool Income."
    try {
      await reclassifyExpense(event.id, targetClass, note)
      await loadData(selectedPoolId)
    } catch (err) {
      console.error("Failed to reclassify", err)
    }
  }

  async function handleCreateSubmit(e: React.FormEvent) {
    e.preventDefault()
    setIsSubmitting(true)
    setModalError(null)
    try {
      await createIncomeExpenseEvent({
        ...form,
        pool: selectedPoolId,
      })
      setIsModalOpen(false)
      setForm({
        pool: selectedPoolId,
        event_type: "expense",
        cost_classification: "direct_permissible",
        category: "Asset Takaful",
        amount: "",
        event_date: new Date().toISOString().slice(0, 10),
        description: "",
        shariah_note: "",
      })
      await loadData(selectedPoolId)
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to record event")
    } finally {
      setIsSubmitting(false)
    }
  }

  // Filter events
  const filteredEvents = events.filter((e) => {
    if (activeTab === "income" && e.event_type !== "income") return false
    if (activeTab === "direct" && (!e.is_direct_expense || e.event_type !== "expense"))
      return false
    if (activeTab === "overhead" && !e.is_overhead_leakage) return false
    if (activeTab === "charity" && !e.quarantined_to_charity) return false

    if (searchQuery) {
      const q = searchQuery.toLowerCase()
      const matchCat = e.category.toLowerCase().includes(q)
      const matchDesc = e.description.toLowerCase().includes(q)
      if (!matchCat && !matchDesc) return false
    }
    return true
  })

  function formatPKR(val: number | string | undefined) {
    const num = typeof val === "string" ? parseFloat(val) : val ?? 0
    return `₨ ${num.toLocaleString("en-PK", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    })}`
  }

  return (
    <div className="space-y-6">
      <PageHeader
        screenNumber="03"
        title="Income & Expense Workbench — Direct Cost Segregation"
        subtitle="SBP IBD Circular 03/2012 Direct Operating Expense Segregation & Charity Purification Engine"
        actions={
          <div className="flex items-center gap-2">
            <Button
              variant="secondary"
              className="text-xs"
              onClick={handleScanOverhead}
              disabled={isScanning}
            >
              {isScanning ? <Spinner className="h-4 w-4" /> : "Scan for Overhead Leakage"}
            </Button>
            <Button
              variant="primary"
              className="bg-emerald-600 text-xs hover:bg-emerald-500"
              onClick={() => setIsModalOpen(true)}
            >
              + Record Income / Expense
            </Button>
          </div>
        }
      />

      {/* Pool Selector & Scan Message */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-ink-secondary uppercase">
            Active Pool Scope:
          </label>
          <select
            value={selectedPoolId}
            onChange={(e) => setSelectedPoolId(e.target.value)}
            className="rounded-md border border-white/10 bg-navy-950 px-3 py-1.5 text-sm text-ink-primary focus:border-gold-500 focus:outline-none"
          >
            {pools.map((p) => (
              <option key={p.id} value={p.id}>
                {p.code} — {p.name}
              </option>
            ))}
          </select>
        </div>

        {scanMessage && (
          <div className="rounded bg-gold-500/10 px-3 py-1 text-xs text-gold-400">
            {scanMessage}
          </div>
        )}
      </div>

      {/* Executive Net Distributable Profit Waterfall Deck */}
      {summary && (
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3 lg:grid-cols-6">
          <Card className="p-3 border-l-4 border-l-emerald-500">
            <span className="text-[10px] font-semibold text-ink-muted uppercase">
              1. Gross Income
            </span>
            <p className="mt-1 text-base font-bold text-emerald-400">
              {formatPKR(summary.total_income_gross)}
            </p>
            <span className="text-[10px] text-ink-secondary">All realized returns</span>
          </Card>

          <Card className="p-3 border-l-4 border-l-red-500">
            <span className="text-[10px] font-semibold text-ink-muted uppercase">
              2. Quarantined (NPI)
            </span>
            <p className="mt-1 text-base font-bold text-red-400">
              - {formatPKR(summary.non_permissible_income)}
            </p>
            <span className="text-[10px] text-ink-secondary">Charity Purification</span>
          </Card>

          <Card className="p-3 border-l-4 border-l-cyan-500">
            <span className="text-[10px] font-semibold text-ink-muted uppercase">
              3. Permissible Income
            </span>
            <p className="mt-1 text-base font-bold text-cyan-400">
              = {formatPKR(summary.net_permissible_income)}
            </p>
            <span className="text-[10px] text-ink-secondary">Gross Pool Permissible</span>
          </Card>

          <Card className="p-3 border-l-4 border-l-gold-500">
            <span className="text-[10px] font-semibold text-ink-muted uppercase">
              4. Direct Expenses
            </span>
            <p className="mt-1 text-base font-bold text-gold-400">
              - {formatPKR(summary.approved_direct_expenses)}
            </p>
            <span className="text-[10px] text-ink-secondary">Takaful & direct asset</span>
          </Card>

          <Card className="p-3 border-l-4 border-l-purple-500">
            <span className="text-[10px] font-semibold text-ink-muted uppercase">
              5. Overheads Blocked
            </span>
            <p className="mt-1 text-base font-bold text-purple-400">
              {formatPKR(summary.bank_absorbed_overheads)}
            </p>
            <span className="text-[10px] text-ink-secondary">100% Bank Absorbed</span>
          </Card>

          <Card className="p-3 border-l-4 border-l-emerald-400 bg-emerald-950/20">
            <span className="text-[10px] font-bold text-emerald-400 uppercase">
              6. Net Distributable
            </span>
            <p className="mt-1 text-base font-bold text-emerald-300">
              = {formatPKR(summary.net_distributable_profit)}
            </p>
            <span className="text-[10px] text-emerald-400/80">Distributable Profit Base</span>
          </Card>
        </div>
      )}

      {/* SBP Shariah Compliance Guardrail Alert Box */}
      {summary && summary.overhead_leakage_detected && (
        <div className="rounded-lg border border-gold-500/30 bg-gold-500/10 p-3.5">
          <div className="flex items-center gap-2">
            <span className="text-base">⚠️</span>
            <h4 className="text-xs font-semibold text-gold-400 uppercase">
              SBP Direct Cost Segregation Safeguard Active (IBD Circular 03/2012)
            </h4>
          </div>
          <p className="mt-1 text-xs text-ink-secondary leading-relaxed">
            <strong>{summary.overhead_leakage_count} indirect overhead expense items</strong>{" "}
            (totaling <strong>{formatPKR(summary.bank_absorbed_overheads)}</strong>) were flagged as
            bank operating expenses (e.g. branch rent, software licensing). Under SBP regulations,
            these have been <strong>strictly blocked from pool deduction</strong> and redirected to
            the Bank Mudarib P&L absorption account to prevent depositor yield dilution.
          </p>
        </div>
      )}

      {/* Filter Tabs & Search */}
      <div className="flex flex-col gap-3 rounded-lg border border-white/5 bg-navy-900/60 p-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-wrap items-center gap-1.5">
          <button
            onClick={() => setActiveTab("all")}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "all"
                ? "bg-emerald-600 text-white"
                : "bg-white/5 text-ink-secondary hover:text-ink-primary"
            }`}
          >
            All Items ({events.length})
          </button>
          <button
            onClick={() => setActiveTab("income")}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "income"
                ? "bg-emerald-600 text-white"
                : "bg-white/5 text-ink-secondary hover:text-ink-primary"
            }`}
          >
            Income Realization ({events.filter((e) => e.event_type === "income").length})
          </button>
          <button
            onClick={() => setActiveTab("direct")}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "direct"
                ? "bg-emerald-600 text-white"
                : "bg-white/5 text-ink-secondary hover:text-ink-primary"
            }`}
          >
            Direct Expenses ({events.filter((e) => e.is_direct_expense && e.event_type === "expense").length})
          </button>
          <button
            onClick={() => setActiveTab("overhead")}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "overhead"
                ? "bg-purple-600 text-white"
                : "bg-white/5 text-ink-secondary hover:text-ink-primary"
            }`}
          >
            Overhead Leakage ({events.filter((e) => e.is_overhead_leakage).length})
          </button>
          <button
            onClick={() => setActiveTab("charity")}
            className={`rounded px-3 py-1 text-xs font-medium transition-colors ${
              activeTab === "charity"
                ? "bg-red-600 text-white"
                : "bg-white/5 text-ink-secondary hover:text-ink-primary"
            }`}
          >
            Charity Quarantine ({events.filter((e) => e.quarantined_to_charity).length})
          </button>
        </div>

        <input
          type="text"
          placeholder="Filter description or category..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-56 rounded-md border border-white/10 bg-navy-950 px-2.5 py-1 text-xs text-ink-primary placeholder-ink-muted focus:border-gold-500 focus:outline-none"
        />
      </div>

      {/* Main Ledger Table */}
      <Card title="Income & Expense Ledger Items">
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 py-12 text-ink-secondary">
            <Spinner className="h-5 w-5" />
            <span className="text-sm">Loading ledger events...</span>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr className="border-b border-white/8 text-[11px] font-semibold tracking-wider text-ink-muted uppercase">
                  <th className="py-2.5 px-3">Date</th>
                  <th className="py-2.5 px-3">Type</th>
                  <th className="py-2.5 px-3">Category & Details</th>
                  <th className="py-2.5 px-3">Gross Amount</th>
                  <th className="py-2.5 px-3">Cost Classification</th>
                  <th className="py-2.5 px-3">Chargeable to Pool</th>
                  <th className="py-2.5 px-3">Bank Absorbed</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5 text-xs">
                {filteredEvents.length > 0 ? (
                  filteredEvents.map((item) => (
                    <tr
                      key={item.id}
                      className={`transition-colors ${
                        item.is_overhead_leakage
                          ? "bg-purple-950/20 hover:bg-purple-950/30"
                          : item.quarantined_to_charity
                            ? "bg-red-950/20 hover:bg-red-950/30"
                            : "hover:bg-white/2"
                      }`}
                    >
                      <td className="py-3 px-3 font-mono text-ink-secondary">
                        {item.event_date}
                      </td>

                      <td className="py-3 px-3">
                        <span
                          className={`rounded px-1.5 py-0.5 text-[10px] font-bold uppercase ${
                            item.event_type === "income"
                              ? "bg-emerald-500/20 text-emerald-400"
                              : "bg-gold-500/20 text-gold-400"
                          }`}
                        >
                          {item.event_type}
                        </span>
                      </td>

                      <td className="py-3 px-3 max-w-xs">
                        <div className="font-medium text-ink-primary">{item.category}</div>
                        <p className="text-[11px] text-ink-secondary truncate">
                          {item.description}
                        </p>
                        {item.shariah_note && (
                          <p className="text-[10px] text-gold-400/90 italic mt-0.5">
                            {item.shariah_note}
                          </p>
                        )}
                      </td>

                      <td className="py-3 px-3 font-mono font-medium text-ink-primary">
                        {formatPKR(item.amount)}
                      </td>

                      <td className="py-3 px-3">
                        {item.cost_classification === "direct_permissible" && (
                          <Badge variant="emerald">Direct Permissible</Badge>
                        )}
                        {item.cost_classification === "indirect_overhead" && (
                          <Badge variant="navy">Overhead (Bank Absorbed)</Badge>
                        )}
                        {item.cost_classification === "permissible_income" && (
                          <Badge variant="emerald">Permissible Return</Badge>
                        )}
                        {item.cost_classification === "non_permissible_income" && (
                          <Badge variant="gold">Charity Quarantine</Badge>
                        )}
                      </td>

                      <td className="py-3 px-3 font-mono">
                        {Number(item.pool_chargeable_amount) > 0 ? (
                          <span className="font-semibold text-emerald-400">
                            {formatPKR(item.pool_chargeable_amount)}
                          </span>
                        ) : (
                          <span className="text-ink-muted">₨ 0.00</span>
                        )}
                      </td>

                      <td className="py-3 px-3 font-mono">
                        {Number(item.bank_absorbed_amount) > 0 ? (
                          <span className="font-semibold text-purple-400">
                            {formatPKR(item.bank_absorbed_amount)}
                          </span>
                        ) : (
                          <span className="text-ink-muted">₨ 0.00</span>
                        )}
                      </td>

                      <td className="py-3 px-3">
                        <Badge variant={item.status === "posted" ? "emerald" : "neutral"}>
                          {item.status}
                        </Badge>
                      </td>

                      <td className="py-3 px-3 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          {item.event_type === "income" && !item.quarantined_to_charity && (
                            <button
                              onClick={() => handleQuarantine(item.id)}
                              className="rounded bg-red-500/20 px-2 py-1 text-[10px] font-semibold text-red-300 hover:bg-red-500/30"
                              title="Route non-permissible return to Charity"
                            >
                              Quarantine
                            </button>
                          )}

                          {item.event_type === "expense" && (
                            <button
                              onClick={() => handleToggleOverhead(item)}
                              className={`rounded px-2 py-1 text-[10px] font-semibold transition-colors ${
                                item.is_overhead_leakage
                                  ? "bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30"
                                  : "bg-purple-500/20 text-purple-300 hover:bg-purple-500/30"
                              }`}
                              title={
                                item.is_overhead_leakage
                                  ? "Reclassify as Direct Permissible"
                                  : "Flag as Overhead (Bank Absorbs)"
                              }
                            >
                              {item.is_overhead_leakage ? "Mark Direct" : "Mark Overhead"}
                            </button>
                          )}

                          {item.status === "pending" && (
                            <button
                              onClick={() => handlePostEvent(item.id)}
                              className="rounded bg-emerald-600 px-2 py-1 text-[10px] font-semibold text-white hover:bg-emerald-500"
                              title="Dual-Control Checker Sign-off"
                            >
                              Post
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={9} className="py-8 text-center text-ink-muted">
                      No income or expense events found matching criteria.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Modal for Recording New Event */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-xl border border-white/10 bg-navy-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/8 pb-3">
              <div>
                <h3 className="text-base font-semibold text-ink-primary">
                  Record Income / Expense Line Item
                </h3>
                <p className="text-xs text-ink-secondary">
                  Classify cost under SBP IBD 03/2012 Direct vs Indirect cost guidelines.
                </p>
              </div>
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="text-ink-muted hover:text-ink-primary"
              >
                ✕
              </button>
            </div>

            {modalError && (
              <div className="mt-3 rounded bg-red-500/10 p-2 text-xs text-red-400">
                {modalError}
              </div>
            )}

            <form onSubmit={handleCreateSubmit} className="mt-4 space-y-3.5 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary">Transaction Type</label>
                  <select
                    value={form.event_type}
                    onChange={(e) => {
                      const t = e.target.value as "income" | "expense"
                      setForm({
                        ...form,
                        event_type: t,
                        cost_classification:
                          t === "income" ? "permissible_income" : "direct_permissible",
                      })
                    }}
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                  >
                    <option value="expense">Expense (Operational Cost)</option>
                    <option value="income">Income (Realized Return)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-ink-secondary">Cost Classification</label>
                  <select
                    value={form.cost_classification}
                    onChange={(e) =>
                      setForm({
                        ...form,
                        cost_classification: e.target.value as CostClassification,
                      })
                    }
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                  >
                    {form.event_type === "expense" ? (
                      <>
                        <option value="direct_permissible">
                          Direct Permissible (Chargeable to Pool)
                        </option>
                        <option value="indirect_overhead">
                          Indirect Overhead (Bank P&L Absorbed)
                        </option>
                      </>
                    ) : (
                      <>
                        <option value="permissible_income">
                          Permissible Income (Distributable)
                        </option>
                        <option value="non_permissible_income">
                          Non-Permissible Income (Charity Quarantine)
                        </option>
                      </>
                    )}
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary">Category</label>
                  <input
                    type="text"
                    value={form.category}
                    onChange={(e) => setForm({ ...form, category: e.target.value })}
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                    placeholder="e.g. Asset Takaful, Custody, Rent"
                    required
                  />
                </div>

                <div>
                  <label className="block text-ink-secondary">Amount (PKR)</label>
                  <input
                    type="number"
                    step="0.01"
                    value={form.amount}
                    onChange={(e) => setForm({ ...form, amount: e.target.value })}
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                    placeholder="0.00"
                    required
                  />
                </div>
              </div>

              <div>
                <label className="block text-ink-secondary">Value Date</label>
                <input
                  type="date"
                  value={form.event_date}
                  onChange={(e) => setForm({ ...form, event_date: e.target.value })}
                  className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                  required
                />
              </div>

              <div>
                <label className="block text-ink-secondary">Description & Obligor</label>
                <textarea
                  rows={2}
                  value={form.description}
                  onChange={(e) => setForm({ ...form, description: e.target.value })}
                  className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                  placeholder="Provide transaction context, asset serial or vendor reference..."
                  required
                />
              </div>

              <div>
                <label className="block text-ink-secondary">
                  Shariah Justification / Attestation Note
                </label>
                <input
                  type="text"
                  value={form.shariah_note ?? ""}
                  onChange={(e) => setForm({ ...form, shariah_note: e.target.value })}
                  className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                  placeholder="e.g. Direct Takaful under Ijarah agreement clause 4.2"
                />
              </div>

              <div className="flex justify-end gap-2 border-t border-white/8 pt-3">
                <Button
                  type="button"
                  variant="secondary"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  variant="primary"
                  className="bg-emerald-600 hover:bg-emerald-500"
                  disabled={isSubmitting}
                >
                  {isSubmitting ? <Spinner className="h-4 w-4" /> : "Save Line Item"}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
