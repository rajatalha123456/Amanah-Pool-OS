import { useEffect, useState, useMemo } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { Table, type TableColumn } from "../components/Table"
import { DonutChart, type DonutSlice } from "../components/charts/DonutChart"
import { RiskGaugeChart, type RiskLimitGauge } from "../components/charts/RiskGaugeChart"
import { fetchExceptions } from "../api/governance"
import { fetchPools } from "../api/pools"
import { fetchReservePolicies } from "../api/reservePolicies"
import {
  fetchConcentrationRisk,
  submitRemediationPlan,
  runConcentrationStressTest,
  type ConcentrationRiskAnalysis,
  type ObligorRiskItem,
  type SectorRiskItem,
  type StressTestResult,
  type RemediationSubmissionResult,
} from "../api/concentrationRisk"
import { extractErrorMessage } from "../api/errors"
import type { Pool, ReservePolicy } from "../types"

type RiskTab = "obligors" | "sectors" | "prudential" | "stress-test" | "exceptions"

interface SeverityCounts {
  low: number
  medium: number
  high: number
  critical: number
}

export function RiskLimitDashboard() {
  const [activeTab, setActiveTab] = useState<RiskTab>("obligors")
  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState<string>("")
  const [isLoading, setIsLoading] = useState(true)
  const [errorMsg, setErrorMsg] = useState("")

  // Concentration Data
  const [concentrationData, setConcentrationData] = useState<ConcentrationRiskAnalysis | null>(null)
  const [isRefreshingRisk, setIsRefreshingRisk] = useState(false)

  // Governance & Exceptions State
  const [severityCounts, setSeverityCounts] = useState<SeverityCounts>({ low: 0, medium: 0, high: 0, critical: 0 })
  const [totalExceptions, setTotalExceptions] = useState(0)
  const [reservePolicies, setReservePolicies] = useState<ReservePolicy[]>([])

  // Search & Filter in Obligors Table
  const [obligorSearch, setObligorSearch] = useState("")
  const [statusFilter, setStatusFilter] = useState<string>("all")

  // Remediation Modal State
  const [remediationTarget, setRemediationTarget] = useState<ObligorRiskItem | SectorRiskItem | null>(null)
  const [remediationType, setRemediationType] = useState<"obligor" | "sector">("obligor")
  const [actionNote, setActionNote] = useState("Commit secondary market syndication & asset re-allocation to ensure compliance within 90 days.")
  const [isSubmittingRemediation, setIsSubmittingRemediation] = useState(false)
  const [remediationResult, setRemediationResult] = useState<RemediationSubmissionResult | null>(null)

  // Stress Testing State
  const [runoffPct, setRunoffPct] = useState(20.0)
  const [stressResult, setStressResult] = useState<StressTestResult | null>(null)
  const [isRunningStress, setIsRunningStress] = useState(false)

  // Initial Data Load
  useEffect(() => {
    setIsLoading(true)
    setErrorMsg("")

    Promise.all([
      fetchPools().catch(() => [] as Pool[]),
      fetchExceptions({ status: "open" }).catch(() => []),
      fetchReservePolicies().catch(() => [] as ReservePolicy[]),
      fetchConcentrationRisk(),
    ])
      .then(([poolsData, openExceptions, policiesData, riskData]) => {
        setPools(poolsData)
        setReservePolicies(policiesData)
        setConcentrationData(riskData)

        const counts: SeverityCounts = { low: 0, medium: 0, high: 0, critical: 0 }
        for (const exception of openExceptions) {
          if (exception.severity in counts) {
            counts[exception.severity as keyof SeverityCounts] += 1
          }
        }
        setSeverityCounts(counts)
        setTotalExceptions(openExceptions.length)
      })
      .catch((err) => {
        setErrorMsg(extractErrorMessage(err, "Failed to load risk and concentration telemetry."))
      })
      .finally(() => {
        setIsLoading(false)
      })
  }, [])

  // Refetch concentration when selected pool changes
  const handlePoolChange = (poolId: string) => {
    setSelectedPoolId(poolId)
    setIsRefreshingRisk(true)
    fetchConcentrationRisk(poolId || undefined)
      .then((data) => {
        setConcentrationData(data)
      })
      .catch((err) => {
        setErrorMsg(extractErrorMessage(err, "Failed to update pool concentration data."))
      })
      .finally(() => {
        setIsRefreshingRisk(false)
      })
  }

  // Handle Stress Testing Trigger
  const handleRunStressTest = () => {
    setIsRunningStress(true)
    runConcentrationStressTest(runoffPct, selectedPoolId || undefined)
      .then((res) => {
        setStressResult(res)
      })
      .catch((err) => {
        alert(extractErrorMessage(err, "Stress testing simulation failed."))
      })
      .finally(() => {
        setIsRunningStress(false)
      })
  }

  // Handle Remediation Submission
  const handleConfirmRemediation = () => {
    if (!remediationTarget) return
    setIsSubmittingRemediation(true)
    const targetName = "obligor_name" in remediationTarget ? remediationTarget.obligor_name : remediationTarget.sector_name

    submitRemediationPlan({
      target_name: targetName,
      target_type: remediationType,
      current_exposure: remediationTarget.total_exposure,
      excess_amount: remediationTarget.excess_amount > 0 ? remediationTarget.excess_amount : remediationTarget.total_exposure * 0.1,
      action_note: actionNote,
      pool_id: selectedPoolId || undefined,
    })
      .then((res) => {
        setRemediationResult(res)
      })
      .catch((err) => {
        alert(extractErrorMessage(err, "Failed to submit SBP remediation plan."))
      })
      .finally(() => {
        setIsSubmittingRemediation(false)
      })
  }

  // Filtered Obligors
  const filteredObligors = useMemo(() => {
    if (!concentrationData?.obligors) return []
    return concentrationData.obligors.filter((o) => {
      const matchSearch =
        o.obligor_name.toLowerCase().includes(obligorSearch.toLowerCase()) ||
        o.sector.toLowerCase().includes(obligorSearch.toLowerCase()) ||
        o.obligor_group.toLowerCase().includes(obligorSearch.toLowerCase())
      const matchStatus = statusFilter === "all" ? true : o.status === statusFilter
      return matchSearch && matchStatus
    })
  }, [concentrationData, obligorSearch, statusFilter])

  // Regulatory Gauges for Cockpit
  const regulatoryGauges: RiskLimitGauge[] = useMemo(() => {
    const totalAssetValue = concentrationData?.total_portfolio_exposure || 1
    const maxSingleAsset = concentrationData?.obligors?.[0]?.total_exposure || 0
    const singleAssetConcentration = (maxSingleAsset / totalAssetValue) * 100

    const totalReserveBalances = reservePolicies.reduce((sum, r) => sum + Number(r.current_balance || 0), 0)
    const reserveCushionPct = (totalReserveBalances / totalAssetValue) * 100

    return [
      {
        label: "SBP Single-Obligor Peak Exposure",
        currentValue: Number(singleAssetConcentration.toFixed(1)),
        thresholdValue: 15.0,
        unit: "%",
        isLowerLimit: false,
      },
      {
        label: "Real Estate Sector Concentration",
        currentValue: Number(
          (
            concentrationData?.sectors.find((s) => s.sector_name.toLowerCase().includes("real estate"))?.portfolio_pct || 0
          ).toFixed(1),
        ),
        thresholdValue: 15.0,
        unit: "%",
        isLowerLimit: false,
      },
      {
        label: "SBP Cash & Sovereign Buffer",
        currentValue: Number(
          (
            concentrationData?.sectors.find((s) => s.sector_name.toLowerCase().includes("sovereign"))?.portfolio_pct || 0
          ).toFixed(1),
        ),
        thresholdValue: 20.0,
        unit: "%",
        isLowerLimit: true,
      },
      {
        label: "PER / IRR Reserve Cushion",
        currentValue: Number(reserveCushionPct.toFixed(1)),
        thresholdValue: 3.0,
        unit: "%",
        isLowerLimit: true,
      },
    ]
  }, [concentrationData, reservePolicies])

  // Exception Donut Slices
  const severitySlices: DonutSlice[] = useMemo(() => {
    const total = severityCounts.critical + severityCounts.high + severityCounts.medium + severityCounts.low
    if (total === 0) return [{ label: "No Open Exceptions", value: 1, color: "#10b981" }]
    const slices: DonutSlice[] = []
    if (severityCounts.critical > 0) slices.push({ label: "Critical", value: severityCounts.critical, color: "#f43f5e" })
    if (severityCounts.high > 0) slices.push({ label: "High", value: severityCounts.high, color: "#f97316" })
    if (severityCounts.medium > 0) slices.push({ label: "Medium", value: severityCounts.medium, color: "#eab308" })
    if (severityCounts.low > 0) slices.push({ label: "Low", value: severityCounts.low, color: "#10b981" })
    return slices
  }, [severityCounts])

  // Status Badge Mapper
  const getStatusBadge = (status: "safe" | "early_warning" | "breach") => {
    if (status === "breach") {
      return (
        <span className="inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-semibold bg-red-500/20 text-red-400 border border-red-500/30">
          BREACH (&gt;100%)
        </span>
      )
    }
    if (status === "early_warning") return <Badge variant="gold">EARLY WARNING (&ge;80%)</Badge>
    return <Badge variant="emerald">SAFE (&lt;80%)</Badge>
  }

  // Obligor Table Columns
  const obligorColumns: TableColumn<ObligorRiskItem>[] = [
    {
      header: "Counterparty / Obligor",
      accessor: (row) => (
        <div>
          <div className="font-semibold text-ink-primary">{row.obligor_name}</div>
          <div className="text-xs text-ink-muted flex items-center gap-2 mt-0.5">
            <span>Group: {row.obligor_group}</span>
            <span>•</span>
            <span className="font-mono text-emerald-400">{row.credit_rating}</span>
            {row.is_sovereign && <span className="text-[10px] bg-sky-500/20 text-sky-400 px-1 py-0.5 rounded">Sovereign / PSE</span>}
          </div>
        </div>
      ),
    },
    {
      header: "Economic Sector",
      accessor: (row) => (
        <div>
          <span className="text-ink-secondary text-sm">{row.sector}</span>
          <div className="text-xs text-ink-muted">{row.shariah_structure}</div>
        </div>
      ),
    },
    {
      header: "Exposure (PKR)",
      accessor: (row) => (
        <div>
          <div className="font-mono font-medium text-ink-primary">
            PKR {row.total_exposure.toLocaleString(undefined, { minimumFractionDigits: 2 })}
          </div>
          <div className="text-xs text-ink-muted">Assets: {row.asset_references.join(", ")}</div>
        </div>
      ),
    },
    {
      header: "Pool Share / Limit",
      accessor: (row) => (
        <div>
          <div className="flex items-center gap-1.5 font-medium">
            <span className={row.portfolio_pct > row.sbp_limit_pct ? "text-red-400 font-bold" : "text-ink-primary"}>
              {row.portfolio_pct}%
            </span>
            <span className="text-xs text-ink-muted">/ {row.sbp_limit_pct}%</span>
          </div>
          <div className="w-24 bg-white/10 rounded-full h-1.5 mt-1 overflow-hidden">
            <div
              className={`h-full rounded-full ${
                row.status === "breach" ? "bg-red-500" : row.status === "early_warning" ? "bg-amber-400" : "bg-emerald-500"
              }`}
              style={{ width: `${Math.min(100, row.utilization_pct)}%` }}
            />
          </div>
        </div>
      ),
    },
    {
      header: "Headroom / Excess",
      accessor: (row) =>
        row.excess_amount > 0 ? (
          <span className="font-mono text-xs font-semibold text-red-400">
            +PKR {row.excess_amount.toLocaleString(undefined, { minimumFractionDigits: 0 })} Excess
          </span>
        ) : (
          <span className="font-mono text-xs text-emerald-400">
            PKR {row.headroom_amount.toLocaleString(undefined, { minimumFractionDigits: 0 })} Headroom
          </span>
        ),
    },
    {
      header: "Status",
      accessor: (row) => getStatusBadge(row.status),
    },
    {
      header: "Action",
      accessor: (row) =>
        row.status !== "safe" ? (
          <Button
            variant="secondary"
            className="text-xs py-1 px-2 border-red-500/30 text-red-300 hover:bg-red-500/20"
            onClick={() => {
              setRemediationTarget(row)
              setRemediationType("obligor")
              setRemediationResult(null)
            }}
          >
            ⚖️ Remediate
          </Button>
        ) : (
          <span className="text-xs text-ink-muted">Within PR Cap</span>
        ),
    },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-24 text-ink-secondary gap-3">
        <Spinner className="h-6 w-6 text-emerald-400" />
        <span className="text-sm">Calculating SBP Statutory Single-Obligor & Sector Concentration telemetry...</span>
      </div>
    )
  }

  const breachesCount = concentrationData?.breach_summary.breaches_count || 0
  const warningsCount = concentrationData?.breach_summary.early_warnings_count || 0

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <PageHeader
        screenNumber="31"
        title="SBP Statutory Risk Limit & Concentration Cockpit"
        subtitle="SBP Prudential Regulations R-1 & R-6, Single Obligor caps, sector thresholds and automated breach remediation"
        actions={
          <div className="flex items-center gap-3">
            <select
              value={selectedPoolId}
              onChange={(e) => handlePoolChange(e.target.value)}
              className="bg-navy-900 border border-white/15 rounded px-3 py-1.5 text-xs text-ink-primary focus:outline-none focus:border-emerald-500"
            >
              <option value="">🌐 Consolidated Portfolio (All Pools)</option>
              {pools.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.code})
                </option>
              ))}
            </select>

            <Button
              variant="secondary"
              className="text-xs"
              onClick={() => handlePoolChange(selectedPoolId)}
              disabled={isRefreshingRisk}
            >
              {isRefreshingRisk ? "Recalculating..." : "🔄 Refresh Ratios"}
            </Button>
          </div>
        }
      />

      {errorMsg && (
        <div className="rounded-lg border border-red-500/30 bg-red-950/20 p-3 text-xs text-red-300">
          {errorMsg}
        </div>
      )}

      {/* SBP Regulatory Alert Banner if any breaches exist */}
      {breachesCount > 0 && (
        <div className="rounded-lg border border-red-500/30 bg-red-950/20 p-4 text-sm text-red-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-lg">
          <div className="flex items-center gap-3">
            <span className="text-2xl">🚨</span>
            <div>
              <div className="font-bold text-red-300">
                SBP PR Regulatory Limit Alert: {breachesCount} Statutory Breaches Detected
              </div>
              <div className="text-xs text-red-200/80 mt-0.5">
                Certain obligor or sector exposures exceed SBP BPRD statutory limits (15% Single Obligor / 15% Real Estate). A formal remediation filing is required within 90 days.
              </div>
            </div>
          </div>
          <Button
            variant="secondary"
            className="text-xs border-red-500/50 text-red-200 bg-red-900/40 hover:bg-red-900/70 whitespace-nowrap"
            onClick={() => setActiveTab("obligors")}
          >
            Review & Remediate Breaches
          </Button>
        </div>
      )}

      {/* Top Level Metric Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <StatCard
          label="Total Portfolio Assets"
          value={`PKR ${((concentrationData?.total_portfolio_exposure || 0) / 1000000).toFixed(1)}M`}
          delta={`${concentrationData?.asset_count || 0} Earmarked Assets`}
          deltaTone="neutral"
        />
        <StatCard
          label="Single Obligor Peak"
          value={`${concentrationData?.obligors[0]?.portfolio_pct || 0}%`}
          delta={`Limit: ${concentrationData?.obligors[0]?.sbp_limit_pct || 15}%`}
          deltaTone={
            (concentrationData?.obligors[0]?.portfolio_pct || 0) > (concentrationData?.obligors[0]?.sbp_limit_pct || 15)
              ? "negative"
              : "positive"
          }
        />
        <StatCard
          label="Top Sector Exposure"
          value={`${concentrationData?.sectors[0]?.portfolio_pct || 0}%`}
          delta={concentrationData?.sectors[0]?.sector_name || "N/A"}
          deltaTone="neutral"
        />
        <StatCard
          label="Active SBP Breaches"
          value={String(breachesCount)}
          delta={breachesCount > 0 ? "Requires ALCO filing" : "Fully Compliant"}
          deltaTone={breachesCount > 0 ? "negative" : "positive"}
        />
        <StatCard
          label="Early Warning Alerts"
          value={String(warningsCount)}
          delta="Exposure >= 80% of PR cap"
          deltaTone={warningsCount > 0 ? "negative" : "positive"}
        />
      </div>

      {/* Navigation Sub-Tabs */}
      <div className="flex gap-4 border-b border-white/8 text-sm">
        {[
          { key: "obligors", label: "Single-Obligor & Counterparties (PR R-1)", count: concentrationData?.obligors.length },
          { key: "sectors", label: "Economic Sector Distribution (PR R-6)", count: concentrationData?.sectors.length },
          { key: "prudential", label: "SBP Prudential Scorecard", count: concentrationData?.prudential_scorecard.length },
          { key: "stress-test", label: "⚡ Concentration Stress Simulator" },
          { key: "exceptions", label: "Governance & Exceptions", count: totalExceptions },
        ].map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key as RiskTab)}
            className={`px-2 pb-2 font-medium transition-colors flex items-center gap-1.5 ${
              activeTab === tab.key
                ? "border-b-2 border-emerald-500 text-ink-primary font-semibold"
                : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            <span>{tab.label}</span>
            {tab.count !== undefined && (
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/10 text-ink-secondary">
                {tab.count}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* TAB 1: Single Obligors Table */}
      {activeTab === "obligors" && (
        <Card
          title="Single Counterparty & Obligor Exposure Matrix (SBP Regulation R-1)"
          actions={
            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Search counterparty or sector..."
                value={obligorSearch}
                onChange={(e) => setObligorSearch(e.target.value)}
                className="bg-navy-900 border border-white/15 rounded px-2.5 py-1 text-xs text-ink-primary placeholder:text-ink-muted w-48 focus:outline-none focus:border-emerald-500"
              />
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-navy-900 border border-white/15 rounded px-2.5 py-1 text-xs text-ink-primary focus:outline-none focus:border-emerald-500"
              >
                <option value="all">All Statuses</option>
                <option value="breach">Breach Only</option>
                <option value="early_warning">Early Warning Only</option>
                <option value="safe">Safe Only</option>
              </select>
            </div>
          }
        >
          <div className="mb-4 text-xs text-ink-secondary">
            Statutory Limit: Maximum 15% of Pool Assets to any single private sector corporate obligor; 20% to connected groups; 25% to Sovereign-guaranteed public entities. Exposures exceeding 80% trigger automated Early Warning Indicators (EWI).
          </div>
          <Table<ObligorRiskItem> columns={obligorColumns} data={filteredObligors} keyField={(row) => row.obligor_name} />
        </Card>
      )}

      {/* TAB 2: Sector Concentration */}
      {activeTab === "sectors" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card title="Economic Sector Exposure Breakdown (PR R-6)" className="lg:col-span-2">
            <div className="space-y-5">
              {concentrationData?.sectors.map((sec) => (
                <div key={sec.sector_name} className="space-y-1.5 p-3 rounded bg-white/5 border border-white/5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-semibold text-ink-primary flex items-center gap-2">
                      {sec.sector_name}
                      {sec.status === "breach" && (
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-red-500/20 text-red-400 border border-red-500/30">
                          CAP EXCEEDED
                        </span>
                      )}
                      {sec.status === "early_warning" && <Badge variant="gold">NEAR LIMIT</Badge>}
                    </span>
                    <div className="flex items-center gap-2 font-mono">
                      <span className="text-ink-muted">PKR {sec.total_exposure.toLocaleString()}</span>
                      <span className={sec.portfolio_pct > sec.sbp_limit_pct ? "text-red-400 font-bold" : "text-ink-primary"}>
                        {sec.portfolio_pct}% / {sec.sbp_limit_pct}% Cap
                      </span>
                    </div>
                  </div>

                  <div className="w-full bg-navy-950 rounded-full h-2.5 overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all duration-500 ${
                        sec.status === "breach" ? "bg-red-500" : sec.status === "early_warning" ? "bg-amber-400" : "bg-emerald-500"
                      }`}
                      style={{ width: `${Math.min(100, sec.utilization_pct)}%` }}
                    />
                  </div>

                  <div className="flex items-center justify-between text-[11px] text-ink-muted">
                    <span>Utilization: {sec.utilization_pct}%</span>
                    {sec.excess_amount > 0 ? (
                      <span className="text-red-400 font-semibold">
                        Excess: PKR {sec.excess_amount.toLocaleString()}
                        <button
                          onClick={() => {
                            setRemediationTarget(sec)
                            setRemediationType("sector")
                            setRemediationResult(null)
                          }}
                          className="ml-2 text-red-300 underline hover:text-red-200"
                        >
                          File SBP Mitigation Plan &rarr;
                        </button>
                      </span>
                    ) : (
                      <span className="text-emerald-400">Headroom: PKR {sec.headroom_amount.toLocaleString()}</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card title="Corporate Group Concentration (PR R-1)">
            <div className="space-y-4 text-xs">
              <p className="text-ink-muted text-xs">
                SBP PR Regulation R-1 caps total exposure to any connected corporate group or conglomerate at 20% of pool assets.
              </p>
              {concentrationData?.groups.map((grp) => (
                <div key={grp.group_name} className="p-3 rounded bg-white/5 border border-white/5 space-y-1">
                  <div className="flex items-center justify-between font-semibold text-ink-primary">
                    <span>{grp.group_name}</span>
                    <span className={grp.portfolio_pct > grp.sbp_limit_pct ? "text-red-400 font-bold" : "text-ink-secondary"}>
                      {grp.portfolio_pct}%
                    </span>
                  </div>
                  <div className="text-[11px] text-ink-muted">
                    Entities: {grp.obligor_names.join(", ")}
                  </div>
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[10px] text-ink-muted">Limit: {grp.sbp_limit_pct}%</span>
                    {getStatusBadge(grp.status)}
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {/* TAB 3: Prudential Scorecard */}
      {activeTab === "prudential" && (
        <Card title="State Bank of Pakistan (SBP) Prudential Scorecard Matrix">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-white/10 text-ink-muted uppercase tracking-wider text-[11px]">
                  <th className="py-2.5 px-3">SBP Regulation Reference</th>
                  <th className="py-2.5 px-3">Statutory Description</th>
                  <th className="py-2.5 px-3">Regulatory Cap</th>
                  <th className="py-2.5 px-3">Current Utilization</th>
                  <th className="py-2.5 px-3">Compliance Verdict</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {concentrationData?.prudential_scorecard.map((item, idx) => (
                  <tr key={idx} className="hover:bg-white/5 transition-colors">
                    <td className="py-3 px-3 font-semibold text-ink-primary">{item.regulation}</td>
                    <td className="py-3 px-3 text-ink-secondary">{item.description}</td>
                    <td className="py-3 px-3 font-mono font-medium text-ink-primary">{item.statutory_limit}</td>
                    <td className="py-3 px-3 font-mono font-bold">
                      <span className={item.status === "breach" ? "text-red-400" : item.status === "warning" ? "text-amber-400" : "text-emerald-400"}>
                        {item.current_value}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      {item.status === "breach" ? (
                        <span className="inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-semibold bg-red-500/20 text-red-400 border border-red-500/30">
                          STATUTORY BREACH
                        </span>
                      ) : item.status === "warning" ? (
                        <Badge variant="gold">EARLY WARNING</Badge>
                      ) : (
                        <Badge variant="emerald">COMPLIANT</Badge>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 4: Concentration Stress Testing Simulator */}
      {activeTab === "stress-test" && (
        <div className="space-y-6">
          <Card
            title="Portfolio Contraction & Liquidity Shock Simulator"
            actions={
              <Button variant="primary" className="text-xs" onClick={handleRunStressTest} disabled={isRunningStress}>
                {isRunningStress ? "Simulating..." : "⚡ Execute Stress Simulation"}
              </Button>
            }
          >
            <p className="text-xs text-ink-secondary mb-4">
              Simulate adverse macroeconomic scenarios where depositor withdrawals trigger sudden pool asset contractions (-5% to -40%). As the denominator shrinks, fixed asset exposures spike relative to statutory SBP PR concentration limits.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 items-center p-4 rounded bg-white/5 border border-white/5">
              <div>
                <label className="block text-xs font-semibold text-ink-primary mb-2">
                  Hypothetical Deposit Runoff / Contraction: <span className="text-emerald-400 font-bold">{runoffPct}%</span>
                </label>
                <input
                  type="range"
                  min="5"
                  max="40"
                  step="5"
                  value={runoffPct}
                  onChange={(e) => setRunoffPct(Number(e.target.value))}
                  className="w-full accent-emerald-500 cursor-pointer"
                />
                <div className="flex justify-between text-[10px] text-ink-muted mt-1">
                  <span>-5% Mild Runoff</span>
                  <span>-20% SBP Baseline Stress</span>
                  <span>-40% Severe Liquidity Crisis</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="p-3 bg-navy-950 rounded border border-white/5">
                  <div className="text-[10px] text-ink-muted uppercase">Pre-Shock Assets</div>
                  <div className="text-sm font-bold font-mono text-ink-primary mt-1">
                    PKR {((concentrationData?.total_portfolio_exposure || 0) / 1000000).toFixed(1)}M
                  </div>
                </div>
                <div className="p-3 bg-navy-950 rounded border border-white/5">
                  <div className="text-[10px] text-ink-muted uppercase">Post-Shock Assets</div>
                  <div className="text-sm font-bold font-mono text-amber-400 mt-1">
                    PKR {(((concentrationData?.total_portfolio_exposure || 0) * (1 - runoffPct / 100)) / 1000000).toFixed(1)}M
                  </div>
                </div>
              </div>
            </div>

            {stressResult && (
              <div className="mt-6 space-y-4">
                <div className="flex items-center justify-between p-3 rounded bg-red-950/20 border border-red-500/20 text-xs">
                  <span className="font-semibold text-red-300">
                    Post-Stress Simulation Outcome: {stressResult.post_stress_breaches_count} Total Breaches (+{stressResult.incremental_breaches} Incremental Breaches)
                  </span>
                  <span className="text-ink-muted">Asset Base: PKR {(stressResult.stressed_portfolio_exposure / 1000000).toFixed(1)}M</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs border-collapse">
                    <thead>
                      <tr className="border-b border-white/10 text-ink-muted uppercase text-[10px]">
                        <th className="py-2 px-3">Obligor</th>
                        <th className="py-2 px-3">Pre-Stress %</th>
                        <th className="py-2 px-3">Post-Stress %</th>
                        <th className="py-2 px-3">Variance</th>
                        <th className="py-2 px-3">Statutory Cap</th>
                        <th className="py-2 px-3">Stressed Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                      {stressResult.stressed_obligors.map((so) => (
                        <tr key={so.obligor_name} className="hover:bg-white/5">
                          <td className="py-2.5 px-3 font-semibold text-ink-primary">{so.obligor_name}</td>
                          <td className="py-2.5 px-3 font-mono">{so.pre_stress_pct}%</td>
                          <td className="py-2.5 px-3 font-mono font-bold text-amber-400">{so.post_stress_pct}%</td>
                          <td className="py-2.5 px-3 font-mono text-xs text-red-400">+{so.pct_delta}%</td>
                          <td className="py-2.5 px-3 font-mono text-ink-muted">{so.sbp_limit_pct}%</td>
                          <td className="py-2.5 px-3">{getStatusBadge(so.status)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* TAB 5: Exceptions & Governance Queue */}
      {activeTab === "exceptions" && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <Card title="Exception Severity Breakdown" className="lg:col-span-1">
            <DonutChart
              data={severitySlices}
              centerLabel="Exceptions"
              centerValue={String(totalExceptions)}
              formatValue={(v) => (totalExceptions === 0 ? "0 Cases" : `${v} Cases`)}
            />
          </Card>

          <Card title="Active Governance & Regulatory Queues" className="lg:col-span-2">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <StatCard label="Critical" value={String(severityCounts.critical)} deltaTone={severityCounts.critical > 0 ? "negative" : "positive"} />
              <StatCard label="High" value={String(severityCounts.high)} deltaTone={severityCounts.high > 0 ? "negative" : "positive"} />
              <StatCard label="Medium" value={String(severityCounts.medium)} deltaTone="neutral" />
              <StatCard label="Low" value={String(severityCounts.low)} deltaTone="neutral" />
            </div>
            <p className="mt-4 text-xs text-ink-muted">
              Regulatory cases classified under SBP BPRD guidelines. Critical concentration breaches automatically prevent end-of-period profit distribution until ALCO sign-off.
            </p>
          </Card>
        </div>
      )}

      {/* Risk Limit Gauges Bottom Row */}
      <RiskGaugeChart gauges={regulatoryGauges} title="Prudential Concentration & Exposure Safeguards" />

      {/* SBP STATUTORY REMEDIATION WIZARD MODAL */}
      {remediationTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in">
          <div className="w-full max-w-2xl bg-navy-900 border border-white/15 rounded-xl shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
            <div className="px-6 py-4 border-b border-white/10 flex items-center justify-between bg-navy-950">
              <div className="flex items-center gap-2">
                <span className="text-xl">⚖️</span>
                <h3 className="text-base font-bold text-ink-primary">
                  SBP Statutory Concentration Breach Remediation
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setRemediationTarget(null)}
                className="text-ink-muted hover:text-ink-primary text-lg"
              >
                ✕
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto text-xs">
              {remediationResult ? (
                <div className="space-y-4">
                  <div className="p-4 rounded-lg bg-emerald-950/30 border border-emerald-500/30 text-emerald-300">
                    <div className="font-bold text-sm">✅ Remediation Plan Registered Successfully!</div>
                    <div className="text-xs mt-1 text-emerald-200/80">
                      Exception Case <span className="font-mono">{remediationResult.exception_case_id}</span> has been logged in the Governance Queue. ALCO statutory filing memo prepared.
                    </div>
                  </div>

                  <div className="p-3 bg-navy-950 rounded border border-white/10 space-y-2">
                    <div className="font-semibold text-ink-primary">Action Steps Committed:</div>
                    <ul className="list-disc list-inside space-y-1 text-ink-secondary">
                      {remediationResult.plan.action_steps.map((st, i) => (
                        <li key={i}>{st}</li>
                      ))}
                    </ul>
                  </div>

                  <div className="flex justify-end">
                    <Button variant="primary" onClick={() => setRemediationTarget(null)}>
                      Close & Return to Dashboard
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <div className="p-3 rounded bg-red-950/20 border border-red-500/20 text-red-200">
                    <div className="font-bold">
                      Target: {"obligor_name" in remediationTarget ? remediationTarget.obligor_name : remediationTarget.sector_name}
                    </div>
                    <div className="mt-1 text-xs">
                      Outstanding Exposure: PKR {remediationTarget.total_exposure.toLocaleString()} ({remediationTarget.portfolio_pct}% of pool) | Limit: {remediationTarget.sbp_limit_pct}%
                    </div>
                  </div>

                  <div>
                    <label className="block text-ink-secondary font-medium mb-1">
                      SBP BPRD Mandatory Remediation Strategy & ALCO Action Note:
                    </label>
                    <textarea
                      rows={4}
                      value={actionNote}
                      onChange={(e) => setActionNote(e.target.value)}
                      className="w-full bg-navy-950 border border-white/15 rounded p-2 text-ink-primary focus:outline-none focus:border-emerald-500"
                    />
                  </div>

                  <div className="p-3 bg-navy-950 rounded border border-white/5 space-y-1.5 text-ink-muted">
                    <div className="font-semibold text-ink-secondary">Mandatory Mitigation Steps:</div>
                    <div>1. Place excess PKR with consortium partner Islamic banks via secondary syndication.</div>
                    <div>2. Rebalance asset assignments with Treasury liquid sovereign Sukuk.</div>
                    <div>3. File Form BPRD-PR1 with State Bank of Pakistan within 7 business days.</div>
                  </div>

                  <div className="flex items-center justify-end gap-3 pt-3 border-t border-white/10">
                    <Button variant="secondary" onClick={() => setRemediationTarget(null)} disabled={isSubmittingRemediation}>
                      Cancel
                    </Button>
                    <Button
                      variant="primary"
                      onClick={handleConfirmRemediation}
                      disabled={isSubmittingRemediation}
                      className="bg-red-600 hover:bg-red-500 text-white border-none"
                    >
                      {isSubmittingRemediation ? "Filing Remediation..." : "Submit Formal Remediation Plan & Log Case"}
                    </Button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
