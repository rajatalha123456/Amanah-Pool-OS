import { useMemo, useState } from "react"

const EVENTS = ["Run sealed", "Run approved", "Period locked", "Statements issued", "Report sealed"]

/** A small, non-cryptographic hash (FNV-1a) used only to illustrate chaining; the platform itself uses SHA-256. */
function mini(value: string) {
  let h = 0x811c9dc5
  for (let i = 0; i < value.length; i++) {
    h ^= value.charCodeAt(i)
    h = Math.imul(h, 0x01000193)
  }
  return (h >>> 0).toString(16).padStart(8, "0")
}

function chain(texts: string[]) {
  const out: string[] = []
  texts.forEach((t, i) => out.push(mini(`${i === 0 ? "genesis" : out[i - 1]}|${t}`)))
  return out
}

const ORIGINAL = chain(EVENTS)

/** Edit one record and see every later link break: the idea behind the platform's tamper-evident audit log. */
export function AuditChainDemo() {
  const [edited, setEdited] = useState<number | null>(null)

  const texts = useMemo(() => EVENTS.map((t, i) => (i === edited ? `${t} (altered)` : t)), [edited])
  const current = useMemo(() => chain(texts), [texts])

  return (
    <div className="site-gold-edge rounded-2xl bg-navy-900/80 p-6 backdrop-blur sm:p-8" data-testid="audit-demo">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-gold-400">Try it</p>
          <h3 className="mt-1 text-lg font-semibold text-ink-primary">Change one record. See the chain break.</h3>
          <p className="mt-1 max-w-xl text-sm text-ink-secondary">
            Each entry carries a fingerprint of the one before it. Alter an earlier entry and every later fingerprint stops matching.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setEdited(edited === null ? 2 : null)}
          className="rounded-lg border border-gold-500/50 bg-gold-500/10 px-4 py-2 text-sm font-semibold text-gold-400 transition hover:bg-gold-500/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold-400"
        >
          {edited === null ? "Alter “Period locked”" : "Restore the record"}
        </button>
      </div>

      <ol className="mt-6 grid gap-3 sm:grid-cols-5">
        {EVENTS.map((_, i) => {
          const valid = current[i] === ORIGINAL[i]
          return (
            <li
              key={i}
              className={`relative rounded-xl border p-3.5 text-xs transition-colors duration-500 ${
                valid ? "border-emerald-500/30 bg-emerald-500/5" : "border-red-500/50 bg-red-500/10"
              }`}
            >
              <p className="font-semibold text-ink-primary">{texts[i]}</p>
              <p className="mt-2 text-[10px] uppercase tracking-wider text-ink-muted">Fingerprint</p>
              <p className={`font-mono text-[11px] ${valid ? "text-emerald-300" : "text-red-300"}`}>{current[i]}</p>
              <p className={`mt-2 text-[10px] font-semibold uppercase tracking-wider ${valid ? "text-emerald-400" : "text-red-300"}`}>
                {valid ? "Verified" : "Mismatch"}
              </p>
              {i < EVENTS.length - 1 && (
                <span
                  className={`absolute -right-2.5 top-1/2 z-10 hidden h-px w-2 sm:block ${valid ? "bg-emerald-500/60" : "bg-red-500/60"}`}
                  aria-hidden="true"
                />
              )}
            </li>
          )
        })}
      </ol>
      <p className="mt-4 text-xs text-ink-muted" aria-live="polite">
        {edited === null
          ? "All five entries verify."
          : `Entry ${edited + 1} was altered, so entries ${edited + 1} to ${EVENTS.length} no longer verify.`}{" "}
        The illustration uses a simple fingerprint; the platform uses SHA-256.
      </p>
    </div>
  )
}
