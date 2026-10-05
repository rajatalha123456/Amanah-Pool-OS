import { useState } from "react"

export interface WeightageTierPoint {
  tierName: string
  weightage: number
  funds?: number
  allocatedProfit?: number
}

export interface WeightageCurveChartProps {
  data: WeightageTierPoint[]
  title?: string
  currency?: string
}

export function WeightageCurveChart({
  data,
  title = "Tiered Weightage Curve & Multiplier Distribution",
  currency = "PKR",
}: WeightageCurveChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  if (!data || data.length === 0) {
    return (
      <div className="flex h-40 w-full items-center justify-center rounded-lg border border-dashed border-white/10 bg-navy-900/40 text-xs text-ink-muted">
        No weightage tier data available for this pool.
      </div>
    )
  }

  const maxWeightage = Math.max(...data.map((d) => d.weightage), 1.5)
  const minWeightage = Math.min(...data.map((d) => d.weightage), 0.5)
  const totalFunds = data.reduce((sum, d) => sum + (d.funds ?? 0), 0)

  return (
    <div className="w-full space-y-4 overflow-hidden rounded-lg border border-white/8 bg-navy-900/50 p-4">
      <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-secondary truncate">
            {title}
          </h4>
          <p className="text-[11px] text-ink-muted truncate">
            Participant tier weightage multiplier scaling factor
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-2 pt-1 sm:pt-0">
          <span className="rounded bg-emerald-500/10 px-2 py-0.5 font-mono text-[11px] text-emerald-400 font-semibold border border-emerald-500/20">
            Max: {maxWeightage.toFixed(2)}x
          </span>
          <span className="rounded bg-navy-800 px-2 py-0.5 font-mono text-[11px] text-ink-secondary border border-white/10">
            Min: {minWeightage.toFixed(2)}x
          </span>
        </div>
      </div>

      {/* Stepped Bar & Weightage Multiplier Visual Grid */}
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4 pt-2">
        {data.map((tier, idx) => {
          const isHovered = hoveredIdx === idx
          const ratioPercent = Math.min(100, Math.max(10, (tier.weightage / maxWeightage) * 100))
          const fundsShare =
            totalFunds > 0 && tier.funds !== undefined ? (tier.funds / totalFunds) * 100 : null

          return (
            <div
              key={tier.tierName}
              className={`rounded-lg border p-3 transition-all cursor-pointer overflow-hidden ${
                isHovered
                  ? "border-emerald-500/50 bg-emerald-500/10 shadow-lg shadow-emerald-950/40"
                  : "border-white/5 bg-navy-950/60 hover:border-white/15"
              }`}
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
            >
              <div className="flex items-center justify-between gap-2 text-xs mb-1.5">
                <span
                  className="font-semibold text-ink-primary truncate min-w-0 flex-1"
                  title={tier.tierName}
                >
                  {tier.tierName}
                </span>
                <span className="font-mono text-emerald-400 font-bold text-sm shrink-0">
                  {tier.weightage.toFixed(2)}x
                </span>
              </div>

              {/* Visual Multiplier Bar */}
              <div className="h-2 w-full rounded-full bg-navy-800 overflow-hidden mb-2">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-emerald-500 to-teal-400 transition-all duration-300"
                  style={{ width: `${ratioPercent}%` }}
                />
              </div>

              {tier.funds !== undefined && (
                <div className="flex items-center justify-between gap-2 text-[10px] text-ink-muted border-t border-white/5 pt-1.5 mt-1">
                  <span className="truncate">Funds:</span>
                  <span className="font-mono text-ink-secondary shrink-0">
                    {currency} {(tier.funds / 1e6).toFixed(1)}M
                  </span>
                </div>
              )}

              {fundsShare !== null && (
                <div className="flex items-center justify-between gap-2 text-[10px] text-ink-muted">
                  <span className="truncate">Pool Share:</span>
                  <span className="font-mono text-emerald-300 font-medium shrink-0">
                    {fundsShare.toFixed(1)}%
                  </span>
                </div>
              )}

              {tier.allocatedProfit !== undefined && (
                <div className="flex items-center justify-between gap-2 text-[10px] text-ink-muted pt-1">
                  <span className="truncate">Allocated:</span>
                  <span className="font-mono text-gold-400 font-semibold shrink-0">
                    {currency} {tier.allocatedProfit.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </span>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
