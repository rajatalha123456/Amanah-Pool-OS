import { useState, type FormEvent } from "react"
import { extractErrorMessage } from "../../api/errors"
import { submitDemoRequest, type DemoRequestInput } from "../../api/publicSite"

const FIELD =
  "w-full rounded-lg border border-white/10 bg-navy-900/80 px-3.5 py-2.5 text-sm text-ink-primary placeholder:text-ink-muted focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500"

const EMPTY: DemoRequestInput = { name: "", organisation: "", email: "", interest: "bank_pool", message: "", website: "" }

export function DemoRequestForm() {
  const [form, setForm] = useState<DemoRequestInput>(EMPTY)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [sentTo, setSentTo] = useState("")

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError("")
    try {
      await submitDemoRequest(form)
      setSentTo(form.email)
      setForm(EMPTY)
    } catch (err) {
      setError(extractErrorMessage(err, "We could not send your request. Please try again in a little while."))
    } finally {
      setBusy(false)
    }
  }

  if (sentTo) {
    return (
      <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 p-8 text-center" role="status" data-testid="demo-sent">
        <p className="font-[family-name:var(--font-display)] text-2xl text-ink-primary">Thank you.</p>
        <p className="mt-2 text-sm text-ink-secondary">
          Your request is with the team. We will write to <span className="text-ink-primary">{sentTo}</span>.
        </p>
      </div>
    )
  }

  return (
    <form onSubmit={onSubmit} className="relative space-y-4 rounded-2xl border border-white/10 bg-navy-800/60 p-6 backdrop-blur sm:p-8">
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-xs font-medium text-ink-secondary">
          Your name
          <input required maxLength={120} className={`${FIELD} mt-1.5`} value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} autoComplete="name" />
        </label>
        <label className="block text-xs font-medium text-ink-secondary">
          Organisation
          <input required maxLength={160} className={`${FIELD} mt-1.5`} value={form.organisation} onChange={(e) => setForm({ ...form, organisation: e.target.value })} autoComplete="organization" />
        </label>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block text-xs font-medium text-ink-secondary">
          Work email
          <input required type="email" className={`${FIELD} mt-1.5`} value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} autoComplete="email" />
        </label>
        <label className="block text-xs font-medium text-ink-secondary">
          I am interested in
          <select className={`${FIELD} mt-1.5`} value={form.interest} onChange={(e) => setForm({ ...form, interest: e.target.value as DemoRequestInput["interest"] })}>
            <option value="bank_pool">An Islamic bank pool</option>
            <option value="investment_pool">An investment pool</option>
            <option value="community_circle">A community savings circle</option>
            <option value="other">Something else</option>
          </select>
        </label>
      </div>
      <label className="block text-xs font-medium text-ink-secondary">
        Anything we should know? <span className="text-ink-muted">(optional)</span>
        <textarea rows={3} maxLength={2000} className={`${FIELD} mt-1.5`} value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} />
      </label>
      {/* Honeypot: hidden from people and assistive technology; bots tend to fill it. */}
      <div className="absolute -left-[9999px] h-0 w-0 overflow-hidden" aria-hidden="true">
        <label>
          Website
          <input tabIndex={-1} autoComplete="off" value={form.website} onChange={(e) => setForm({ ...form, website: e.target.value })} />
        </label>
      </div>
      {error && (
        <p className="text-sm text-red-400" role="alert">
          {error}
        </p>
      )}
      <button
        type="submit"
        disabled={busy}
        className="inline-flex w-full items-center justify-center rounded-lg bg-emerald-600 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-400 disabled:opacity-60"
      >
        {busy ? "Sending..." : "Request a demo"}
      </button>
      <p className="text-center text-[11px] text-ink-muted">We use your details only to reply to this request.</p>
    </form>
  )
}
