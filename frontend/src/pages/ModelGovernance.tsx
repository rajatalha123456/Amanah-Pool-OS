import { useEffect, useState } from "react"
import { useAuth } from "../api/auth"
import { fetchAIModels, toggleAIModel } from "../api/aiModels"
import { extractErrorMessage } from "../api/errors"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import type { AIModelRegistry, BadgeVariant } from "../types"

const STATUS_BADGE: Record<AIModelRegistry["status"], BadgeVariant> = {
  active: "emerald",
  disabled: "navy",
}

export function ModelGovernance() {
  const { user } = useAuth()
  const canToggle = user?.role === "platform_super_admin"
  const [models, setModels] = useState<AIModelRegistry[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState("")
  const [pendingId, setPendingId] = useState<number | null>(null)

  useEffect(() => {
    fetchAIModels()
      .then(setModels)
      .catch((err) => setError(extractErrorMessage(err, "Unable to load AI models.")))
      .finally(() => setIsLoading(false))
  }, [])

  async function handleToggle(model: AIModelRegistry) {
    const nextStatus = model.status === "active" ? "disabled" : "active"
    const reason = nextStatus === "disabled" ? window.prompt("Reason for disabling this AI model:") : undefined
    if (nextStatus === "disabled" && reason === null) return

    setPendingId(model.id)
    setError("")
    try {
      const updated = await toggleAIModel(model.id, nextStatus, reason ?? undefined)
      setModels((current) => current.map((item) => (item.id === updated.id ? updated : item)))
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to update AI model status."))
    } finally {
      setPendingId(null)
    }
  }

  const columns: TableColumn<AIModelRegistry>[] = [
    { header: "Model", accessor: (model) => model.model_name },
    { header: "Version", accessor: (model) => model.version },
    {
      header: "Status",
      accessor: (model) => <Badge variant={STATUS_BADGE[model.status]}>{model.status}</Badge>,
    },
    {
      header: "Control",
      accessor: (model) =>
        canToggle ? (
          <Button
            variant={model.status === "active" ? "outline" : "primary"}
            disabled={pendingId === model.id}
            onClick={() => handleToggle(model)}
          >
            {pendingId === model.id ? <Spinner className="h-4 w-4" /> : model.status === "active" ? "Disable" : "Enable"}
          </Button>
        ) : null,
    },
  ]

  if (isLoading) {
    return <div className="flex items-center gap-2 py-12 text-ink-secondary"><Spinner className="h-5 w-5" /><span className="text-sm">Loading AI models...</span></div>
  }

  return (
    <div className="space-y-4">
      {error && <p className="text-sm text-red-400">{error}</p>}
      <Card>
        {models.length === 0 ? (
          <p className="text-sm text-ink-secondary">No AI models registered.</p>
        ) : (
          <Table columns={columns} data={models} keyField={(model) => model.id} />
        )}
      </Card>
    </div>
  )
}