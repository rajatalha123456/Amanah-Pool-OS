import { useState, useId } from "react"

export interface DonutSlice {
  label: string
  value: number
  color: string
  sublabel?: string
}

export interface DonutChartProps {
  data: DonutSlice[]
  title?: string
  centerLabel?: string
  centerValue?: string
  size?: number
  strokeWidth?: number
  showLegend?: boolean
  layout?: "auto" | "stacked" | "side-by-side"
  formatValue?: (val: number) => string
  emptyMessage?: string
}

export function DonutChart({
  data,
  title,
  centerLabel = "Total",
  centerValue,
  size = 150,
  strokeWidth = 20,
  showLegend = true,
  layout = "stacked",
  formatValue = (v) => v.toLocaleString(),
  emptyMessage = "No data available",
}: DonutChartProps) {
  const chartId = useId().replace(/:/g, "-")
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const total = data.reduce((sum, item) => sum + Math.max(0, item.value), 0)

  if (total === 0 || data.length === 0) {
    return (
      <div className="flex h-44 w-full flex-col items-center justify-center rounded-lg border border-dashed border-white/10 bg-navy-900/40 p-4 text-center">
        <p className="text-xs text-ink-muted">{emptyMessage}</p>
      </div>
    )
  }

  const radius = (size - strokeWidth) / 2
  const center = size / 2
  const circumference = 2 * Math.PI * radius

  let accumulatedPercent = 0
  const slices = data.map((item, idx) => {
    const validVal = Math.max(0, item.value)
    const percent = validVal / total
    const strokeDasharray = `${percent * circumference} ${circumference * (1 - percent)}`
    const strokeDashoffset = -(accumulatedPercent * circumference)
    accumulatedPercent += percent

    return {
      ...item,
      percent,
      strokeDasharray,
      strokeDashoffset,
      index: idx,
    }
  })

  const activeSlice = hoveredIndex !== null ? slices[hoveredIndex] : null
  const displayLabel = activeSlice ? activeSlice.label : centerLabel
  const displayValue = activeSlice
    ? `${(activeSlice.percent * 100).toFixed(1)}%`
    : centerValue ?? formatValue(total)
  const displaySubtext = activeSlice ? formatValue(activeSlice.value) : `${slices.length} Categories`

  const isSideBySide = layout === "side-by-side"

  return (
    <div className="flex w-full flex-col space-y-3 overflow-hidden">
      {title && (
        <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-secondary truncate">
          {title}
        </h4>
      )}

      <div
        className={`flex w-full items-center gap-4 ${
          isSideBySide ? "flex-col xl:flex-row xl:items-center xl:justify-between" : "flex-col"
        }`}
      >
        {/* SVG Donut Container */}
        <div className="relative flex shrink-0 items-center justify-center py-1">
          <svg
            width={size}
            height={size}
            viewBox={`0 0 ${size} ${size}`}
            className="shrink-0 transition-transform duration-300"
          >
            {/* Background ring */}
            <circle
              cx={center}
              cy={center}
              r={radius}
              fill="transparent"
              stroke="rgba(255, 255, 255, 0.06)"
              strokeWidth={strokeWidth}
            />

            {/* Dynamic Slices */}
            {slices.map((slice) => {
              const isHovered = hoveredIndex === slice.index
              return (
                <circle
                  key={`${chartId}-${slice.index}`}
                  cx={center}
                  cy={center}
                  r={radius}
                  fill="transparent"
                  stroke={slice.color}
                  strokeWidth={isHovered ? strokeWidth + 4 : strokeWidth}
                  strokeDasharray={slice.strokeDasharray}
                  strokeDashoffset={slice.strokeDashoffset}
                  strokeLinecap="round"
                  transform={`rotate(-90 ${center} ${center})`}
                  className="cursor-pointer transition-all duration-200"
                  style={{
                    filter: isHovered ? `drop-shadow(0 0 6px ${slice.color})` : "none",
                    opacity: hoveredIndex === null || isHovered ? 1 : 0.45,
                  }}
                  onMouseEnter={() => setHoveredIndex(slice.index)}
                  onMouseLeave={() => setHoveredIndex(null)}
                />
              )
            })}
          </svg>

          {/* Center Info Text */}
          <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center p-2">
            <span className="text-[10px] uppercase tracking-wider text-ink-muted truncate max-w-[85px]">
              {displayLabel}
            </span>
            <span className="text-sm font-bold text-ink-primary truncate max-w-[95px]">
              {displayValue}
            </span>
            <span className="text-[9px] text-ink-secondary truncate max-w-[85px]">
              {displaySubtext}
            </span>
          </div>
        </div>

        {/* Legend */}
        {showLegend && (
          <div className="flex w-full min-w-0 flex-col space-y-1.5 pt-1">
            {slices.map((slice) => {
              const isHovered = hoveredIndex === slice.index
              return (
                <div
                  key={slice.label}
                  className={`flex w-full cursor-pointer items-center justify-between gap-2 rounded-md px-2 py-1 text-xs transition-colors ${
                    isHovered ? "bg-white/10" : "hover:bg-white/5"
                  }`}
                  onMouseEnter={() => setHoveredIndex(slice.index)}
                  onMouseLeave={() => setHoveredIndex(null)}
                >
                  <div className="flex min-w-0 items-center gap-2">
                    <span
                      className="h-2 w-2 rounded-full shrink-0"
                      style={{ backgroundColor: slice.color }}
                    />
                    <span className="truncate text-ink-primary font-medium text-xs">
                      {slice.label}
                    </span>
                  </div>
                  <div className="flex shrink-0 items-center gap-2 pl-2">
                    <span className="font-mono text-ink-secondary text-[11px]">
                      {formatValue(slice.value)}
                    </span>
                    <span className="w-11 text-right font-mono font-semibold text-emerald-400 text-[11px]">
                      {(slice.percent * 100).toFixed(1)}%
                    </span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
