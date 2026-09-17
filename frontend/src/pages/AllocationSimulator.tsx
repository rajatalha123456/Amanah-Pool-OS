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
import { extractErrorMessage } from "../api/errors"
import type { AllocationLine, AllocationRun, BadgeVariant, Pool, SimulateAllocationResult } from "../types"

export function AllocationSimulator() {
  const navigate = useNavigate()

  const [pools, setPools] = useState<Pool[]>([])
  const [isLoadingPools, setIsLoadingPools] = useState(true)
  const [selectedPoolId, setSelectedPoolId] = useState("")

  const [valueDate, setValueDate] = useState("")
  const [grossIncome, setGrossIncome] = useState("")
  const [directExpenses, setDirectExpenses] = useState("")

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
          setSelectedPoolId(data[0].id)
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
  }, [selectedPoolId])

  function buildInput() {
    return {
      pool: selectedPoolId,
      value_date: valueDate,
      gross_income: grossIncome,
      direct_expenses: directExpenses || "0",
    }
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
          "Unable to run simulation. Check that daily balances, weightage bands and a PSR exist for this pool and date.",
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
    { header: "Participant Class", accessor: (line) => line.participant_class },
    { header: "Daily Funds", accessor: (line) => line.daily_funds },
    { header: "Weightage", accessor: (line) => line.weightage },
    { header: "Weighted Funds", accessor: (line) => line.weighted_funds },
    { header: "Allocated Amount", accessor: (line) => line.allocated_amount },
  ]

  const STATUS_BADGE: Record<string, BadgeVariant> = {
    simulated: "neutral",
    pending_approval: "gold",
    signed: "emerald",
    rejected: "navy",
  }

  const runColumns: TableColumn<AllocationRun>[] = [
    { header: "Value Date", accessor: (run) => run.value_date },
    { header: "Gross Income", accessor: (run) => run.gross_income },
    {
      header: "Status",
      accessor: (run) => (
        <Badge variant={STATUS_BADGE[run.status] ?? "neutral"}>{run.status}</Badge>
      ),
    },
    { header: "Created At", accessor: (run) => run.created_at },
  ]

  return (
    <div>
      <PageHeader title="Allocation Simulator" subtitle="What-if analysis before changing economics" />

      <Card title="Run Parameters" className="mb-6">
        {isLoadingPools ? (
          <div className="flex items-center gap-2 text-sm text-ink-secondary">
            <Spinner className="h-4 w-4" />
            Loading pools...
          </div>
        ) : pools.length === 0 ? (
          <p className="text-sm text-gold-400">No pools available. Create a pool first.</p>
        ) : (
          <form onSubmit={handleSimulate} className="grid grid-cols-1 gap-4 sm:grid-cols-4 sm:items-end">
            <div>
              <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                Pool
              </label>
              <select
                value={selectedPoolId}
                onChange={(e) => setSelectedPoolId(e.target.value)}
                className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
              >
                {pools.map((pool) => (
                  <option key={pool.id} value={pool.id}>
                    {pool.name} ({pool.code})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                Value Date
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
                Gross Income
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
                Direct Expenses
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

            <div className="sm:col-span-4">
              <Button type="submit" variant="primary" disabled={isSimulating}>
                {isSimulating ? <Spinner className="h-4 w-4" /> : "Simulate"}
              </Button>
            </div>
          </form>
        )}

        {simulateError && <p className="mt-4 text-sm text-red-400">{simulateError}</p>}
      </Card>

      {result && (
        <>
          <div className="mb-4 flex items-center gap-2">
            <span className="rounded-full bg-white/8 px-3 py-1 text-xs font-medium text-ink-secondary">
              Preview only — not saved
            </span>
          </div>

          <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Distributable" value={result.distributable} deltaTone="neutral" />
            <StatCard label="Total Weighted Funds" value={result.total_weighted_funds} deltaTone="neutral" />
            <StatCard label="Depositor Share" value={result.depositor_pool_share} deltaTone="neutral" />
            <StatCard label="Mudarib Share" value={result.mudarib_share} deltaTone="neutral" />
          </div>

          <Card title="Allocation by Participant Class" className="mb-6">
            <Table columns={lineColumns} data={result.lines} keyField={(line) => line.participant_class} />
          </Card>

          <div className="mb-6">
            <Button variant="primary" onClick={handleSaveAsRun} disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Save as Allocation Run"}
            </Button>
            {saveError && <p className="mt-3 text-sm text-red-400">{saveError}</p>}
          </div>
        </>
      )}

      <Card title="Recent Runs">
        {isLoadingRuns ? (
          <div className="flex items-center gap-2 text-sm text-ink-secondary">
            <Spinner className="h-4 w-4" />
            Loading runs...
          </div>
        ) : recentRuns.length === 0 ? (
          <p className="text-sm text-ink-secondary">No allocation runs for this pool yet.</p>
        ) : (
          <Table
            columns={runColumns}
            data={recentRuns}
            keyField={(run) => run.id}
            onRowClick={(run) => navigate(`/allocation-runs/${run.id}`)}
          />
        )}
      </Card>
    </div>
  )
}
