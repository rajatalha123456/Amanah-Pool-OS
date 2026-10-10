import { useEffect, useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import {
  fetchPoolVersionDiff,
  fetchPoolVersions,
  createPoolVersion,
} from "../../api/pools"
import type {
  PoolVersion,
  PoolVersionDiffResponse,
  VersionDiffItem,
  CreatePoolVersionInput,
} from "../../types"

interface PoolVersionComparisonProps {
  poolId: string
  onVersionCreated?: () => void
}

export function PoolVersionComparison({
  poolId,
  onVersionCreated,
}: PoolVersionComparisonProps) {
  const [versions, setVersions] = useState<PoolVersion[]>([])
  const [v1Id, setV1Id] = useState<string>("")
  const [v2Id, setV2Id] = useState<string>("")
  const [diffData, setDiffData] = useState<PoolVersionDiffResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Filters
  const [selectedCategory, setSelectedCategory] = useState<string>("all")
  const [onlyChanged, setOnlyChanged] = useState<boolean>(false)
  const [searchQuery, setSearchQuery] = useState<string>("")

  // Modal for new version creation
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [modalError, setModalError] = useState<string | null>(null)
  const [newVersionForm, setNewVersionForm] = useState<CreatePoolVersionInput>({
    psr: {
      mudarib_share_pct: 45.0,
      rabbul_maal_share_pct: 55.0,
      wakalah_fee_pct: 0.0,
      performance_incentive_pct: 15.0,
    },
    reserve_policy: {
      per_ceiling_pct: 3.0,
      irr_ceiling_pct: 1.5,
      max_monthly_appropriation_pct: 15.0,
      hiba_concession_allowed: true,
    },
    benchmarks: {
      benchmark_index: "1-Month KIBOR",
      spread_bps: 85,
      target_yield_pct: 17.85,
    },
    shariah_resolution_code: "SB-RES-2026-11-CALIB",
    approving_scholar: "Mufti Dr. Taqi Usmani (Shariah Board Chair)",
    change_rationale: "Liquidity yield calibration in response to central bank rate trajectory",
  })

  // Load versions list
  useEffect(() => {
    async function init() {
      try {
        setIsLoading(true)
        setError(null)
        const vList = await fetchPoolVersions(poolId)
        setVersions(vList)

        if (vList.length >= 2) {
          // Default: compare oldest (v1) with latest (e.g. v2)
          const sorted = [...vList].sort((a, b) => a.version_number - b.version_number)
          setV1Id(sorted[0].id)
          setV2Id(sorted[sorted.length - 1].id)
        } else if (vList.length === 1) {
          setV1Id(vList[0].id)
          setV2Id(vList[0].id)
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to load pool versions")
      } finally {
        setIsLoading(false)
      }
    }
    init()
  }, [poolId])

  // Load diff when v1Id or v2Id changes
  useEffect(() => {
    if (!v1Id || !v2Id) return
    async function loadDiff() {
      try {
        setIsLoading(true)
        setError(null)
        const res = await fetchPoolVersionDiff(poolId, v1Id, v2Id)
        setDiffData(res)
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : "Failed to compare versions")
      } finally {
        setIsLoading(false)
      }
    }
    loadDiff()
  }, [poolId, v1Id, v2Id])

  const categories = diffData
    ? ["all", ...Array.from(new Set(diffData.diff_matrix.map((d) => d.category)))]
    : ["all"]

  const filteredDiffs = diffData?.diff_matrix.filter((item) => {
    if (selectedCategory !== "all" && item.category !== selectedCategory) return false
    if (onlyChanged && !item.is_changed) return false
    if (
      searchQuery &&
      !item.label.toLowerCase().includes(searchQuery.toLowerCase()) &&
      !item.category.toLowerCase().includes(searchQuery.toLowerCase())
    ) {
      return false
    }
    return true
  })

  async function handleCreateVersionSubmit(e: React.FormEvent) {
    e.preventDefault()
    setIsSubmitting(true)
    setModalError(null)
    try {
      await createPoolVersion(poolId, newVersionForm)
      setIsModalOpen(false)
      // Refresh version list
      const vList = await fetchPoolVersions(poolId)
      setVersions(vList)
      const sorted = [...vList].sort((a, b) => a.version_number - b.version_number)
      setV1Id(sorted[0].id)
      setV2Id(sorted[sorted.length - 1].id)
      if (onVersionCreated) onVersionCreated()
    } catch (err: unknown) {
      setModalError(err instanceof Error ? err.message : "Failed to create new version")
    } finally {
      setIsSubmitting(false)
    }
  }

  function renderValue(item: VersionDiffItem, val: unknown) {
    if (val === null || val === undefined) return <span className="text-ink-muted">—</span>
    if (item.format === "boolean") {
      return val ? (
        <span className="inline-flex items-center gap-1 rounded bg-emerald-500/10 px-2 py-0.5 text-xs font-medium text-emerald-400">
          ✓ Allowed
        </span>
      ) : (
        <span className="inline-flex items-center gap-1 rounded bg-red-500/10 px-2 py-0.5 text-xs font-medium text-red-400">
          ✗ Prohibited
        </span>
      )
    }
    if (item.format === "percentage") {
      return <span className="font-mono text-ink-primary">{Number(val).toFixed(2)}%</span>
    }
    if (item.format === "bps") {
      return <span className="font-mono text-ink-primary">+{String(val)} bps</span>
    }
    if (typeof val === "object") {
      return <span className="text-ink-primary font-mono">{JSON.stringify(val)}</span>
    }
    return <span className="text-ink-primary">{String(val)}</span>
  }

  return (
    <div className="space-y-6">
      {/* Top Banner & Control Deck */}
      <Card className="border border-gold-500/20 bg-gradient-to-r from-navy-900 via-navy-950 to-navy-900">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="rounded bg-gold-500/20 px-2 py-0.5 text-xs font-semibold text-gold-400">
                BRD SCREEN 05
              </span>
              <span className="rounded bg-navy-800 px-2 py-0.5 text-xs text-ink-secondary">
                Governance Diff Matrix
              </span>
              <span className="text-xs text-ink-muted">SBP IBD Circular 03/2012</span>
            </div>
            <h2 className="mt-1 text-lg font-semibold text-ink-primary">
              Pool Version Comparison & Governance Diff Matrix
            </h2>
            <p className="text-xs text-ink-secondary">
              Deterministic side-by-side parameter diff comparing Profit Sharing Ratios (PSR),
              weightage bands, prudential reserve ceilings, and Shariah board attestation digests.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-2">
            <Button
              variant="secondary"
              className="text-xs"
              onClick={() => {
                if (versions.length >= 2) {
                  const sorted = [...versions].sort(
                    (a, b) => a.version_number - b.version_number,
                  )
                  setV1Id(sorted[sorted.length - 2].id)
                  setV2Id(sorted[sorted.length - 1].id)
                }
              }}
              disabled={versions.length < 2}
            >
              Latest vs Previous
            </Button>
            <Button
              variant="primary"
              className="bg-emerald-600 text-xs hover:bg-emerald-500"
              onClick={() => setIsModalOpen(true)}
            >
              + New Calibration Version
            </Button>
          </div>
        </div>

        {/* Version Pickers */}
        <div className="mt-4 grid grid-cols-1 gap-4 border-t border-white/5 pt-4 md:grid-cols-2 lg:grid-cols-3">
          <div>
            <label className="mb-1 block text-xs font-medium text-ink-secondary">
              Baseline Version (Base)
            </label>
            <select
              value={v1Id}
              onChange={(e) => setV1Id(e.target.value)}
              className="w-full rounded-md border border-white/10 bg-navy-950 px-3 py-1.5 text-sm text-ink-primary focus:border-gold-500 focus:outline-none"
            >
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version_number} {v.is_current ? "(Active)" : "(Historical)"} —{" "}
                  {v.created_at?.slice(0, 10)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="mb-1 block text-xs font-medium text-ink-secondary">
              Comparison Version (Target)
            </label>
            <select
              value={v2Id}
              onChange={(e) => setV2Id(e.target.value)}
              className="w-full rounded-md border border-white/10 bg-navy-950 px-3 py-1.5 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
            >
              {versions.map((v) => (
                <option key={v.id} value={v.id}>
                  v{v.version_number} {v.is_current ? "(Active)" : "(Historical)"} —{" "}
                  {v.created_at?.slice(0, 10)}
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-end">
            <div className="w-full rounded bg-white/5 p-2 text-xs">
              <span className="text-ink-muted">Comparing: </span>
              <span className="font-semibold text-gold-400">
                v{diffData?.v1.version_number ?? "—"}
              </span>
              <span className="text-ink-muted"> vs </span>
              <span className="font-semibold text-emerald-400">
                v{diffData?.v2.version_number ?? "—"}
              </span>
              <span className="ml-2 text-ink-secondary">
                ({diffData?.summary.total_changes ?? 0} parameter deltas)
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Error or Loading */}
      {isLoading && (
        <div className="flex items-center justify-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-6 w-6 text-gold-400" />
          <span className="text-sm">Calculating cryptographic diff matrix...</span>
        </div>
      )}

      {error && (
        <Card className="border-red-500/30 bg-red-500/10">
          <p className="text-sm text-red-400">Error: {error}</p>
        </Card>
      )}

      {/* Summary Scorecard */}
      {diffData && !isLoading && (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-5">
            <Card className="p-3">
              <span className="text-[11px] font-medium text-ink-muted uppercase">
                Total Modifications
              </span>
              <p className="mt-1 text-2xl font-bold text-ink-primary">
                {diffData.summary.total_changes}
              </p>
              <span className="text-[11px] text-ink-secondary">
                {diffData.summary.field_changes_count} Core •{" "}
                {diffData.summary.tier_changes_count} Tiers
              </span>
            </Card>

            <Card className="p-3">
              <span className="text-[11px] font-medium text-ink-muted uppercase">
                Governance Risk Impact
              </span>
              <div className="mt-1">
                <Badge
                  variant={
                    diffData.summary.risk_impact === "HIGH"
                      ? "gold"
                      : diffData.summary.risk_impact === "CRITICAL"
                        ? "navy"
                        : "emerald"
                  }
                >
                  {diffData.summary.risk_impact} IMPACT
                </Badge>
              </div>
              <span className="mt-1 block text-[11px] text-ink-secondary">
                {diffData.summary.requires_regulatory_filing
                  ? "SBP Filing Required"
                  : "Internal Routine"}
              </span>
            </Card>

            <Card className="p-3">
              <span className="text-[11px] font-medium text-ink-muted uppercase">
                Shariah Attestation
              </span>
              <div className="mt-1 flex items-center gap-1.5 text-xs text-emerald-400">
                <span>✓</span>
                <span className="font-semibold">Quorum Certified</span>
              </div>
              <span className="text-[11px] text-ink-secondary font-mono">
                {diffData.v2.shariah_resolution}
              </span>
            </Card>

            <Card className="p-3">
              <span className="text-[11px] font-medium text-ink-muted uppercase">
                Base SHA-256 Seal
              </span>
              <p className="mt-1 font-mono text-[11px] text-ink-secondary truncate">
                {diffData.v1.snapshot_hash.slice(0, 16)}...
              </p>
              <span className="text-[10px] text-ink-muted">
                v{diffData.v1.version_number} Immutable Hash
              </span>
            </Card>

            <Card className="p-3">
              <span className="text-[11px] font-medium text-ink-muted uppercase">
                Target SHA-256 Seal
              </span>
              <p className="mt-1 font-mono text-[11px] text-emerald-400 truncate">
                {diffData.v2.snapshot_hash.slice(0, 16)}...
              </p>
              <span className="text-[10px] text-ink-muted">
                v{diffData.v2.version_number} Immutable Hash
              </span>
            </Card>
          </div>

          {/* Filter Bar */}
          <div className="flex flex-col gap-3 rounded-lg border border-white/5 bg-navy-900/60 p-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex flex-wrap items-center gap-1.5">
              {categories.map((cat) => (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`rounded-md px-2.5 py-1 text-xs font-medium transition-colors ${
                    selectedCategory === cat
                      ? "bg-emerald-600 text-white"
                      : "bg-white/5 text-ink-secondary hover:bg-white/10 hover:text-ink-primary"
                  }`}
                >
                  {cat === "all" ? "All Categories" : cat}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <label className="flex cursor-pointer items-center gap-1.5 text-xs text-ink-secondary">
                <input
                  type="checkbox"
                  checked={onlyChanged}
                  onChange={(e) => setOnlyChanged(e.target.checked)}
                  className="rounded border-white/10 bg-navy-950 text-emerald-500 focus:ring-0"
                />
                <span>Only Changed ({diffData.summary.field_changes_count})</span>
              </label>

              <input
                type="text"
                placeholder="Search parameter..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-40 rounded-md border border-white/10 bg-navy-950 px-2 py-1 text-xs text-ink-primary placeholder-ink-muted focus:border-gold-500 focus:outline-none"
              />
            </div>
          </div>

          {/* Side-by-Side Diff Table */}
          <Card title="Executive Parameter Comparison Matrix">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/8 text-[11px] font-semibold tracking-wider text-ink-muted uppercase">
                    <th className="py-2.5 px-3">Parameter & Regulatory Domain</th>
                    <th className="py-2.5 px-3">
                      v{diffData.v1.version_number} (Baseline)
                    </th>
                    <th className="py-2.5 px-3">
                      v{diffData.v2.version_number} (Target Calibration)
                    </th>
                    <th className="py-2.5 px-3">Delta / Direction</th>
                    <th className="py-2.5 px-3">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-xs">
                  {filteredDiffs && filteredDiffs.length > 0 ? (
                    filteredDiffs.map((item) => (
                      <tr
                        key={item.key}
                        className={`transition-colors ${
                          item.is_changed ? "bg-gold-500/5 hover:bg-gold-500/10" : "hover:bg-white/2"
                        }`}
                      >
                        <td className="py-3 px-3">
                          <div className="font-medium text-ink-primary">{item.label}</div>
                          <span className="text-[10px] text-ink-muted">
                            {item.category} • {item.key}
                          </span>
                        </td>

                        <td className="py-3 px-3">
                          {renderValue(item, item.v1_value)}
                        </td>

                        <td className="py-3 px-3 font-medium">
                          {renderValue(item, item.v2_value)}
                        </td>

                        <td className="py-3 px-3">
                          {item.is_changed ? (
                            item.delta !== null && item.delta !== undefined ? (
                              <span
                                className={`inline-flex items-center gap-1 rounded px-2 py-0.5 font-mono text-xs font-semibold ${
                                  item.delta > 0
                                    ? "bg-emerald-500/20 text-emerald-400"
                                    : "bg-gold-500/20 text-gold-400"
                                }`}
                              >
                                {item.delta > 0 ? `+${item.delta}` : item.delta}
                                {item.unit ? ` ${item.unit}` : ""}
                              </span>
                            ) : (
                              <span className="rounded bg-gold-500/10 px-2 py-0.5 text-xs text-gold-400">
                                Modified
                              </span>
                            )
                          ) : (
                            <span className="text-ink-muted">Unchanged</span>
                          )}
                        </td>

                        <td className="py-3 px-3">
                          {item.is_changed ? (
                            <Badge variant="gold">Calibration</Badge>
                          ) : (
                            <Badge variant="neutral">Active</Badge>
                          )}
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={5} className="py-6 text-center text-ink-muted">
                        No parameters match the current filters.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Weightage Bands Tier Diff */}
          <Card title="Depositor Tiers & Weightage Multipliers Matrix">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-white/8 text-[11px] font-semibold tracking-wider text-ink-muted uppercase">
                    <th className="py-2.5 px-3">Depositor Tier / Tenor Band</th>
                    <th className="py-2.5 px-3">Tier Code</th>
                    <th className="py-2.5 px-3">v{diffData.v1.version_number} Multiplier</th>
                    <th className="py-2.5 px-3">v{diffData.v2.version_number} Multiplier</th>
                    <th className="py-2.5 px-3">Multiplier Delta</th>
                    <th className="py-2.5 px-3">Tenor Lock (Days)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5 text-xs">
                  {diffData.tiers_diff.map((tier) => (
                    <tr
                      key={tier.code}
                      className={tier.is_changed ? "bg-emerald-500/5" : ""}
                    >
                      <td className="py-3 px-3 font-medium text-ink-primary">
                        {tier.name}
                      </td>
                      <td className="py-3 px-3 font-mono text-ink-secondary">
                        {tier.code}
                      </td>
                      <td className="py-3 px-3 font-mono text-ink-secondary">
                        {tier.v1_weight !== null ? `${tier.v1_weight}x` : "—"}
                      </td>
                      <td className="py-3 px-3 font-mono font-semibold text-emerald-400">
                        {tier.v2_weight !== null ? `${tier.v2_weight}x` : "—"}
                      </td>
                      <td className="py-3 px-3">
                        {tier.delta !== null && tier.delta !== undefined ? (
                          <span
                            className={`rounded px-1.5 py-0.5 font-mono text-[11px] font-bold ${
                              tier.delta > 0
                                ? "bg-emerald-500/20 text-emerald-400"
                                : "bg-red-500/20 text-red-400"
                            }`}
                          >
                            {tier.delta > 0 ? `+${tier.delta}x` : `${tier.delta}x`}
                          </span>
                        ) : (
                          <span className="text-ink-muted">0.00x</span>
                        )}
                      </td>
                      <td className="py-3 px-3 text-ink-secondary">
                        {tier.v2_tenor_days ?? tier.v1_tenor_days ?? 0} days
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Shariah Attestation & Governance Card */}
          <Card title="Shariah Governance & Regulatory Attestation Trail">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div className="rounded-lg border border-white/5 bg-white/2 p-3">
                <span className="text-[11px] font-semibold text-ink-muted uppercase">
                  v{diffData.v1.version_number} Governance Memo
                </span>
                <p className="mt-1 text-xs text-ink-secondary">
                  Resolution Ref:{" "}
                  <span className="font-mono text-ink-primary">
                    {diffData.v1.shariah_resolution}
                  </span>
                </p>
                <p className="mt-0.5 text-xs text-ink-secondary">
                  Created by: {diffData.v1.created_by}
                </p>
                <p className="mt-0.5 text-xs text-ink-muted">
                  Timestamp: {diffData.v1.created_at ?? "System Genesis"}
                </p>
              </div>

              <div className="rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-3">
                <span className="text-[11px] font-semibold text-emerald-400 uppercase">
                  v{diffData.v2.version_number} Active Governance Memo
                </span>
                <p className="mt-1 text-xs text-ink-secondary">
                  Resolution Ref:{" "}
                  <span className="font-mono text-emerald-300">
                    {diffData.v2.shariah_resolution}
                  </span>
                </p>
                <p className="mt-0.5 text-xs text-ink-secondary">
                  Created by: {diffData.v2.created_by}
                </p>
                <p className="mt-0.5 text-xs text-ink-muted">
                  Timestamp: {diffData.v2.created_at ?? "Latest Calibration"}
                </p>
              </div>
            </div>
          </Card>
        </>
      )}

      {/* Modal for Creating New Calibration Version */}
      {isModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm">
          <div className="w-full max-w-xl rounded-xl border border-white/10 bg-navy-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/8 pb-3">
              <div>
                <h3 className="text-base font-semibold text-ink-primary">
                  Draft New Pool Calibration Version
                </h3>
                <p className="text-xs text-ink-secondary">
                  Calibrate PSR, reserve caps, and weightages with Shariah quorum notes.
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

            <form onSubmit={handleCreateVersionSubmit} className="mt-4 space-y-4 text-xs">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary">Mudarib Share (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={newVersionForm.psr?.mudarib_share_pct ?? 48.0}
                    onChange={(e) =>
                      setNewVersionForm({
                        ...newVersionForm,
                        psr: {
                          ...newVersionForm.psr!,
                          mudarib_share_pct: parseFloat(e.target.value),
                          rabbul_maal_share_pct: 100.0 - parseFloat(e.target.value),
                        },
                      })
                    }
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                    required
                  />
                </div>

                <div>
                  <label className="block text-ink-secondary">Rab-ul-Maal Share (%)</label>
                  <input
                    type="number"
                    value={newVersionForm.psr?.rabbul_maal_share_pct ?? 52.0}
                    disabled
                    className="mt-1 w-full rounded border border-white/5 bg-navy-950/50 px-2.5 py-1.5 text-ink-muted"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary">PER Ceiling (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={newVersionForm.reserve_policy?.per_ceiling_pct ?? 2.5}
                    onChange={(e) =>
                      setNewVersionForm({
                        ...newVersionForm,
                        reserve_policy: {
                          ...newVersionForm.reserve_policy!,
                          per_ceiling_pct: parseFloat(e.target.value),
                        },
                      })
                    }
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                    required
                  />
                </div>

                <div>
                  <label className="block text-ink-secondary">IRR Ceiling (%)</label>
                  <input
                    type="number"
                    step="0.1"
                    value={newVersionForm.reserve_policy?.irr_ceiling_pct ?? 1.0}
                    onChange={(e) =>
                      setNewVersionForm({
                        ...newVersionForm,
                        reserve_policy: {
                          ...newVersionForm.reserve_policy!,
                          irr_ceiling_pct: parseFloat(e.target.value),
                        },
                      })
                    }
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                    required
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-ink-secondary">Benchmark Spread (bps)</label>
                  <input
                    type="number"
                    value={newVersionForm.benchmarks?.spread_bps ?? 75}
                    onChange={(e) =>
                      setNewVersionForm({
                        ...newVersionForm,
                        benchmarks: {
                          ...newVersionForm.benchmarks!,
                          spread_bps: parseInt(e.target.value),
                        },
                      })
                    }
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                  />
                </div>

                <div>
                  <label className="block text-ink-secondary">Target Indicative Yield (%)</label>
                  <input
                    type="number"
                    step="0.05"
                    value={newVersionForm.benchmarks?.target_yield_pct ?? 18.25}
                    onChange={(e) =>
                      setNewVersionForm({
                        ...newVersionForm,
                        benchmarks: {
                          ...newVersionForm.benchmarks!,
                          target_yield_pct: parseFloat(e.target.value),
                        },
                      })
                    }
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                  />
                </div>
              </div>

              <div>
                <label className="block text-ink-secondary">
                  Shariah Resolution / Fatwa Ref
                </label>
                <input
                  type="text"
                  value={newVersionForm.shariah_resolution_code ?? ""}
                  onChange={(e) =>
                    setNewVersionForm({
                      ...newVersionForm,
                      shariah_resolution_code: e.target.value,
                    })
                  }
                  className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                  placeholder="e.g. SB-RES-2026-Q4-01"
                  required
                />
              </div>

              <div>
                <label className="block text-ink-secondary">Change Rationale</label>
                <textarea
                  rows={2}
                  value={newVersionForm.change_rationale ?? ""}
                  onChange={(e) =>
                    setNewVersionForm({
                      ...newVersionForm,
                      change_rationale: e.target.value,
                    })
                  }
                  className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-2.5 py-1.5 text-ink-primary"
                  placeholder="Explain reason for calibration (e.g. SBP rate cut, depositor yield competition)..."
                  required
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
                  {isSubmitting ? (
                    <Spinner className="h-4 w-4" />
                  ) : (
                    "Attest & Commit Version"
                  )}
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
