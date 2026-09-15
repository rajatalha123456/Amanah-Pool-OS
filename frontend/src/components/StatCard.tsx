interface StatCardProps {
  label: string
  value: string
  delta?: string
  deltaTone?: "positive" | "negative" | "neutral"
}

const toneClasses: Record<NonNullable<StatCardProps["deltaTone"]>, string> = {
  positive: "text-emerald-400",
  negative: "text-red-400",
  neutral: "text-ink-secondary",
}

export function StatCard({ label, value, delta, deltaTone = "positive" }: StatCardProps) {
  return (
    <div className="rounded-xl border border-white/8 bg-navy-900 p-5">
      <p className="text-xs font-semibold tracking-wide text-ink-secondary uppercase">
        {label}
      </p>
      <p className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-semibold text-ink-primary">{value}</span>
        {delta && (
          <span className={`text-sm font-medium ${toneClasses[deltaTone]}`}>{delta}</span>
        )}
      </p>
    </div>
  )
}
