import { useMemo, useState } from "react"
import { SiteIcon } from "./SiteIcons"

const PEOPLE = ["User A", "User B", "User C", "User D"]
const STEPS = [
  { key: "maker", role: "Finance Maker", action: "Prepares the run" },
  { key: "checker", role: "Finance Checker", action: "Checks it independently" },
  { key: "shariah", role: "Shariah reviewer", action: "Reviews conformity" },
  { key: "signatory", role: "Authorized Signatory", action: "Releases it" },
] as const

type Key = (typeof STEPS)[number]["key"]

// The system's own rule: preparer, checker and releaser must be three different people.
const RULES: { a: Key; b: Key; text: string }[] = [
  { a: "maker", b: "checker", text: "The maker cannot check their own run." },
  { a: "maker", b: "signatory", text: "The maker cannot release their own run." },
  { a: "checker", b: "signatory", text: "The checker cannot give the final release." },
]

/** A small, honest model of the rule the platform enforces: try to let one person fill two roles. */
export function CeremonyPlayground() {
  const [who, setWho] = useState<Record<Key, number>>({ maker: 0, checker: 1, shariah: 2, signatory: 3 })
  const [ran, setRan] = useState(false)

  const broken = useMemo(() => RULES.filter((r) => who[r.a] === who[r.b]), [who])
  const released = ran && broken.length === 0

  return (
    <div className="site-gold-edge rounded-2xl bg-navy-900/80 p-6 backdrop-blur sm:p-7" data-testid="playground">
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gold-400">Try the rule</p>
          <h3 className="mt-1 text-lg font-semibold text-ink-primary">Can one person do two steps?</h3>
        </div>
        <span className="rounded-full border border-white/10 px-2.5 py-1 text-[10px] uppercase tracking-widest text-ink-muted">Interactive</span>
      </div>
      <p className="mt-2 text-sm text-ink-secondary">Assign people to the four steps. Give two steps to the same person and watch what happens.</p>

      <div className="mt-5 space-y-3">
        {STEPS.map((s, i) => {
          const conflict = RULES.some((r) => (r.a === s.key || r.b === s.key) && who[r.a] === who[r.b])
          return (
            <div
              key={s.key}
              className={`flex items-center gap-3 rounded-xl border px-4 py-3 transition-colors ${
                conflict ? "border-red-500/50 bg-red-500/10" : "border-white/10 bg-navy-800/60"
              }`}
            >
              <span className="font-[family-name:var(--font-display)] text-lg text-gold-400">{i + 1}</span>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium text-ink-primary">{s.role}</p>
                <p className="truncate text-xs text-ink-secondary">{s.action}</p>
              </div>
              <label className="sr-only" htmlFor={`who-${s.key}`}>
                Person for {s.role}
              </label>
              <select
                id={`who-${s.key}`}
                value={who[s.key]}
                onChange={(e) => {
                  setWho({ ...who, [s.key]: Number(e.target.value) })
                  setRan(false)
                }}
                className="rounded-md border border-white/10 bg-navy-950 px-2.5 py-1.5 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
              >
                {PEOPLE.map((p, idx) => (
                  <option key={p} value={idx}>
                    {p}
                  </option>
                ))}
              </select>
            </div>
          )
        })}
      </div>

      <button
        type="button"
        onClick={() => setRan(true)}
        className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400"
      >
        Release the run <SiteIcon name="arrow" className="h-4 w-4" />
      </button>

      <div className="mt-4 min-h-[3.5rem]" aria-live="polite">
        {ran && broken.length > 0 && (
          <div className="rounded-lg border border-red-500/40 bg-red-500/10 p-3 text-sm text-red-200" data-testid="playground-refused">
            <p className="font-semibold">Refused by the system</p>
            <ul className="mt-1 space-y-0.5 text-xs">
              {broken.map((b) => (
                <li key={b.text}>{b.text}</li>
              ))}
            </ul>
          </div>
        )}
        {released && (
          <div className="rounded-lg border border-emerald-500/40 bg-emerald-500/10 p-3 text-sm text-emerald-200" data-testid="playground-released">
            <p className="font-semibold">Released</p>
            <p className="mt-0.5 text-xs">Four steps, three different people on the controls. Journals are posted and statements generated.</p>
          </div>
        )}
      </div>
    </div>
  )
}
