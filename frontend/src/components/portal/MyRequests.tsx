import { useCallback, useEffect, useState, type FormEvent } from "react"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Card } from "../Card"
import { extractErrorMessage } from "../../api/errors"
import { fetchMyRequests, raiseRequest, REQUEST_TYPE_LABEL, type MyRequest, type RequestType } from "../../api/portal"

const INPUT =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"

/** Disputes and requests (BRD 13: investor "disputes", member "hardship request"): raised here, worked by staff. */
export function MyRequests({ pools }: { pools: { id: string; label: string }[] }) {
  const [rows, setRows] = useState<MyRequest[]>([])
  const [type, setType] = useState<RequestType>("dispute")
  const [subject, setSubject] = useState("")
  const [description, setDescription] = useState("")
  const [pool, setPool] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")

  const load = useCallback(async () => {
    try {
      setRows(await fetchMyRequests())
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load your requests."))
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function submit(e: FormEvent) {
    e.preventDefault()
    setBusy(true)
    setError("")
    try {
      await raiseRequest({ request_type: type, subject, description, pool })
      setSubject("")
      setDescription("")
      await load()
    } catch (err) {
      setError(extractErrorMessage(err, "Your request could not be sent."))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Card title="My requests and disputes">
      <div className="space-y-4" data-testid="my-requests">
        {error && <p className="text-sm text-red-400">{error}</p>}
        <form onSubmit={submit} className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <select className={INPUT} value={type} onChange={(e) => setType(e.target.value as RequestType)} aria-label="Type of request">
            {(Object.keys(REQUEST_TYPE_LABEL) as RequestType[]).map((k) => (
              <option key={k} value={k}>
                {REQUEST_TYPE_LABEL[k]}
              </option>
            ))}
          </select>
          <select className={INPUT} value={pool} onChange={(e) => setPool(e.target.value)} aria-label="Related pool or circle">
            <option value="">Not about one pool</option>
            {pools.map((p) => (
              <option key={p.id} value={p.id}>
                {p.label}
              </option>
            ))}
          </select>
          <input required className={`${INPUT} sm:col-span-2`} placeholder="Subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
          <textarea required rows={3} className={`${INPUT} sm:col-span-2`} placeholder="Tell us what happened" value={description} onChange={(e) => setDescription(e.target.value)} />
          <div className="sm:col-span-2">
            <Button type="submit" variant="primary" disabled={busy}>
              Send request
            </Button>
          </div>
        </form>

        {rows.length === 0 ? (
          <p className="text-xs text-ink-secondary">You have not raised any request.</p>
        ) : (
          <ul className="space-y-2">
            {rows.map((r) => (
              <li key={r.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-xs">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold text-ink-primary">
                    {REQUEST_TYPE_LABEL[r.request_type] ?? r.request_type}: {r.subject}
                  </span>
                  <Badge variant={r.status === "resolved" || r.status === "closed" ? "emerald" : "gold"}>{r.status.replace("_", " ")}</Badge>
                </div>
                <p className="mt-1 text-ink-secondary">{r.description}</p>
                {r.resolution_notes && <p className="mt-1 text-emerald-300">Answer: {r.resolution_notes}</p>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </Card>
  )
}
