import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import { Badge } from "../Badge"
import { Card } from "../Card"
import { apiClient } from "../../api/axios"

interface Alert {
  code: string
  severity: "critical" | "warning"
  title: string
  count: number
  link: string
  detail: string
}

/** What has been left undone for too long. Hidden when there is nothing, and for roles the server does not answer. */
export function ControlAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  useEffect(() => {
    apiClient
      .get<{ alerts: Alert[] }>("core/control-alerts/")
      .then((r) => setAlerts(r.data.alerts))
      .catch(() => setAlerts([]))
  }, [])
  if (alerts.length === 0) return null
  return (
    <Card title="Control alerts">
      <ul className="space-y-2 text-sm">
        {alerts.map((a) => (
          <li key={a.code} className="flex flex-wrap items-center gap-2">
            <Badge variant={a.severity === "critical" ? "navy" : "gold"}>{a.severity}</Badge>
            <Link to={a.link} className="font-medium text-ink-primary hover:text-emerald-400">
              {a.count} · {a.title}
            </Link>
            {a.detail && <span className="text-xs text-ink-secondary">{a.detail}</span>}
          </li>
        ))}
      </ul>
    </Card>
  )
}
