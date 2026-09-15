import { useEffect, useState } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { PageHeader } from "../components/PageHeader"
import { getHealthStatus } from "../api/health"

type ConnectionState = "loading" | "connected" | "error"

export function CommandCenter() {
  const [state, setState] = useState<ConnectionState>("loading")
  const [status, setStatus] = useState<string>("")
  const [errorMessage, setErrorMessage] = useState<string>("")

  useEffect(() => {
    getHealthStatus()
      .then((data) => {
        setStatus(data.status)
        setState("connected")
      })
      .catch((error) => {
        setErrorMessage(
          error instanceof Error ? error.message : "Unknown error",
        )
        setState("error")
      })
  }, [])

  return (
    <div>
      <PageHeader
        title="Executive Command Center"
        subtitle="Enterprise visibility across all pool models"
      />
      <Card title="Backend Connection">
        {state === "loading" && (
          <p className="text-sm text-ink-secondary">Checking backend connection...</p>
        )}
        {state === "connected" && (
          <div className="flex items-center gap-2">
            <Badge variant="emerald">Connected</Badge>
            <span className="text-sm text-ink-secondary">
              GET /health/ responded with status: "{status}"
            </span>
          </div>
        )}
        {state === "error" && (
          <div className="flex items-center gap-2">
            <Badge variant="gold">Disconnected</Badge>
            <span className="text-sm text-ink-secondary">{errorMessage}</span>
          </div>
        )}
      </Card>
    </div>
  )
}
