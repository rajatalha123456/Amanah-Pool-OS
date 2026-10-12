const ITEMS = [
  "Mudarabah",
  "Musharakah",
  "Wakalah",
  "Qard",
  "Profit-sharing ratios",
  "PER / IRR reserves",
  "Loss waterfall",
  "Purification",
  "Maker-checker",
  "Shariah quorum",
  "Hash-chained audit",
  "Period close",
]

/** A slow ribbon of the concepts the platform handles. Pauses on hover; static for reduced motion. */
export function Ribbon() {
  const row = [...ITEMS, ...ITEMS]
  return (
    <div className="site-marquee relative overflow-hidden border-y border-white/8 bg-navy-950/70 py-4" aria-label="Concepts the platform handles">
      <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-24 bg-gradient-to-r from-navy-950 to-transparent" />
      <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-24 bg-gradient-to-l from-navy-950 to-transparent" />
      <div className="site-marquee-track" aria-hidden="true">
        {row.map((t, i) => (
          <span key={`${t}-${i}`} className="mx-6 flex items-center gap-6 whitespace-nowrap text-sm font-medium tracking-wide text-ink-secondary">
            {t}
            <span className="h-1 w-1 rotate-45 bg-gold-500/70" />
          </span>
        ))}
      </div>
    </div>
  )
}
