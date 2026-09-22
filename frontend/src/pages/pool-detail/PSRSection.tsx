import { useEffect, useState, type FormEvent } from "react"
import { Card } from "../../components/Card"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { Table, type TableColumn } from "../../components/Table"
import { useAuth } from "../../api/auth"
import { approvePSR, createPSR, fetchPSRSchedules } from "../../api/allocation"
import { extractErrorMessage } from "../../api/errors"
import type { BadgeVariant, PSR } from "../../types"

const STATUS_BADGE: Record<string, BadgeVariant> = {
  draft: "neutral",
  approved: "emerald",
}

export function PSRSection({ poolId }: { poolId: string }) {
  const { user } = useAuth()
  const canApprove = user?.role === "shariah_board"
  const [schedules, setSchedules] = useState<PSR[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState("")

  const [depositorShare, setDepositorShare] = useState("")
  const [mudaribShare, setMudaribShare] = useState("")
  const [effectiveFrom, setEffectiveFrom] = useState("")
  const [formError, setFormError] = useState("")
  const [isSubmitting, setIsSubmitting] = useState(false)

  const [approvingId, setApprovingId] = useState<string | null>(null)
  const [actionError, setActionError] = useState("")

  function loadSchedules() {
    setIsLoading(true)
    fetchPSRSchedules(poolId)
      .then(setSchedules)
      .catch(() => setLoadError("Failed to load data"))
      .finally(() => setIsLoading(false))
  }

  useEffect(() => {
    loadSchedules()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [poolId])

  async function handleAdd(event: FormEvent) {
    event.preventDefault()
    setFormError("")
    setIsSubmitting(true)
    try {
      const psr = await createPSR({
        pool: poolId,
        depositor_share: depositorShare,
        mudarib_share: mudaribShare,
        effective_from: effectiveFrom,
      })
      setSchedules((prev) => [...prev, psr])
      setDepositorShare("")
      setMudaribShare("")
      setEffectiveFrom("")
    } catch (err) {
      setFormError(extractErrorMessage(err, "Unable to create PSR."))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleApprove(id: string) {
    setActionError("")
    setApprovingId(id)
    try {
      const updated = await approvePSR(id)
      setSchedules((prev) => prev.map((s) => (s.id === id ? updated : s)))
    } catch (err) {
      setActionError(extractErrorMessage(err, "Unable to approve PSR."))
    } finally {
      setApprovingId(null)
    }
  }

  const columns: TableColumn<PSR>[] = [
    { header: "Depositor Share", accessor: (psr) => `${psr.depositor_share}%` },
    { header: "Mudarib Share", accessor: (psr) => `${psr.mudarib_share}%` },
    { header: "Effective From", accessor: (psr) => psr.effective_from },
    { header: "Effective To", accessor: (psr) => psr.effective_to ?? "Open-ended" },
    {
      header: "Status",
      accessor: (psr) => <Badge variant={STATUS_BADGE[psr.status] ?? "neutral"}>{psr.status}</Badge>,
    },
    {
      header: "",
      accessor: (psr) =>
        canApprove && psr.status === "draft" ? (
          <button
            type="button"
            onClick={() => handleApprove(psr.id)}
            disabled={approvingId === psr.id}
            className="text-sm font-medium text-emerald-400 hover:text-emerald-300 disabled:opacity-50"
          >
            {approvingId === psr.id ? "Approving..." : "Approve"}
          </button>
        ) : null,
    },
  ]

  return (
    <Card title="Profit Sharing Ratio">
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
          {schedules.length === 0 ? (
            <p className="mb-4 text-sm text-ink-secondary">No PSR schedules yet.</p>
          ) : (
            <div className="mb-4">
              <Table columns={columns} data={schedules} keyField={(psr) => psr.id} />
            </div>
          )}

          <form onSubmit={handleAdd} className="grid grid-cols-1 gap-3 sm:grid-cols-4 sm:items-end">
            <div>
              <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                Depositor Share %
              </label>
              <input
                type="number"
                step="0.01"
                value={depositorShare}
                onChange={(e) => setDepositorShare(e.target.value)}
                required
                className="w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase">
                Mudarib Share %
              </label>
              <input
                type="number"
                step="0.01"
                value={mudaribShare}
                onChange={(e) => setMudaribShare(e.target.value)}
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
              {isSubmitting ? <Spinner className="h-4 w-4" /> : "+ Add PSR"}
            </Button>
          </form>

          {formError && <p className="mt-3 text-sm text-red-400">{formError}</p>}
        </>
      )}
    </Card>
  )
}
