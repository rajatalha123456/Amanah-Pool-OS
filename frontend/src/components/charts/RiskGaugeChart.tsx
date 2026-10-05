export interface RiskLimitGauge {
  label: string
  currentValue: number
  thresholdValue: number
  unit: string
  isLowerLimit?: boolean // true if currentValue below threshold is breach
  statusText?: string
}

export interface RiskGaugeChartProps {
  gauges: RiskLimitGauge[]
  title?: string
}

export function RiskGaugeChart({
  gauges,
  title = "Regulatory Exposure & Risk Limit Monitors",
}: RiskGaugeChartProps) {
  return (
    <div className="w-full space-y-4 overflow-hidden rounded-lg border border-white/8 bg-navy-900/50 p-4">
      {title && (
        <div className="flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-secondary truncate">
            {title}
          </h4>
          <span className="text-[11px] text-ink-muted truncate">
            SBP / AAOIFI Prudential Rules
          </span>
        </div>
      )}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 pt-2">
        {gauges.map((gauge) => {
          const isBreached = gauge.isLowerLimit
            ? gauge.currentValue < gauge.thresholdValue
            : gauge.currentValue > gauge.thresholdValue

          const isNearWarning = gauge.isLowerLimit
            ? gauge.currentValue <= gauge.thresholdValue * 1.15
            : gauge.currentValue >= gauge.thresholdValue * 0.85

          const toneColor = isBreached
            ? "rose"
            : isNearWarning
            ? "amber"
            : "emerald"

          const maxScale = Math.max(gauge.thresholdValue * 1.4, gauge.currentValue * 1.15, 1)
          const fillPercent = Math.min(100, Math.max(4, (gauge.currentValue / maxScale) * 100))
          const pinPercent = Math.min(96, Math.max(4, (gauge.thresholdValue / maxScale) * 100))

          return (
            <div
              key={gauge.label}
              className={`rounded-lg border p-3 transition-colors overflow-hidden ${
                isBreached
                  ? "border-rose-500/40 bg-rose-950/20"
                  : isNearWarning
                  ? "border-amber-500/30 bg-amber-950/10"
                  : "border-white/5 bg-navy-950/60"
              }`}
            >
              <div className="flex items-start justify-between gap-2 mb-2">
                <span
                  className="text-xs font-semibold text-ink-primary truncate flex-1 min-w-0"
                  title={gauge.label}
                >
                  {gauge.label}
                </span>
                <span
                  className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wider ${
                    isBreached
                      ? "bg-rose-500/20 text-rose-300"
                      : isNearWarning
                      ? "bg-amber-500/20 text-amber-300"
                      : "bg-emerald-500/20 text-emerald-300"
                  }`}
                >
                  {isBreached ? "BREACH" : isNearWarning ? "WARNING" : "NORMAL"}
                </span>
              </div>

              {/* Progress gauge bar */}
              <div className="relative mb-2.5 mt-1">
                <div className="h-2 w-full rounded-full bg-navy-800 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-500 ${
                      toneColor === "rose"
                        ? "bg-rose-500"
                        : toneColor === "amber"
                        ? "bg-amber-400"
                        : "bg-emerald-400"
                    }`}
                    style={{ width: `${fillPercent}%` }}
                  />
                </div>
                {/* Threshold Marker Pin with bounded styling */}
                <div
                  className="absolute -top-0.5 h-3.5 w-1 -translate-x-1/2 rounded-full bg-white shadow-sm pointer-events-none"
                  style={{ left: `${pinPercent}%` }}
                  title={`Limit: ${gauge.thresholdValue}${gauge.unit}`}
                />
              </div>

              <div className="flex items-center justify-between gap-2 text-xs font-mono">
                <span className="text-ink-secondary truncate">
                  Current:{" "}
                  <strong className="text-ink-primary font-bold">
                    {gauge.currentValue.toFixed(1)}
                    {gauge.unit}
                  </strong>
                </span>
                <span className="text-ink-muted text-[11px] shrink-0">
                  Limit: {gauge.thresholdValue}
                  {gauge.unit}
                </span>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
