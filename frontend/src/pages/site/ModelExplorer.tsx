import { useState } from "react"
import { MODELS } from "./content"
import { SiteIcon } from "./SiteIcons"

const FLOWS: Record<string, string[]> = {
  bank: ["Daily balances", "Weightage bands", "Profit-sharing ratio", "Mudarib share or Wakalah fee", "PER / IRR reserves", "Statements and journals"],
  investment: ["Subscription at NAV", "Units and capital account", "Valuation and NAV", "Profit by ratio, loss by capital", "Redemption with notice and gate"],
  circle: ["Rules accepted by members", "Verifiable draw", "Contributions", "Eligibility gate", "Dual-approved payout", "Closure and reconciliation"],
}

/** Tabs for the three operating models, each with the path money takes through the platform. */
export function ModelExplorer() {
  const [active, setActive] = useState(MODELS[0].key)
  const model = MODELS.find((m) => m.key === active) ?? MODELS[0]
  const flow = FLOWS[model.key]

  return (
    <div className="mt-14">
      <div role="tablist" aria-label="Operating models" className="inline-flex flex-wrap gap-2 rounded-xl border border-white/10 bg-navy-900/70 p-1.5">
        {MODELS.map((m) => (
          <button
            key={m.key}
            role="tab"
            type="button"
            aria-selected={active === m.key}
            onClick={() => setActive(m.key)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-gold-400 ${
              active === m.key ? "bg-gold-500/15 text-gold-400 shadow-inner" : "text-ink-secondary hover:text-ink-primary"
            }`}
          >
            {m.tag}
          </button>
        ))}
      </div>

      <div key={model.key} role="tabpanel" className="site-rise mt-8 grid gap-10 lg:grid-cols-[0.9fr_1.1fr]" style={{ animationDuration: "0.5s" }} data-testid="model-panel">
        <div>
          <h3 className="font-[family-name:var(--font-display)] text-2xl font-semibold leading-snug text-ink-primary sm:text-3xl">{model.title}</h3>
          <p className="mt-4 text-base leading-relaxed text-ink-secondary">{model.body}</p>
          <ul className="mt-6 space-y-3">
            {model.points.map((p) => (
              <li key={p} className="flex items-start gap-3 text-sm text-ink-secondary">
                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-emerald-500/15 text-emerald-300">
                  <SiteIcon name="check" className="h-3.5 w-3.5" />
                </span>
                {p}
              </li>
            ))}
          </ul>
        </div>

        <div className="site-gold-edge rounded-2xl bg-navy-900/70 p-6 sm:p-8">
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gold-400">The path through the platform</p>
          <ol className="relative mt-6 space-y-0">
            {flow.map((step, i) => (
              <li key={step} className="relative flex items-center gap-4 pb-6 last:pb-0">
                {i < flow.length - 1 && (
                  <svg className="absolute left-[15px] top-8 h-[calc(100%-1rem)] w-px" aria-hidden="true">
                    <line x1="0.5" y1="0" x2="0.5" y2="100%" stroke="#34d399" strokeOpacity="0.55" strokeWidth="1.5" className="site-dash" />
                  </svg>
                )}
                <span className="z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-emerald-500/50 bg-navy-950 text-xs font-semibold text-emerald-300">
                  {i + 1}
                </span>
                <span className="rounded-lg border border-white/8 bg-navy-800/70 px-4 py-2.5 text-sm text-ink-primary">{step}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </div>
  )
}
