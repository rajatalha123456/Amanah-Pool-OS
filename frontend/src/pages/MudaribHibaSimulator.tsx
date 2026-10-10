import { useEffect, useState } from "react"
import { useParams, Link } from "react-router-dom"
import { PageHeader } from "../components/PageHeader"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Spinner } from "../components/Spinner"
import { Modal } from "../components/Modal"
import { fetchAllocationRuns } from "../api/allocationRuns"
import {
  simulateHiba,
  applyHiba,
  type HibaSimulationResponse,
} from "../api/hiba"
import { extractErrorMessage } from "../api/errors"
import type { AllocationRun } from "../types"

export function MudaribHibaSimulator() {
  const params = useParams<{ id?: string; runId?: string }>()
  const routeRunId = params.id || params.runId

  const [runs, setRuns] = useState<AllocationRun[]>([])
  const [selectedRunId, setSelectedRunId] = useState<string>(routeRunId || "")
  const [loadingRuns, setLoadingRuns] = useState(true)

  const [simLoading, setSimLoading] = useState(false)
  const [simData, setSimData] = useState<HibaSimulationResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  // Simulation controls
  const [targetKibor, setTargetKibor] = useState<number>(18.00)
  const [hibaAmount, setHibaAmount] = useState<number>(300000)
  const [copiedMemo, setCopiedMemo] = useState(false)

  // Apply Modal state
  const [isApplyModalOpen, setIsApplyModalOpen] = useState(false)
  const [justification, setJustification] = useState("ALCO Yield Optimization against KIBOR benchmark")
  const [applying, setApplying] = useState(false)
  const [applyResult, setApplyResult] = useState<string | null>(null)

  // 1. Fetch available runs
  useEffect(() => {
    setLoadingRuns(true)
    fetchAllocationRuns()
      .then((data) => {
        setRuns(data)
        if (!selectedRunId && data.length > 0) {
          // Default to the first signed, simulated, or pending run
          const defaultRun = data.find((r) => r.status === "signed" || r.status === "simulated") || data[0]
          setSelectedRunId(defaultRun.id)
        }
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setLoadingRuns(false))
  }, [])

  // 2. Run simulation when selectedRunId, targetKibor, or hibaAmount changes
  const runSimulation = (runId: string, kiborVal: number, hibaVal: number) => {
    if (!runId) return
    setSimLoading(true)
    setError(null)
    simulateHiba(runId, { target_kibor: kiborVal, hiba_amount: hibaVal })
      .then((res) => {
        setSimData(res)
      })
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setSimLoading(false))
  }

  useEffect(() => {
    if (selectedRunId) {
      runSimulation(selectedRunId, targetKibor, hibaAmount)
    }
  }, [selectedRunId])

  const handleKiborChange = (newKibor: number) => {
    setTargetKibor(newKibor)
    runSimulation(selectedRunId, newKibor, hibaAmount)
  }

  const handleHibaChange = (newHiba: number) => {
    setHibaAmount(newHiba)
    runSimulation(selectedRunId, targetKibor, newHiba)
  }

  const handlePresetConcession = (pct: number) => {
    if (!simData) return
    const maxFee = simData.metrics.contractual_mudarib_share
    const calculatedHiba = Math.round((maxFee * pct) / 100)
    handleHibaChange(calculatedHiba)
  }

  const handleMatchKibor = () => {
    if (!simData) return
    const optimalHiba = simData.metrics.optimal_hiba_needed_for_kibor
    if (optimalHiba > 0) {
      handleHibaChange(optimalHiba)
    } else {
      handleHibaChange(0)
    }
  }

  const handleApplyHibaSubmit = async () => {
    if (!selectedRunId || !simData) return
    setApplying(true)
    try {
      const res = await applyHiba(selectedRunId, {
        hiba_amount: hibaAmount,
        justification,
      })
      setApplyResult(res.message)
      setIsApplyModalOpen(false)
      // Refresh simulation
      runSimulation(selectedRunId, targetKibor, hibaAmount)
    } catch (err) {
      alert(`Failed to apply Hiba: ${extractErrorMessage(err)}`)
    } finally {
      setApplying(false)
    }
  }

  const copyMemoToClipboard = () => {
    if (!simData?.alco_memo) return
    navigator.clipboard.writeText(simData.alco_memo)
    setCopiedMemo(true)
    setTimeout(() => setCopiedMemo(false), 2500)
  }

  return (
    <div className="space-y-6">
      <PageHeader
        screenNumber="19"
        title="Mudarib Fee Optimization & Hiba Yield Simulator"
        subtitle="AAOIFI Shariah Standard No. 13 (Tanazul / Hiba) & SBP Market Yield Parity Engine"
        actions={
          <div className="flex items-center gap-2">
            {selectedRunId && (
              <Link to={`/allocation-runs/${selectedRunId}`}>
                <Button variant="secondary" className="text-xs">
                  View Run Details
                </Button>
              </Link>
            )}
            <Button
              variant="primary"
              className="text-xs"
              onClick={() => setIsApplyModalOpen(true)}
              disabled={!simData || simData.status === "reversed"}
            >
              ✍️ Apply Hiba to Allocation Run
            </Button>
          </div>
        }
      />

      {applyResult && (
        <div className="p-4 rounded-lg border border-emerald-500/30 bg-emerald-950/20 text-xs text-emerald-300 flex items-center justify-between">
          <span className="font-semibold">✓ {applyResult}</span>
          <button
            type="button"
            onClick={() => setApplyResult(null)}
            className="text-ink-secondary hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-lg border border-red-500/30 bg-red-950/20 text-xs text-red-300 flex items-center justify-between">
          <span className="font-semibold">⚠️ {error}</span>
          <button
            type="button"
            onClick={() => setError(null)}
            className="text-ink-secondary hover:text-white"
          >
            ✕
          </button>
        </div>
      )}

      {/* Target Run Selector & Baseline Context */}
      <Card title="Allocation Run Context & Target Benchmark">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-semibold text-ink-secondary mb-1.5 uppercase">
              Target Allocation Run
            </label>
            {loadingRuns ? (
              <Spinner className="h-5 w-5" />
            ) : (
              <select
                value={selectedRunId}
                onChange={(e) => setSelectedRunId(e.target.value)}
                className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-xs text-ink-primary focus:border-emerald-500 focus:outline-none"
              >
                {runs.map((r) => (
                  <option key={r.id} value={r.id}>
                    Run #{r.id.slice(0, 8)} • {r.value_date} • {r.status.toUpperCase()}
                  </option>
                ))}
              </select>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-ink-secondary mb-1.5 uppercase">
              Market Benchmark (1M KIBOR Target)
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="0.05"
                min="0"
                max="30"
                value={targetKibor}
                onChange={(e) => handleKiborChange(Number(e.target.value))}
                className="w-32 rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-xs text-ink-primary font-mono focus:border-emerald-500 focus:outline-none"
              />
              <span className="text-xs text-ink-secondary">% p.a.</span>
            </div>
            <div className="mt-2 flex gap-1.5">
              {[17.0, 17.5, 18.0, 18.5, 19.0].map((rate) => (
                <button
                  key={rate}
                  type="button"
                  onClick={() => handleKiborChange(rate)}
                  className={`px-2 py-0.5 rounded text-[11px] font-mono border ${
                    targetKibor === rate
                      ? "bg-emerald-600/30 border-emerald-500 text-emerald-300"
                      : "bg-surface border-ink/10 text-ink-secondary hover:text-ink"
                  }`}
                >
                  {rate.toFixed(1)}%
                </button>
              ))}
            </div>
          </div>

          <div className="p-3 rounded-lg bg-surface-subtle border border-ink/10 flex flex-col justify-between">
            <span className="text-[11px] text-ink-secondary uppercase tracking-wider font-semibold">
              Benchmark Parity Target
            </span>
            <div className="flex items-baseline gap-2">
              <span className="text-xl font-bold font-mono text-emerald-400">
                {targetKibor.toFixed(2)}%
              </span>
              <span className="text-xs text-ink-muted">Conventional 1M KIBOR</span>
            </div>
            <p className="text-[11px] text-ink-muted">
              Prevents retail & institutional depositor flight to conventional banks.
            </p>
          </div>
        </div>
      </Card>

      {/* Interactive Hiba Sliders & Financial Waterfall */}
      {simLoading ? (
        <Card>
          <div className="flex items-center justify-center py-12 text-ink-secondary gap-2">
            <Spinner className="h-5 w-5" />
            <span className="text-sm">Calculating Hiba yield matrix & Shariah standard checks...</span>
          </div>
        </Card>
      ) : simData ? (
        <>
          {/* Hiba Controls Card */}
          <Card title="⚡ Interactive Voluntary Hiba Concession Controls">
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center">
                <div>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-semibold text-ink-secondary uppercase">
                      Hiba Foregone by Bank (PKR)
                    </span>
                    <span className="text-xs font-mono font-bold text-gold-400">
                      PKR {hibaAmount.toLocaleString()} (
                      {simData.metrics.contractual_mudarib_share > 0
                        ? (
                            (hibaAmount / simData.metrics.contractual_mudarib_share) *
                            100
                          ).toFixed(1)
                        : 0}
                      % of fee)
                    </span>
                  </div>
                  <input
                    type="range"
                    min="0"
                    max={simData.metrics.contractual_mudarib_share}
                    step="10000"
                    value={hibaAmount}
                    onChange={(e) => handleHibaChange(Number(e.target.value))}
                    className="w-full accent-emerald-500 cursor-pointer"
                  />
                  <div className="flex justify-between text-[11px] text-ink-muted font-mono mt-1">
                    <span>PKR 0 (0%)</span>
                    <span>
                      Max: PKR {simData.metrics.contractual_mudarib_share.toLocaleString()} (100%)
                    </span>
                  </div>
                </div>

                {/* Quick Preset Buttons */}
                <div className="space-y-2">
                  <span className="text-xs font-semibold text-ink-secondary uppercase block">
                    Optimization Presets:
                  </span>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="secondary"
                      className="text-xs"
                      onClick={() => handlePresetConcession(0)}
                    >
                      Reset (0% Hiba)
                    </Button>
                    <Button
                      variant="secondary"
                      className="text-xs"
                      onClick={() => handlePresetConcession(15)}
                    >
                      15% Concession
                    </Button>
                    <Button
                      variant="secondary"
                      className="text-xs"
                      onClick={() => handlePresetConcession(25)}
                    >
                      25% Concession
                    </Button>
                    <Button
                      variant="secondary"
                      className="text-xs"
                      onClick={() => handlePresetConcession(40)}
                    >
                      40% Concession
                    </Button>
                    <Button
                      variant="primary"
                      className="text-xs"
                      onClick={handleMatchKibor}
                    >
                      🎯 Match KIBOR Target
                    </Button>
                  </div>
                </div>
              </div>

              {/* Waterfall Summary Cards */}
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3 pt-2">
                <div className="p-3 rounded-lg border border-ink/10 bg-surface">
                  <span className="text-[10px] text-ink-secondary uppercase">Gross Distributable</span>
                  <p className="text-sm font-bold font-mono text-ink mt-0.5">
                    PKR {simData.metrics.distributable_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </p>
                  <span className="text-[10px] text-ink-muted">Pool profit</span>
                </div>

                <div className="p-3 rounded-lg border border-ink/10 bg-surface">
                  <span className="text-[10px] text-ink-secondary uppercase">Contractual Mudarib</span>
                  <p className="text-sm font-bold font-mono text-ink mt-0.5">
                    PKR {simData.metrics.contractual_mudarib_share.toLocaleString()} ({simData.metrics.contractual_mudarib_pct}%)
                  </p>
                  <span className="text-[10px] text-ink-muted">Pre-notified PSR</span>
                </div>

                <div className="p-3 rounded-lg border border-gold-500/30 bg-gold-950/20">
                  <span className="text-[10px] text-gold-300 uppercase">Hiba Foregone</span>
                  <p className="text-sm font-bold font-mono text-gold-400 mt-0.5">
                    -PKR {simData.metrics.simulated_hiba_amount.toLocaleString()}
                  </p>
                  <span className="text-[10px] text-gold-400/80">Voluntary concession</span>
                </div>

                <div className="p-3 rounded-lg border border-ink/10 bg-surface">
                  <span className="text-[10px] text-ink-secondary uppercase">Net Mudarib Retained</span>
                  <p className="text-sm font-bold font-mono text-ink mt-0.5">
                    PKR {simData.metrics.effective_mudarib_share.toLocaleString()} ({simData.metrics.effective_mudarib_pct}%)
                  </p>
                  <span className="text-[10px] text-ink-muted">Bank net fee</span>
                </div>

                <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-950/20">
                  <span className="text-[10px] text-emerald-300 uppercase">Net Yield Uplift</span>
                  <p className="text-sm font-bold font-mono text-emerald-400 mt-0.5">
                    +{simData.metrics.net_yield_uplift_bps} bps
                  </p>
                  <span className="text-[10px] text-emerald-400/80">
                    {simData.metrics.avg_baseline_yield}% → {simData.metrics.avg_revised_yield}%
                  </span>
                </div>
              </div>
            </div>
          </Card>

          {/* Tier-by-Tier Yield Impact Table */}
          <Card title="Depositor Tier Annualized Yield Comparison">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-surface-subtle text-ink-secondary font-medium">
                  <tr>
                    <th className="py-2.5 px-3">Participant Tier</th>
                    <th className="py-2.5 px-3 text-right">Daily Funds (PKR)</th>
                    <th className="py-2.5 px-3 text-center">Weightage</th>
                    <th className="py-2.5 px-3 text-right">Baseline Share</th>
                    <th className="py-2.5 px-3 text-right">Base Yield</th>
                    <th className="py-2.5 px-3 text-right">Hiba Share</th>
                    <th className="py-2.5 px-3 text-right">Revised Share</th>
                    <th className="py-2.5 px-3 text-right font-bold text-emerald-400">Revised Yield</th>
                    <th className="py-2.5 px-3 text-right">Uplift</th>
                    <th className="py-2.5 px-3 text-center">vs KIBOR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-ink/5">
                  {simData.tiers.map((t, idx) => (
                    <tr key={idx} className="hover:bg-surface-subtle/50">
                      <td className="py-2.5 px-3 font-semibold text-ink">{t.participant_class}</td>
                      <td className="py-2.5 px-3 text-right font-mono">
                        {t.daily_funds.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-2.5 px-3 text-center font-mono">{t.weightage.toFixed(2)}</td>
                      <td className="py-2.5 px-3 text-right font-mono text-ink-secondary">
                        {t.baseline_allocated_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-ink-muted">
                        {t.baseline_annualized_yield.toFixed(2)}%
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-gold-400">
                        +{t.incremental_hiba_share.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-medium text-ink">
                        {t.revised_allocated_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono font-bold text-emerald-400 text-sm">
                        {t.revised_annualized_yield.toFixed(2)}%
                      </td>
                      <td className="py-2.5 px-3 text-right font-mono text-emerald-300">
                        +{t.yield_delta_bps} bps
                      </td>
                      <td className="py-2.5 px-3 text-center">
                        <Badge
                          variant={t.gap_vs_benchmark >= 0 ? "emerald" : "gold"}
                        >
                          {t.gap_vs_benchmark >= 0 ? `+${t.gap_vs_benchmark.toFixed(2)}%` : `${t.gap_vs_benchmark.toFixed(2)}%`}
                        </Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Shariah Standards Checklist & ALCO Memo */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* AAOIFI & SBP Compliance Gate */}
            <Card title="AAOIFI FAS-30 & SBP IBD Circular 03/2012 Governance Gate">
              <div className="space-y-3">
                {simData.shariah_validation.checklist.map((item) => (
                  <div
                    key={item.id}
                    className="p-3 rounded-lg border border-ink/10 bg-surface-subtle space-y-1"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-ink">{item.rule}</span>
                      <Badge variant={item.passed ? "emerald" : "neutral"}>
                        {item.passed ? "PASSED" : "FAILED"}
                      </Badge>
                    </div>
                    <p className="text-[11px] text-ink-secondary">{item.details}</p>
                    <div className="text-[10px] text-ink-muted font-mono">{item.standard}</div>
                  </div>
                ))}
              </div>
            </Card>

            {/* ALCO Resolution Memorandum */}
            <Card
              title="Official ALCO & Shariah Board Resolution Memorandum"
              actions={
                <Button variant="secondary" className="text-xs" onClick={copyMemoToClipboard}>
                  {copiedMemo ? "✓ Copied" : "📋 Copy Memorandum"}
                </Button>
              }
            >
              <pre className="font-mono text-[11px] text-ink-secondary bg-surface-subtle p-3 rounded-lg whitespace-pre-wrap max-h-72 overflow-y-auto leading-relaxed border border-ink/10">
                {simData.alco_memo}
              </pre>
            </Card>
          </div>
        </>
      ) : null}

      {/* Apply Hiba Modal */}
      {isApplyModalOpen && (
        <Modal
          title="Confirm Hiba Concession Application"
          onClose={() => setIsApplyModalOpen(false)}
        >
          <div className="space-y-4 text-xs">
            <p className="text-ink-secondary">
              You are applying a voluntary Mudarib profit share reduction (Hiba) of{" "}
              <strong className="text-gold-400">PKR {hibaAmount.toLocaleString()}</strong> to Run #
              {selectedRunId.slice(0, 8)}. This will permanently re-apportion profits to depositors
              and recalculate all line allocations.
            </p>

            <div className="p-3 rounded-lg border border-emerald-500/30 bg-emerald-950/20 text-emerald-300">
              <p className="font-semibold">Shariah Guarantee:</p>
              <p className="mt-1 text-[11px]">
                Under AAOIFI Standard No. 13, this concession is determined ex-post and is irrevocable.
              </p>
            </div>

            <div>
              <label className="block font-semibold text-ink-secondary mb-1 uppercase">
                ALCO Justification / Audit Note *
              </label>
              <textarea
                rows={3}
                value={justification}
                onChange={(e) => setJustification(e.target.value)}
                className="w-full rounded-md border border-white/10 bg-navy-800 p-2.5 text-ink-primary focus:border-emerald-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-2 pt-2 border-t border-ink/10">
              <Button
                variant="secondary"
                onClick={() => setIsApplyModalOpen(false)}
                disabled={applying}
              >
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleApplyHibaSubmit}
                disabled={applying}
              >
                {applying ? "Applying Concession..." : "Confirm & Commit Hiba"}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
