import { SiteIcon } from "./SiteIcons"

const STEPS = [
  { who: "Finance Maker", what: "Prepared from posted events", done: true },
  { who: "Finance Checker", what: "Independent check and seal verified", done: true },
  { who: "Shariah Board", what: "Conformity reviewed", done: true },
  { who: "Authorized Signatory", what: "Final release within limit", done: false },
]

/** A diagram of the release ceremony: illustrative of the workflow, not of any real run or figure. */
export function HeroVisual() {
  return (
    <div className="relative mx-auto w-full max-w-md" aria-hidden="true">
      <div className="site-glow absolute -inset-10 -z-10 rounded-full bg-emerald-500/10 blur-3xl" />
      <div className="site-glow absolute -right-6 -top-8 -z-10 h-40 w-40 rounded-full bg-gold-500/10 blur-3xl" />

      <div className="site-float rounded-2xl border border-white/10 bg-navy-900/80 p-5 shadow-2xl shadow-black/40 backdrop-blur">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] font-semibold uppercase tracking-[0.2em] text-gold-400">Release ceremony</p>
            <p className="mt-1 text-sm font-semibold text-ink-primary">Period profit allocation</p>
          </div>
          <span className="rounded-full border border-emerald-500/30 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold text-emerald-300">
            Sealed
          </span>
        </div>

        <ol className="relative mt-5 space-y-4">
          <span className="site-line absolute left-[15px] top-3 h-[calc(100%-1.5rem)] w-px bg-gradient-to-b from-emerald-500/70 via-emerald-500/30 to-white/10" />
          {STEPS.map((s) => (
            <li key={s.who} className="relative flex items-start gap-3">
              <span
                className={`z-10 mt-0.5 flex h-[30px] w-[30px] shrink-0 items-center justify-center rounded-full border ${
                  s.done
                    ? "border-emerald-500/60 bg-emerald-950 text-emerald-300"
                    : "border-gold-500/50 bg-navy-900 text-gold-400"
                }`}
              >
                <SiteIcon name={s.done ? "check" : "lock"} className="h-4 w-4" />
              </span>
              <div>
                <p className="text-sm font-medium text-ink-primary">{s.who}</p>
                <p className="text-xs text-ink-secondary">{s.what}</p>
              </div>
            </li>
          ))}
        </ol>

        <div className="mt-5 flex items-center gap-2 rounded-lg border border-white/8 bg-navy-950/60 px-3 py-2 text-[11px] text-ink-secondary">
          <SiteIcon name="chain" className="h-4 w-4 text-gold-400" />
          <span>Inputs, rules and result are hashed into the run</span>
        </div>
      </div>

      <div className="site-float-slow absolute -bottom-12 -left-10 hidden rounded-xl border border-white/10 bg-navy-800/90 px-4 py-3 shadow-xl backdrop-blur sm:block">
        <p className="text-[10px] uppercase tracking-widest text-ink-muted">Rule</p>
        <p className="text-sm font-semibold text-ink-primary">Maker ≠ Checker ≠ Signatory</p>
      </div>
    </div>
  )
}
