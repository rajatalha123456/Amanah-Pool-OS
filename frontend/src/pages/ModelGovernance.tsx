import { useEffect, useState } from "react"
import { useAuth } from "../api/auth"
import { fetchAIModels, toggleAIModel, updateAIModelInventory } from "../api/aiModels"
import { Modal } from "../components/Modal"
import { extractErrorMessage } from "../api/errors"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { AIRecommendationLog } from "../components/AIRecommendationLog"
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
  const [editing, setEditing] = useState<AIModelRegistry | null>(null)
  const [draft, setDraft] = useState<Record<string, string>>({})

  function startEdit(model: AIModelRegistry) {
    setEditing(model)
    setDraft({
      owner: model.owner ?? "", purpose: model.purpose ?? "", provenance: model.provenance ?? "",
      validation_status: model.validation_status ?? "not_validated", validated_on: model.validated_on ?? "",
      validation_reference: model.validation_reference ?? "", retirement_date: model.retirement_date ?? "",
      confidence_threshold: String(model.confidence_threshold ?? "0.800"),
    })
  }

  async function saveInventory() {
    if (!editing) return
    try {
      const body: Record<string, string | null> = { ...draft }
      for (const key of ["validated_on", "retirement_date"]) if (!body[key]) body[key] = null
      const updated = await updateAIModelInventory(editing.id, body as Partial<AIModelRegistry>)
      setModels((current) => current.map((item) => (item.id === updated.id ? updated : item)))
      setEditing(null)
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to save the inventory."))
    }
  }

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
    { header: "Owner", accessor: (model) => model.owner || "not set" },
    {
      header: "Validation",
      accessor: (model) => (model.validation_status === "validated" ? `validated ${model.validated_on ?? ""}` : model.validation_status.replace("_", " ")),
    },
    { header: "Retires", accessor: (model) => model.retirement_date ?? "no date" },
    {
      header: "Inventory",
      accessor: (model) => (canToggle ? <Button variant="secondary" onClick={() => startEdit(model)}>Edit</Button> : null),
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
      {editing && (
        <Modal title={`Inventory - ${editing.model_name}`} onClose={() => setEditing(null)}>
          <div className="space-y-3">
            {[["owner", "Owner"], ["purpose", "Purpose"], ["provenance", "Training / source provenance"],
              ["validation_reference", "Validation reference"], ["confidence_threshold", "Confidence threshold (0-1)"]].map(([k, label]) => (
              <label key={k} className="block text-sm">
                {label}
                <input className="mt-1 w-full rounded border border-white/10 bg-transparent p-2" value={draft[k] ?? ""} onChange={(e) => setDraft({ ...draft, [k]: e.target.value })} />
              </label>
            ))}
            <label className="block text-sm">
              Validation status
              <select className="mt-1 w-full rounded border border-white/10 bg-transparent p-2" value={draft.validation_status} onChange={(e) => setDraft({ ...draft, validation_status: e.target.value })}>
                <option value="not_validated">Not validated</option>
                <option value="validated">Validated</option>
                <option value="expired">Validation expired</option>
              </select>
            </label>
            {[["validated_on", "Validated on"], ["retirement_date", "Retirement date"]].map(([k, label]) => (
              <label key={k} className="block text-sm">
                {label}
                <input type="date" className="mt-1 w-full rounded border border-white/10 bg-transparent p-2" value={draft[k] ?? ""} onChange={(e) => setDraft({ ...draft, [k]: e.target.value })} />
              </label>
            ))}
            <div className="flex justify-end gap-2">
              <Button variant="secondary" onClick={() => setEditing(null)}>Cancel</Button>
              <Button variant="primary" onClick={() => void saveInventory()}>Save</Button>
            </div>
          </div>
        </Modal>
      )}
      {/* The recommendation log is tenant data: not shown to the platform administrator. */}
      {!canToggle && <AIRecommendationLog />}
    </div>
  )
}