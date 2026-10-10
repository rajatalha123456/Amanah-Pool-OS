import { useEffect, useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { Table, type TableColumn } from "../components/Table"
import { fetchPools } from "../api/pools"
import { createAllocationRun, fetchAllocationRuns, simulateAllocation } from "../api/allocationRuns"
import { fetchImportHistory } from "../api/balances"
import { extractErrorMessage } from "../api/errors"
import { ScenarioSimulator } from "./ScenarioSimulator"
import { ProfitWaterfallChart } from "../components/charts/ProfitWaterfallChart"
import { WeightageCurveChart } from "../components/charts/WeightageCurveChart"
import type { AllocationLine, AllocationRun, BadgeVariant, Pool, SimulateAllocationResult } from "../types"

type AllocationEngineTab = "simulator" | "scenarios"

const TABS: { key: AllocationEngineTab; label: string }[] = [
  { key: "simulator", label: "Allocation Simulator" },
  { key: "scenarios", label: "Scenario Comparison" },
]

export function AllocationSimulator() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<AllocationEngineTab>("simulator")

  const [pools, setPools] = useState<Pool[]>([])
  const [isLoadingPools, setIsLoadingPools] = useState(true)
  const [selectedPoolId, setSelectedPoolId] = useState("")

  const [valueDate, setValueDate] = useState("")
  const [grossIncome, setGrossIncome] = useState("5000000.00")
  const [directExpenses, setDirectExpenses] = useState("100000.00")

  const [simulateError, setSimulateError] = useState("")
  const [isSimulating, setIsSimulating] = useState(false)
  const [result, setResult] = useState<SimulateAllocationResult | null>(null)

  const [saveError, setSaveError] = useState("")
  const [isSaving, setIsSaving] = useState(false)

  const [recentRuns, setRecentRuns] = useState<AllocationRun[]>([])
  const [isLoadingRuns, setIsLoadingRuns] = useState(false)

  useEffect(() => {
    fetchPools()
      .then((data) => {
        setPools(data)
        if (data.length > 0) {
          const generalPool = data.find(
            (p) =>
              p.name.toLowerCase().includes("general") ||
              p.code.toLowerCase().includes("gen") ||
              p.product_detail?.operating_model === "bank_pool" ||
              p.product_detail?.operating_model === "investment_pool",
          ) || data[0]
          setSelectedPoolId(generalPool.id)
        }
      })
      .catch(() => setSimulateError("Failed to load pools"))
      .finally(() => setIsLoadingPools(false))
  }, [])

  useEffect(() => {
    if (!selectedPoolId) return
    setIsLoadingRuns(true)
    fetchAllocationRuns(selectedPoolId)
      .then((data) => setRecentRuns(data))
      .catch(() => setRecentRuns([]))
      .finally(() => setIsLoadingRuns(false))

    // Pre-fill value date with the latest imported balance date if available
    fetchImportHistory(selectedPoolId)
      .then((batches) => {
        if (batches.length > 0) {
          const sorted = [...batches].sort(
            (a, b) => new Date(b.value_date).getTime() - new Date(a.value_date).getTime(),
          )
          setValueDate(sorted[0].value_date)
        } else if (!valueDate) {
          setValueDate("2026-09-28")
        }
      })
      .catch(() => {
        if (!valueDate) setValueDate("2026-09-28")
      })
  }, [selectedPoolId])

  function buildInput() {
    return {
      pool: selectedPoolId,
      value_date: valueDate,
      gross_income: grossIncome,
      direct_expenses: directExpenses || "0",
    }
  }

  function handleFillDefaults() {
    const generalPool = pools.find(
      (p) =>
        p.name.toLowerCase().includes("general") ||
        p.code.toLowerCase().includes("gen"),
    )
    if (generalPool) {
      setSelectedPoolId(generalPool.id)
    }
    setGrossIncome("5000000.00")
    setDirectExpenses("100000.00")
    setValueDate("2026-09-28")
    setSimulateError("")
  }

  async function handleSimulate(event: FormEvent) {
    event.preventDefault()
    setSimulateError("")
    setSaveError("")
    setResult(null)
    setIsSimulating(true)

    try {
      const simulationResult = await simulateAllocation(buildInput())
      setResult(simulationResult)
    } catch (err) {
      setSimulateError(
        extractErrorMessage(
          err,
          "Unable to run simulation. Ensure that daily balances, weightage bands, and an approved PSR exist for this pool and date.",
        ),
      )
    } finally {
      setIsSimulating(false)
    }
  }

  async function handleSaveAsRun() {
    setSaveError("")
    setIsSaving(true)

    try {
      const run = await createAllocationRun(buildInput())
      navigate("/allocation-runs/" + run.id)
    } catch (err) {
      setSaveError(extractErrorMessage(err, "Unable to save allocation run."))
    } finally {
      setIsSaving(false)
    }
  }

  const lineColumns: TableColumn<AllocationLine>[] = [
    {
      header: "Participant Class",
      accessor: (line) => <span className="font-medium text-ink-primary">{line.participant_class}</span>,
    },
    {
      header: "Daily Funds (PKR)",
      accessor: (line) => Number(line.daily_funds).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      header: "Weightage",
      accessor: (line) => (
        <span className="font-mono text-emerald-400">
          {Number(line.weightage).toFixed(2)}x
        </span>
      ),
    },
    {
      header: "Weighted Funds (PKR)",
      accessor: (line) => Number(line.weighted_funds).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      header: "Allocated Profit (PKR)",
      accessor: (line) => (
        <span className="font-semibold text-emerald-400">
          {Number(line.allocated_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </span>
      ),
    },
  ]

  const STATUS_BADGE: Record<string, BadgeVariant> = {
    simulated: "neutral",
    pending_approval: "gold",
    shariah_review: "gold",
    signed: "emerald",
    rejected: "navy",
  }

  const runColumns: TableColumn<AllocationRun>[] = [
    {
      header: "Value Date",
      accessor: (run) => <span className="font-semibold text-ink-primary">{run.value_date}</span>,
    },
    {
      header: "Gross Income (PKR)",
      accessor: (run) => Number(run.gross_income).toLocaleString(undefined, { minimumFractionDigits: 2 }),
    },
    {
      header: "Distributable (PKR)",
      accessor: (run) => (
        <span className="text-emerald-400 font-semibold">
          {Number(run.distributable_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
        </span>
      ),
    },
    {
      header: "Status",
      accessor: (run) => (
        <Badge variant={STATUS_BADGE[run.status] ?? "neutral"}>{run.status.toUpperCase()}</Badge>
      ),
    },
    { header: "Created At", accessor: (run) => new Date(run.created_at).toLocaleDateString() },
  ]

  return (
    <div className="space-y-6">
      <PageHeader
        screenNumber="12"
        title="Allocation Simulator"
        subtitle="What-if analysis and profit-sharing model verification before cycle commitment"
        actions={
          <Button
            type="button"
            variant="secondary"
            className="flex items-center gap-2 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10 text-xs"
            onClick={() => navigate("/mudarib-fee-optimization")}
          >
            <span>⚡</span>
            <span>Mudarib Fee & Hiba Optimizer (Screen 19)</span>
          </Button>
        }
      />

      <div className="flex gap-4 border-b border-white/8 text-sm">
        {TABS.map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`px-1 pb-2 font-medium transition-colors ${
              activeTab === tab.key
                ? "border-b-2 border-emerald-500 text-ink-primary font-semibold"
                : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {activeTab === "scenarios" && <ScenarioSimulator />}

      {activeTab === "simulator" && (
        <>
          <Card
            title="Simulation Parameters"
            actions={
              <Button type="button" variant="secondary" className="text-xs" onClick={handleFillDefaults}>
                + Quick Fill Standard Values
              </Button>
            }
          >
            {isLoadingPools ? (
              <div className="flex items-center gap-2 py-4 text-sm text-ink-secondary">
                <Spinner className="h-4 w-4" />
                Loading pools...
              </div>
            ) : pools.length === 0 ? (
              <p className="text-sm text-gold-400">No pools available. Create a pool first.</p>
            ) : (
              <form onSubmit={handleSimulate} className="grid grid-cols-1 gap-4 sm:grid-cols-4 sm:items-end">
                <div>
                  <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                    Target Pool *
                  </label>
                  <select
                    value={selectedPoolId}
                    onChange={(e) => setSelectedPoolId(e.target.value)}
                    className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                  >
                    {pools.map((pool) => (
                      <option key={pool.id} value={pool.id}>
                        {pool.code} — {pool.name}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                    Value Date *
                  </label>
                  <input
                    type="date"
                    value={valueDate}
                    onChange={(e) => setValueDate(e.target.value)}
                    required
                    className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                    Gross Pool Income (PKR) *
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={grossIncome}
                    onChange={(e) => setGrossIncome(e.target.value)}
                    required
                    className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div>
                  <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                    Direct Expenses (PKR)
                  </label>
                  <input
                    type="number"
                    step="0.01"
                    value={directExpenses}
                    onChange={(e) => setDirectExpenses(e.target.value)}
                    placeholder="0.00"
                    className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
                  />
                </div>

                <div className="sm:col-span-4 pt-2">
                  <Button type="submit" variant="primary" disabled={isSimulating}>
                    {isSimulating ? <Spinner className="h-4 w-4" /> : "Run Profit Allocation Simulation"}
                  </Button>
                </div>
              </form>
            )}

            {simulateError && (
              <div className="mt-4 rounded border border-red-500/30 bg-red-950/20 p-3 text-sm text-red-400">
                {simulateError}
              </div>
            )}
          </Card>

          {result && (
            <div className="space-y-6">
              <div className="flex items-center justify-between">
                <span className="rounded-full bg-emerald-500/10 border border-emerald-500/30 px-3 py-1 text-xs font-medium text-emerald-400">
                  ✓ Simulation Engine Complete — Preview only (Uncommitted)
                </span>
                <Button variant="primary" onClick={handleSaveAsRun} disabled={isSaving}>
                  {isSaving ? <Spinner className="h-4 w-4" /> : "Commit as Official Allocation Run →"}
                </Button>
              </div>

              {saveError && (
                <div className="rounded border border-red-500/30 bg-red-950/20 p-3 text-sm text-red-400">
                  {saveError}
                </div>
              )}

              {result.is_loss && (
                <div className="rounded-lg border border-amber-500/40 bg-amber-950/20 p-4 text-amber-300">
                  <div className="flex items-center gap-2 font-semibold text-sm">
                    <span>⚠️</span> Shariah Capital Loss Waterfall Active (BRD Sec 2 & 7)
                  </div>
                  <p className="mt-1 text-xs text-amber-200/80">
                    Net pool income is negative (expenses exceed income). Under Islamic Mudarabah & Musharakah principles, Mudarib receives PKR 0.00 profit share. 100% of verified capital loss is distributed pro-rata to capital providers according to daily funds.
                  </p>
                </div>
              )}

              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
                <StatCard
                  label={result.is_loss ? "Net Capital Loss" : "Net Distributable Profit"}
                  value={`PKR ${Number(result.distributable).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
                  deltaTone={result.is_loss ? "negative" : "positive"}
                />
                <StatCard
                  label="Total Weighted Funds"
                  value={`PKR ${Number(result.total_weighted_funds).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
                  deltaTone="neutral"
                />
                <StatCard
                  label={result.is_loss ? "Depositors Loss Share" : "Depositor Pool Share"}
                  value={`PKR ${Number(result.depositor_pool_share).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
                  deltaTone={result.is_loss ? "negative" : "positive"}
                />
                <StatCard
                  label="Mudarib Share"
                  value={`PKR ${Number(result.mudarib_share).toLocaleString(undefined, { minimumFractionDigits: 2 })}`}
                  deltaTone="neutral"
                />
              </div>

              {(Number(result.per_amount) > 0 || Number(result.irr_amount) > 0) && (
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                  <div className="rounded-lg border border-emerald-500/20 bg-navy-900/60 p-3 flex justify-between items-center text-xs">
                    <span className="text-ink-secondary">PER Appropriation (Profit Equalization Reserve):</span>
                    <span className="font-mono text-emerald-400 font-semibold">
                      PKR {Number(result.per_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                  <div className="rounded-lg border border-emerald-500/20 bg-navy-900/60 p-3 flex justify-between items-center text-xs">
                    <span className="text-ink-secondary">IRR Appropriation (Investment Risk Reserve):</span>
                    <span className="font-mono text-emerald-400 font-semibold">
                      PKR {Number(result.irr_amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </span>
                  </div>
                </div>
              )}

              {/* Shariah Waterfall Breakdown */}
              <ProfitWaterfallChart
                grossIncome={Number(grossIncome) || Number(result.distributable) + Number(directExpenses || 0)}
                directExpenses={Number(directExpenses) || 0}
                distributable={Number(result.distributable)}
                mudaribShare={Number(result.mudarib_share)}
                depositorShare={Number(result.depositor_pool_share)}
                mudaribRatio={
                  Number(result.distributable) > 0
                    ? Math.round((Number(result.mudarib_share) / Number(result.distributable)) * 100)
                    : 20
                }
              />

              {/* Tiered Weightage Multiplier Visualization */}
              <WeightageCurveChart
                data={result.lines.map((l) => ({
                  tierName: l.participant_class,
                  weightage: Number(l.weightage),
                  funds: Number(l.daily_funds),
                  allocatedProfit: Number(l.allocated_amount),
                }))}
              />

              <Card title="Simulated Distribution by Participant Tier">
                <Table columns={lineColumns} data={result.lines} keyField={(line) => line.participant_class} />
              </Card>
            </div>
          )}

          <Card title="Historical Allocation Runs">
            {isLoadingRuns ? (
              <div className="flex items-center gap-2 py-4 text-sm text-ink-secondary">
                <Spinner className="h-4 w-4" />
                Loading allocation runs...
              </div>
            ) : recentRuns.length === 0 ? (
              <p className="text-sm text-ink-secondary py-4">No allocation runs for this pool yet.</p>
            ) : (
              <Table
                columns={runColumns}
                data={recentRuns}
                keyField={(run) => run.id}
                onRowClick={(run) => navigate(`/allocation-runs/${run.id}`)}
              />
            )}
          </Card>
        </>
      )}
    </div>
  )
}
