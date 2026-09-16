import { useEffect, useState, type FormEvent } from "react"
import { Card } from "../../components/Card"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { Table, type TableColumn } from "../../components/Table"
import {
  approveWeightageBand,
  createWeightageBand,
  fetchWeightageBands,
} from "../../api/allocation"
import { extractErrorMessage } from "../../api/errors"
import type { BadgeVariant, WeightageBand } from "../../types"

const STATUS_BADGE: Record<string, BadgeVariant> = {
  draft: "neutral",
  approved: "emerald",
}

export function WeightageBandsSection({ poolId }: { poolId: string }) {
  const [bands, setBands] = useState<WeightageBand[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState("")

  const [participantClass, setParticipantClass] = useState("")
  const [weightage, setWeightage] = useState("")
  const [effectiveFrom, setEffectiveFrom] = useState("")
  const [formError, setFormError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [approvingId, setApprovingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState("")

  function loadBands() {
    setIsLoading(true)
    fetchWeightageBands(poolId)
      .then(setBands)
      .catch(() => setLoadError("Failed to load data"))
      .finally(() => setIsLoading(false))
  }

  useEffect(() => {
    loadBands()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [poolId])

  async function handleAdd(event: FormEvent) {
    event.preventDefault()
    setFormError("")
    setIsSubmitting(true)
    try {
      const band = await createWeightageBand({
        pool: poolId,
        participant_class: participantClass,
        weightage,
        effective_from: effectiveFrom,
      })
      setBands((prev) => [...prev, band])
      setParticipantClass("")
      setWeightage("")
      setEffectiveFrom("")
    } catch (err) {
      setFormError(extractErrorMessage(err, "Unable to create weightage band."))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleApprove(id: string) {
    setActionError("")
    setApprovingId(id)
    try {
      const updated = await approveWeightageBand(id)
      setBands((prev) => prev.map((b) => (b.id === id ? updated : b)))
    } catch (err) {
      setActionError(extractErrorMessage(err, "Unable to approve weightage band."))
    } finally {
      setApprovingId(null)
    }
  }

  const columns: TableColumn<WeightageBand>[] = [
    { header: "Participant Class", accessor: (band) => band.participant_class },
    { header: "Weightage", accessor: (band) => band.weightage },
    { header: "Effective From", accessor: (band) => band.effective_from },
    { header: "Effective To", accessor: (band) => band.effective_to ?? "Open-ended" },
    {
      header: "Status",
      accessor: (band) => <Badge variant={STATUS_BADGE[band.status] ?? "neutral"}>{band.status}</Badge>,
    },
    {
      header: "",
      accessor: (band) =>
        band.status === "draft" ? (
          <button
            type="button"
            onClick={() => handleApprove(band.id)}
            disabled={approvingId === band.id}
            className="text-sm font-medium text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
          >
            {approvingId === band.id ? "Approving..." : "Approve"}
          </button>
        ) : null,
    },
  ]

  return (
    <Card title="Weightage Bands">
      {actionError && <p className="mb-3 text-sm text-red-400">{actionError}</p>}

      {isLoading && (
        <div className="flex items-center gap-2 py-4 text-ink-secondary">
          <Spinner className="h-4 w-4" />
          <span className="text-sm">Loading...</span>
        </div>
      )}

      {loadError && <p className="text-sm text-red-400">{loadError}</p>}

      {!isLoading && !loadError && (
        <>
          {bands.length === 0 ? (
            <p className="mb-4 text-sm text-ink-secondary">No weightage bands yet.</p>
          ) : (
            <div className="mb-4">
              <Table columns={columns} data={bands} keyField={(band) => band.id} />
            </div>
          )}

          <form onSubmit={handleAdd} className="grid grid-cols-1 gap-3 sm:grid-cols-4 sm:items-end">
            <div>
              <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                Participant Class
              </label>
              <input
                type="text"
                value={participantClass}
                onChange={(e) => setParticipantClass(e.target.value)}
                required
                className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                Weightage
              </label>
              <input
                type="number"
                step="0.01"
                value={weightage}
                onChange={(e) => setWeightage(e.target.value)}
                required
                className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                Effective From
              </label>
              <input
                type="date"
                value={effectiveFrom}
                onChange={(e) => setEffectiveFrom(e.target.value)}
                required
                className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <Button type="submit" variant="primary" disabled={isSubmitting}>
              {isSubmitting ? <Spinner className="h-4 w-4" /> : "+ Add Band"}
            </Button>
          </form>

          {formError && <p className="mt-3 text-sm text-red-400">{formError}</p>}
        </>
      )}
    </Card>
  )
}
