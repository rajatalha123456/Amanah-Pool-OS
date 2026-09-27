import { useEffect, useState, type FormEvent } from "react"
import { Card } from "../components/Card"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { fetchPools } from "../api/pools"
import { simulateAllocation } from "../api/allocationRuns"
import { extractErrorMessage } from "../api/errors"
import type { Pool, SimulateAllocationResult } from "../types"

interface ScenarioInputs {
  poolId: string
  valueDate: string
  grossIncome: string
  directExpenses: string
}

interface ScenarioFormProps {
  label: string
  inputs: ScenarioInputs
  onChange: (inputs: ScenarioInputs) => void
  pools: Pool[]
  isLoadingPools: boolean
}

function ScenarioForm({ label, inputs, onChange, pools, isLoadingPools }: ScenarioFormProps) {
  return (
    <Card title={label}>
      {isLoadingPools ? (
        <div className="flex items-center gap-2 text-sm text-ink-secondary">
          <Spinner className="h-4 w-4" />
          Loading pools...
        </div>
      ) : pools.length === 0 ? (
        <p className="text-sm text-gold-400">No pools available. Create a pool first.</p>
      ) : (
        <div className="grid grid-cols-1 gap-4">
          <div>
            <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
              Pool
            </label>
            <select
              value={inputs.poolId}
              onChange={(e) => onChange({ ...inputs, poolId: e.target.value })}
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
              value={inputs.valueDate}
              onChange={(e) => onChange({ ...inputs, valueDate: e.target.value })}
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
              value={inputs.grossIncome}
              onChange={(e) => onChange({ ...inputs, grossIncome: e.target.value })}
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
              value={inputs.directExpenses}
              onChange={(e) => onChange({ ...inputs, directExpenses: e.target.value })}
              placeholder="0.00"
              className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
            />
          </div>
        </div>
      )}
    </Card>
  )
}

function percentDifference(a: string, b: string): string {
  const numA = Number(a)
  const numB = Number(b)
  if (numA === 0) return numB === 0 ? "0.00%" : "—"
  const diff = ((numB - numA) / Math.abs(numA)) * 100
  const sign = diff > 0 ? "+" : ""
  return `${sign}${diff.toFixed(2)}%`
}

interface ComparisonRow {
  participantClass: string
  allocatedA: string
  allocatedB: string
  difference: string
}

export function ScenarioSimulator() {
  const [pools, setPools] = useState<Pool[]>([])
  const [isLoadingPools, setIsLoadingPools] = useState(true)

  const [scenarioA, setScenarioA] = useState<ScenarioInputs>({
    poolId: "",
    valueDate: "",
    grossIncome: "",
    directExpenses: "",
  })
  const [scenarioB, setScenarioB] = useState<ScenarioInputs>({
    poolId: "",
    valueDate: "",
    grossIncome: "",
    directExpenses: "",
  })

  const [resultA, setResultA] = useState<SimulateAllocationResult | null>(null)
  const [resultB, setResultB] = useState<SimulateAllocationResult | null>(null)
  const [compareError, setCompareError] = useState("")
  const [isComparing, setIsComparing] = useState(false)

  useEffect(() => {
    fetchPools()
      .then((data) => {
        setPools(data)
        if (data.length > 0) {
          setScenarioA((prev) => ({ ...prev, poolId: prev.poolId || data[0].id }))
          setScenarioB((prev) => ({ ...prev, poolId: prev.poolId || data[0].id }))
        }
      })
      .catch(() => setCompareError("Failed to load pools"))
      .finally(() => setIsLoadingPools(false))
  }, [])

  async function handleCompare(event: FormEvent) {
    event.preventDefault()
    setCompareError("")
    setResultA(null)
    setResultB(null)
    setIsComparing(true)

    try {
      const [a, b] = await Promise.all([
        simulateAllocation({
          pool: scenarioA.poolId,
          value_date: scenarioA.valueDate,
          gross_income: scenarioA.grossIncome,
          direct_expenses: scenarioA.directExpenses || "0",
        }),
        simulateAllocation({
          pool: scenarioB.poolId,
          value_date: scenarioB.valueDate,
          gross_income: scenarioB.grossIncome,
          direct_expenses: scenarioB.directExpenses || "0",
        }),
      ])
      setResultA(a)
      setResultB(b)
    } catch (err) {
      setCompareError(
        extractErrorMessage(
          err,
          "Unable to run comparison. Check that both scenarios have valid daily balances, weightage bands and a PSR.",
        ),
      )
    } finally {
      setIsComparing(false)
    }
  }

  const comparisonRows: ComparisonRow[] =
    resultA && resultB
      ? (() => {
          const byClassA = new Map(resultA.lines.map((line) => [line.participant_class, line]))
          const byClassB = new Map(resultB.lines.map((line) => [line.participant_class, line]))
          const classes = Array.from(new Set([...byClassA.keys(), ...byClassB.keys()]))
          return classes.map((participantClass) => {
            const lineA = byClassA.get(participantClass)
            const lineB = byClassB.get(participantClass)
            return {
              participantClass,
              allocatedA: lineA?.allocated_amount ?? "0",
              allocatedB: lineB?.allocated_amount ?? "0",
              difference: percentDifference(lineA?.allocated_amount ?? "0", lineB?.allocated_amount ?? "0"),
            }
          })
        })()
      : []

  const comparisonColumns: TableColumn<ComparisonRow>[] = [
    { header: "Participant Class", accessor: (row) => row.participantClass },
    { header: "Scenario A — Allocated", accessor: (row) => row.allocatedA },
    { header: "Scenario B — Allocated", accessor: (row) => row.allocatedB },
    { header: "Difference", accessor: (row) => row.difference },
  ]

  const summaryColumns: TableColumn<{ label: string; a: string; b: string; diff: string }>[] = [
    { header: "Metric", accessor: (row) => row.label },
    { header: "Scenario A", accessor: (row) => row.a },
    { header: "Scenario B", accessor: (row) => row.b },
    { header: "Difference", accessor: (row) => row.diff },
  ]

  const summaryRows =
    resultA && resultB
      ? [
          {
            label: "Distributable",
            a: resultA.distributable,
            b: resultB.distributable,
            diff: percentDifference(resultA.distributable, resultB.distributable),
          },
          {
            label: "Depositor Share",
            a: resultA.depositor_pool_share,
            b: resultB.depositor_pool_share,
            diff: percentDifference(resultA.depositor_pool_share, resultB.depositor_pool_share),
          },
          {
            label: "Mudarib Share",
            a: resultA.mudarib_share,
            b: resultB.mudarib_share,
            diff: percentDifference(resultA.mudarib_share, resultB.mudarib_share),
          },
        ]
      : []

  return (
    <div>
      <p className="mb-6 text-sm text-ink-secondary">
        Run two independent allocation simulations side by side to compare how a change in gross
        income, direct expenses, or pool selection shifts the distributable amount and per-class
        allocations. Neither scenario is saved — this is preview-only.
      </p>

      <form onSubmit={handleCompare}>
        <div className="mb-6 grid grid-cols-1 gap-4 lg:grid-cols-2">
          <ScenarioForm
            label="Scenario A"
            inputs={scenarioA}
            onChange={setScenarioA}
            pools={pools}
            isLoadingPools={isLoadingPools}
          />
          <ScenarioForm
            label="Scenario B"
            inputs={scenarioB}
            onChange={setScenarioB}
            pools={pools}
            isLoadingPools={isLoadingPools}
          />
        </div>

        <div className="mb-6">
          <Button type="submit" variant="primary" disabled={isComparing || pools.length === 0}>
            {isComparing ? <Spinner className="h-4 w-4" /> : "Compare"}
          </Button>
          {compareError && <p className="mt-3 text-sm text-red-400">{compareError}</p>}
        </div>
      </form>

      {resultA && resultB && (
        <>
          <Card title="Summary Comparison" className="mb-6">
            <Table columns={summaryColumns} data={summaryRows} keyField={(row) => row.label} />
          </Card>

          <Card title="Per-Participant-Class Comparison">
            <Table columns={comparisonColumns} data={comparisonRows} keyField={(row) => row.participantClass} />
          </Card>
        </>
      )}
    </div>
  )
}
