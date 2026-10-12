import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Card } from "../Card"
import { fetchRoleDashboard, type RoleDashboard as RoleDashboardData } from "../../api/dashboard"

const fmt = (v: string) => (/^-?\d+(\.\d+)?$/.test(v) ? Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 }) : v)

/** The signed-in role's own dashboard (BRD 13). Every figure comes from recorded data; "-" means there is no source yet. */
export function RoleDashboard() {
  const [data, setData] = useState<RoleDashboardData | null>(null)

  useEffect(() => {
    void fetchRoleDashboard().then(setData)
  }, [])

  if (!data) return null
  return (
    <div className="space-y-4" data-testid="role-dashboard">
      <h2 className="text-sm font-semibold uppercase tracking-wider text-gold-400">{data.audience} dashboard</h2>
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {data.sections.map((section) => (
          <Card key={section.title} title={section.title}>
            <ul className="divide-y divide-white/5">
              {section.metrics.map((m) => {
                const row = (
                  <div className="flex items-baseline justify-between gap-4 py-2 text-sm">
                    <span className="text-ink-secondary">
                      {m.label}
                      {m.detail && <span className="ml-1 text-[11px] text-ink-muted">({m.detail})</span>}
                    </span>
                    <span className={`font-mono font-semibold ${m.tone === "attention" ? "text-gold-400" : "text-ink-primary"}`}>
                      {m.value === null ? "-" : fmt(m.value)}
                    </span>
                  </div>
                )
                return <li key={m.label}>{m.link ? <Link to={m.link} className="block hover:bg-white/[0.03]">{row}</Link> : row}</li>
              })}
            </ul>
          </Card>
        ))}
      </div>
    </div>
  )
}
