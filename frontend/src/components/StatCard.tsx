import { useTranslation } from "react-i18next"
import { translatePhrase } from "../i18n/translate"

interface StatCardProps {
  label: string
  value: string
  delta?: string
  deltaTone?: "positive" | "negative" | "neutral"
  subtext?: string
}

const toneClasses: Record<NonNullable<StatCardProps["deltaTone"]>, string> = {
  positive: "text-emerald-400",
  negative: "text-red-400",
  neutral: "text-ink-secondary",
}

export function StatCard({ label, value, delta, deltaTone = "positive", subtext }: StatCardProps) {
  const { i18n } = useTranslation()
  const isUrdu = !!i18n.language && !i18n.language.startsWith("en") // any non-English language
  const displayLabel = isUrdu ? translatePhrase(i18n.language, label) : label
  const displaySubtext = isUrdu && subtext ? translatePhrase(i18n.language, subtext) : subtext

  return (
    <div className="rounded-xl border border-white/8 bg-navy-900 p-5">
      <p className="text-xs font-semibold tracking-wide text-ink-secondary uppercase">
        {displayLabel}
      </p>
      <p className="mt-2 flex items-baseline gap-2">
        <span className="text-2xl font-semibold text-ink-primary">{value}</span>
        {delta && (
          <span className={`text-sm font-medium ${toneClasses[deltaTone]}`}>{delta}</span>
        )}
      </p>
      {displaySubtext && (
        <p className="mt-1 text-[11px] text-ink-muted">{displaySubtext}</p>
      )}
    </div>
  )
}
