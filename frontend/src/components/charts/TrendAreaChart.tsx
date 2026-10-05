import { useState, useId } from "react"

export interface TrendDataPoint {
  label: string
  value: number
  secondaryValue?: number
  tooltipExtra?: string
}

export interface TrendAreaChartProps {
  data: TrendDataPoint[]
  title?: string
  subtitle?: string
  height?: number
  color?: string
  secondaryColor?: string
  valuePrefix?: string
  valueSuffix?: string
  formatValue?: (val: number) => string
  showGrid?: boolean
  showDots?: boolean
  emptyMessage?: string
  primaryLegend?: string
  secondaryLegend?: string
}

export function TrendAreaChart({
  data,
  title,
  subtitle,
  height = 190,
  color = "#10b981",
  secondaryColor = "#38bdf8",
  valuePrefix = "",
  valueSuffix = "",
  formatValue,
  showGrid = true,
  showDots = true,
  emptyMessage = "No historical points available",
  primaryLegend,
  secondaryLegend,
}: TrendAreaChartProps) {
  const chartId = useId().replace(/:/g, "-")
  const [hoveredIndex, setHoveredIndex] = useState<number | null>(null)

  const defaultFormat = (val: number) =>
    `${valuePrefix}${val.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}${valueSuffix}`
  const formatter = formatValue ?? defaultFormat

  if (!data || data.length < 2) {
    return (
      <div
        className="flex w-full flex-col items-center justify-center rounded-lg border border-dashed border-white/10 bg-navy-900/40 p-6 text-center"
        style={{ height }}
      >
        <p className="text-xs text-ink-muted">{emptyMessage}</p>
      </div>
    )
  }

  // Generous coordinate bounds for viewBox
  const width = 640
  const padLeft = 65
  const padRight = 40
  const padTop = 22
  const padBottom = 30

  const chartW = width - padLeft - padRight
  const chartH = height - padTop - padBottom

  const allValues = data.flatMap((d) =>
    [d.value, d.secondaryValue].filter((v): v is number => v !== undefined),
  )
  const rawMin = Math.min(...allValues)
  const rawMax = Math.max(...allValues)
  const range = rawMax - rawMin || 1
  const min = Math.max(0, rawMin - range * 0.06)
  const max = rawMax + range * 0.08
  const actualRange = max - min || 1

  const getX = (idx: number) => padLeft + (idx / (data.length - 1)) * chartW
  const getY = (val: number) => padTop + chartH - ((val - min) / actualRange) * chartH

  // Build smooth bezier curve
  const buildSmoothPath = (values: number[]) => {
    const points = values.map((val, idx) => ({ x: getX(idx), y: getY(val) }))
    if (points.length === 0) return ""
    let path = `M ${points[0].x.toFixed(1)} ${points[0].y.toFixed(1)}`
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i === 0 ? 0 : i - 1]
      const p1 = points[i]
      const p2 = points[i + 1]
      const p3 = points[i + 2 < points.length ? i + 2 : points.length - 1]
      const cp1x = p1.x + (p2.x - p0.x) / 6
      const cp1y = p1.y + (p2.y - p0.y) / 6
      const cp2x = p2.x - (p3.x - p1.x) / 6
      const cp2y = p2.y - (p3.y - p1.y) / 6
      path += ` C ${cp1x.toFixed(1)} ${cp1y.toFixed(1)}, ${cp2x.toFixed(1)} ${cp2y.toFixed(1)}, ${p2.x.toFixed(1)} ${p2.y.toFixed(1)}`
    }
    return path
  }

  const primaryValues = data.map((d) => d.value)
  const primaryLinePath = buildSmoothPath(primaryValues)
  const primaryAreaPath = `${primaryLinePath} L ${(width - padRight).toFixed(1)} ${(padTop + chartH).toFixed(1)} L ${padLeft.toFixed(1)} ${(padTop + chartH).toFixed(1)} Z`

  const hasSecondary = data.some((d) => d.secondaryValue !== undefined)
  const secondaryValues = hasSecondary ? data.map((d) => d.secondaryValue ?? d.value) : []
  const secondaryLinePath = hasSecondary ? buildSmoothPath(secondaryValues) : ""

  const activePoint = hoveredIndex !== null ? data[hoveredIndex] : null

  // 3 horizontal guideline ticks
  const yTicks = [
    { value: max, y: getY(max) },
    { value: min + actualRange / 2, y: getY(min + actualRange / 2) },
    { value: min, y: getY(min) },
  ]

  return (
    <div className="flex w-full flex-col space-y-2 overflow-hidden">
      {(title || primaryLegend) && (
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0 flex-1">
            {title && (
              <h4 className="text-xs font-semibold uppercase tracking-wider text-ink-secondary truncate">
                {title}
              </h4>
            )}
            {subtitle && <p className="text-[11px] text-ink-muted truncate">{subtitle}</p>}
          </div>

          {(primaryLegend || secondaryLegend) && (
            <div className="flex shrink-0 items-center gap-3 text-xs">
              {primaryLegend && (
                <div className="flex items-center gap-1.5">
                  <span className="h-2 w-3 rounded-full" style={{ backgroundColor: color }} />
                  <span className="text-ink-secondary text-[11px]">{primaryLegend}</span>
                </div>
              )}
              {secondaryLegend && (
                <div className="flex items-center gap-1.5">
                  <span
                    className="h-2 w-3 rounded-full"
                    style={{ backgroundColor: secondaryColor }}
                  />
                  <span className="text-ink-secondary text-[11px]">{secondaryLegend}</span>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* SVG Canvas Container */}
      <div className="relative w-full overflow-hidden rounded-lg border border-white/5 bg-navy-950/40 p-2">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto block"
          style={{ maxHeight: height }}
        >
          <defs>
            <linearGradient id={`grad-${chartId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity="0.32" />
              <stop offset="95%" stopColor={color} stopOpacity="0.01" />
            </linearGradient>
            {hasSecondary && (
              <linearGradient id={`grad-sec-${chartId}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={secondaryColor} stopOpacity="0.20" />
                <stop offset="95%" stopColor={secondaryColor} stopOpacity="0.01" />
              </linearGradient>
            )}
          </defs>

          {/* Grid lines */}
          {showGrid &&
            yTicks.map((tick, i) => (
              <g key={i}>
                <line
                  x1={padLeft}
                  y1={tick.y}
                  x2={width - padRight}
                  y2={tick.y}
                  stroke="rgba(255, 255, 255, 0.08)"
                  strokeDasharray="3 3"
                />
                <text
                  x={padLeft - 8}
                  y={tick.y + 3.5}
                  textAnchor="end"
                  className="fill-slate-400 font-mono text-[9px]"
                >
                  {tick.value >= 1e6
                    ? `${(tick.value / 1e6).toFixed(1)}M`
                    : tick.value >= 1e3
                    ? `${(tick.value / 1e3).toFixed(0)}k`
                    : tick.value.toFixed(1)}
                </text>
              </g>
            ))}

          {/* Secondary Line if provided */}
          {hasSecondary && (
            <path
              d={secondaryLinePath}
              fill="none"
              stroke={secondaryColor}
              strokeWidth="2"
              strokeDasharray="4 3"
              opacity="0.8"
            />
          )}

          {/* Primary Gradient Area */}
          <path d={primaryAreaPath} fill={`url(#grad-${chartId})`} />

          {/* Primary Stroke Line */}
          <path
            d={primaryLinePath}
            fill="none"
            stroke={color}
            strokeWidth="2.5"
            strokeLinecap="round"
          />

          {/* Hover guideline */}
          {hoveredIndex !== null && (
            <line
              x1={getX(hoveredIndex)}
              y1={padTop}
              x2={getX(hoveredIndex)}
              y2={padTop + chartH}
              stroke="rgba(255, 255, 255, 0.3)"
              strokeDasharray="2 2"
            />
          )}

          {/* Data Points */}
          {showDots &&
            data.map((d, idx) => {
              const cx = getX(idx)
              const cy = getY(d.value)
              const isHovered = hoveredIndex === idx
              return (
                <g key={idx} className="cursor-pointer">
                  <circle
                    cx={cx}
                    cy={cy}
                    r={isHovered ? 5.5 : 3.5}
                    fill="#0f172a"
                    stroke={color}
                    strokeWidth={isHovered ? 3 : 2}
                    className="transition-all duration-150"
                  />
                  {/* Invisible hit target for hover */}
                  <rect
                    x={cx - 18}
                    y={padTop}
                    width={36}
                    height={chartH + padBottom}
                    fill="transparent"
                    onMouseEnter={() => setHoveredIndex(idx)}
                    onMouseLeave={() => setHoveredIndex(null)}
                  />
                </g>
              )
            })}

          {/* X-axis labels with edge boundary alignment */}
          {data.map((d, idx) => {
            const x = getX(idx)
            const isFirst = idx === 0
            const isLast = idx === data.length - 1
            const anchor = isFirst ? "start" : isLast ? "end" : "middle"
            const labelX = isFirst ? padLeft : isLast ? width - padRight : x

            return (
              <text
                key={idx}
                x={labelX}
                y={height - 8}
                textAnchor={anchor}
                className="fill-slate-400 font-mono text-[9px]"
              >
                {d.label}
              </text>
            )
          })}
        </svg>

        {/* Hover Tooltip Overlay with boundary clamping */}
        {activePoint && hoveredIndex !== null && (
          <div
            className="pointer-events-none absolute z-20 rounded-md border border-white/10 bg-navy-900/95 px-3 py-1.5 shadow-xl backdrop-blur-md text-xs transition-all duration-75"
            style={{
              left:
                hoveredIndex === 0
                  ? "12px"
                  : hoveredIndex === data.length - 1
                  ? "auto"
                  : `${(getX(hoveredIndex) / width) * 100}%`,
              right: hoveredIndex === data.length - 1 ? "12px" : "auto",
              transform:
                hoveredIndex === 0 || hoveredIndex === data.length - 1
                  ? "none"
                  : "translateX(-50%)",
              top: "12px",
            }}
          >
            <p className="font-semibold text-ink-primary text-xs">{activePoint.label}</p>
            <p className="font-mono text-emerald-400 font-bold text-xs">
              {formatter(activePoint.value)}
            </p>
            {activePoint.secondaryValue !== undefined && (
              <p className="font-mono text-sky-400 text-[11px]">
                Sec: {formatter(activePoint.secondaryValue)}
              </p>
            )}
            {activePoint.tooltipExtra && (
              <p className="text-[10px] text-ink-muted">{activePoint.tooltipExtra}</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
