import { useCallback, useEffect, useState } from "react"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { Card } from "../../components/Card"
import { extractErrorMessage } from "../../api/errors"
import { fetchDemoRequests, markDemoRequestHandled, type DemoRequestRow } from "../../api/publicSite"

const INTEREST: Record<string, string> = {
  bank_pool: "Islamic bank pool",
  investment_pool: "Investment pool",
  community_circle: "Community circle",
  other: "Something else",
}

/** Enquiries received through the public website; read and handled by the Platform Super Admin. */
export function DemoRequests() {
  const [rows, setRows] = useState<DemoRequestRow[]>([])
  const [error, setError] = useState("")
  const [loaded, setLoaded] = useState(false)

  const load = useCallback(async () => {
    try {
      setRows(await fetchDemoRequests())
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load website enquiries."))
    } finally {
      setLoaded(true)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  return (
    <Card title="Website enquiries">
      {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
      {loaded && rows.length === 0 && !error && (
        <p className="text-sm text-ink-secondary">No enquiries have come in from the website yet.</p>
      )}
      <div className="space-y-3" data-testid="demo-requests">
        {rows.map((r) => (
          <div key={r.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-4 text-sm">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-semibold text-ink-primary">
                {r.name} <span className="font-normal text-ink-secondary">· {r.organisation}</span>
              </p>
              <div className="flex items-center gap-3">
                <Badge variant={r.handled ? "emerald" : "gold"}>{r.handled ? "Handled" : "New"}</Badge>
                {!r.handled && (
                  <Button size="sm" variant="secondary" onClick={() => void markDemoRequestHandled(r.id).then(load)}>
                    Mark handled
                  </Button>
                )}
              </div>
            </div>
            <p className="mt-1 text-xs text-ink-secondary">
              <a className="text-emerald-400 hover:text-emerald-300" href={`mailto:${r.email}`}>
                {r.email}
              </a>{" "}
              · {INTEREST[r.interest] ?? r.interest} · {r.created_at.slice(0, 10)}
            </p>
            {r.message && <p className="mt-2 whitespace-pre-wrap text-xs text-ink-primary">{r.message}</p>}
          </div>
        ))}
      </div>
    </Card>
  )
}
