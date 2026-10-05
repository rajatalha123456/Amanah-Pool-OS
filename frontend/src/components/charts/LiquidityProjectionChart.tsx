import { useState } from "react"

export interface LiquidityBarPoint {
  dayLabel: string
  projectedBalance: number
  inflowOutflowDelta: number
}

export interface LiquidityProjectionChartProps {
  currentBalance: number
  projectedBalance: number
  trendPerDay: number
  horizonDays?: number
  knownOutflows: number
  minRegulatoryBuffer?: number
  currency?: string
}

export function LiquidityProjectionChart({
  currentBalance,
  projectedBalance,
  trendPerDay,
  horizonDays = 30,
  knownOutflows,
  minRegulatoryBuffer,
  currency = "PKR",
}: LiquidityProjectionChartProps) {
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  // Construct milestone projection points: Day 0, Day 7, Day 14, Day 21, Day 30
  const intervals = [0, 7, 14, 21, horizonDays]
  const data: LiquidityBarPoint[] = intervals.map((day) => {
    const projected = Math.max(
      0,
      currentBalance + trendPerDay * day - (day / horizonDays) * knownOutflows,
    )
    return {
      dayLabel: day === 0 ? "Today" : `Day +${day}`,
      projectedBalance: day === horizonDays ? projectedBalance : projected,
      inflowOutflowDelta: trendPerDay * day,
    }
  })

  const bufferThreshold = minRegulatoryBuffer ?? currentBalance * 0.15
  const maxVal = Math.max(...data.map((d) => d.projectedBalance), bufferThreshold * 1.25, 1)

  // Clean SVG Chart Coordinate System
  const width = 560
  const height = 180
  const padLeft = 50
  const padRight = 30
  const padTop = 28
  const padBottom = 30

  const plotW = width - padLeft - padRight
  const plotH = height - padTop - padBottom

  const getY = (val: number) => padTop + plotH - (Math.max(0, val) / maxVal) * plotH
  const bufferY = getY(bufferThreshold)

  const barCount = data.length
  const barSlotWidth = plotW / barCount
  const barWidth = Math.min(48, barSlotWidth * 0.55)

  return (
    <div className="flex w-full flex-col space-y-4 overflow-hidden rounded-lg border border-white/8 bg-navy-900/50 p-4">
      {/* Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 flex-1">
          <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-secondary truncate">
            30-Day Liquidity Buffer & Cash Projection
          </h4>
          <p className="text-[11px] text-ink-muted truncate">
            Prudential cash runway analysis considering daily trend & scheduled outflows
          </p>
        </div>
        <div className="flex shrink-0 items-center gap-3 text-[11px]">
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            <span className="text-ink-secondary">Cash Buffer</span>
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-2 w-2 rounded-full bg-amber-400" />
            <span className="text-ink-secondary">Regulatory Floor</span>
          </span>
        </div>
      </div>

      {/* SVG Canvas */}
      <div className="relative w-full overflow-hidden rounded-lg border border-white/5 bg-navy-950/40 p-2">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto block"
          style={{ maxHeight: height }}
        >
          {/* Regulatory Floor dashed line across plot area */}
          <line
            x1={padLeft}
            y1={bufferY}
            x2={width - padRight}
            y2={bufferY}
            stroke="#f59e0b"
            strokeWidth="1.5"
            strokeDasharray="4 4"
            opacity="0.8"
          />
          <text
            x={width - padRight}
            y={bufferY - 5}
            textAnchor="end"
            className="fill-amber-400 font-mono text-[9px] font-semibold"
          >
            SBP Floor: {(bufferThreshold / 1e6).toFixed(1)}M
          </text>

          {/* Baseline */}
          <line
            x1={padLeft}
            y1={padTop + plotH}
            x2={width - padRight}
            y2={padTop + plotH}
            stroke="rgba(255, 255, 255, 0.12)"
          />

          {/* Bars */}
          {data.map((item, idx) => {
            const slotCenterX = padLeft + (idx + 0.5) * barSlotWidth
            const barX = slotCenterX - barWidth / 2
            const barY = getY(item.projectedBalance)
            const barH = Math.max(4, padTop + plotH - barY)
            const isBelow = item.projectedBalance < bufferThreshold
            const isHovered = hoveredIdx === idx

            const fillColor = isBelow ? "#f43f5e" : "#10b981"

            return (
              <g
                key={item.dayLabel}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredIdx(idx)}
                onMouseLeave={() => setHoveredIdx(null)}
              >
                {/* Background hover slot */}
                <rect
                  x={slotCenterX - barSlotWidth / 2}
                  y={padTop}
                  width={barSlotWidth}
                  height={plotH}
                  fill={isHovered ? "rgba(255, 255, 255, 0.04)" : "transparent"}
                  rx="4"
                />

                {/* Amount text above bar */}
                <text
                  x={slotCenterX}
                  y={barY - 5}
                  textAnchor="middle"
                  className={`font-mono text-[9px] transition-all ${
                    isHovered
                      ? "fill-white font-bold"
                      : "fill-slate-400"
                  }`}
                >
                  {(item.projectedBalance / 1e6).toFixed(1)}M
                </text>

                {/* Bar */}
                <rect
                  x={barX}
                  y={barY}
                  width={barWidth}
                  height={barH}
                  rx="3"
                  fill={fillColor}
                  opacity={isHovered ? 1 : 0.85}
                  className="transition-all duration-200"
                />

                {/* Day label on X-axis */}
                <text
                  x={slotCenterX}
                  y={height - 10}
                  textAnchor="middle"
                  className={`font-mono text-[9px] ${
                    isHovered ? "fill-white font-bold" : "fill-slate-400"
                  }`}
                >
                  {item.dayLabel}
                </text>
              </g>
            )
          })}
        </svg>
      </div>

      {/* KPI Summary Footer */}
      <div className="grid grid-cols-2 gap-2 sm:grid-cols-4 pt-1 text-xs">
        <div className="min-w-0 rounded bg-white/5 p-2">
          <span className="text-ink-muted text-[10px] block truncate">CURRENT BALANCE</span>
          <span className="font-mono font-semibold text-ink-primary truncate block">
            {currency} {(currentBalance / 1e6).toFixed(2)}M
          </span>
        </div>
        <div className="min-w-0 rounded bg-white/5 p-2">
          <span className="text-ink-muted text-[10px] block truncate">30D PROJECTION</span>
          <span className="font-mono font-semibold text-emerald-400 truncate block">
            {currency} {(projectedBalance / 1e6).toFixed(2)}M
          </span>
        </div>
        <div className="min-w-0 rounded bg-white/5 p-2">
          <span className="text-ink-muted text-[10px] block truncate">SCHEDULED OUTFLOWS</span>
          <span className="font-mono font-semibold text-rose-400 truncate block">
            -{currency} {(knownOutflows / 1e6).toFixed(2)}M
          </span>
        </div>
        <div className="min-w-0 rounded bg-white/5 p-2">
          <span className="text-ink-muted text-[10px] block truncate">DAILY TRAJECTORY</span>
          <span
            className={`font-mono font-semibold truncate block ${
              trendPerDay >= 0 ? "text-emerald-400" : "text-amber-400"
            }`}
          >
            {trendPerDay >= 0 ? "+" : ""}
            {currency} {(trendPerDay / 1e3).toFixed(1)}k / day
          </span>
        </div>
      </div>
    </div>
  )
}
