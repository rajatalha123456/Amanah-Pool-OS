import { useEffect, useState } from "react"
import { Card } from "../../components/Card"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { Table, type TableColumn } from "../../components/Table"
import { useAuth } from "../../api/auth"
import { decideAssetTransfer, fetchAssetAssignments, fetchAssetTransfers, fetchAssets, unassignAsset, type AssetTransferRequest } from "../../api/assets"
import { extractErrorMessage } from "../../api/errors"
import { AssignAssetModal } from "./AssignAssetModal"
import { TransferAssetModal } from "./TransferAssetModal"
import type { Asset, AssetAssignment } from "../../types"

export function AssignedAssetsSection({ poolId }: { poolId: string }) {
  const [assignments, setAssignments] = useState<AssetAssignment[]>([])
  const [assetsById, setAssetsById] = useState<Record<string, Asset>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [unassigningId, setUnassigningId] = useState<string | null>(null)
  const [actionError, setActionError] = useState("")
  const [transferId, setTransferId] = useState<string | null>(null)
  const { user } = useAuth()
  const canDecide = user?.role === "finance_checker" || user?.role === "risk_compliance"
  const [transfers, setTransfers] = useState<AssetTransferRequest[]>([])
  const [notice, setNotice] = useState("")

  function loadData() {
    setIsLoading(true)
    Promise.all([fetchAssetAssignments(poolId), fetchAssets(), fetchAssetTransfers(poolId)])
      .then(([assignmentData, assetData, transferData]) => {
        setAssignments(assignmentData)
        setTransfers(transferData)
        setAssetsById(Object.fromEntries(assetData.map((asset) => [asset.id, asset])))
      })
      .catch(() => setLoadError("Failed to load data"))
      .finally(() => setIsLoading(false))
  }

  useEffect(() => {
    loadData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [poolId])

  async function handleUnassign(id: string) {
    setActionError("")
    setUnassigningId(id)
    try {
      await unassignAsset(id)
      loadData()
    } catch (err) {
      setActionError(extractErrorMessage(err, "Unable to unassign asset."))
    } finally {
      setUnassigningId(null)
    }
  }

  const activeAssignments = assignments.filter((a) => a.unassigned_date === null)

  const columns: TableColumn<AssetAssignment>[] = [
    {
      header: "Reference Code",
      accessor: (assignment) => assetsById[assignment.asset]?.reference_code ?? assignment.asset,
    },
    {
      header: "Asset Type",
      accessor: (assignment) => assetsById[assignment.asset]?.asset_type ?? "—",
    },
    { header: "Assigned Date", accessor: (assignment) => assignment.assigned_date },
    {
      header: "",
      accessor: (assignment) => (
        <div className="flex gap-4">
        <button
          type="button"
          onClick={() => setTransferId(assignment.id)}
          className="text-sm font-medium text-emerald-400 hover:text-emerald-300"
        >
          Transfer
        </button>
        <button
          type="button"
          onClick={() => handleUnassign(assignment.id)}
          disabled={unassigningId === assignment.id}
          className="text-sm font-medium text-red-400 hover:text-red-300 disabled:opacity-50"
        >
          {unassigningId === assignment.id ? "Unassigning..." : "Unassign"}
        </button>
        </div>
      ),
    },
  ]

  return (
    <Card
      title="Assigned Assets"
      className="mb-6"
    >
      <div className="mb-4 flex justify-end">
        <Button variant="primary" onClick={() => setIsModalOpen(true)}>
          + Assign Asset
        </Button>
      </div>

      {actionError && <p className="mb-3 text-sm text-red-400">{actionError}</p>}
      {notice && <p className="mb-3 text-sm text-emerald-300">{notice}</p>}

      {transfers.filter((t) => t.status === "pending").length > 0 && (
        <div className="mb-4 space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-secondary">Transfers awaiting approval</p>
          {transfers
            .filter((t) => t.status === "pending")
            .map((t) => (
              <div key={t.id} className="rounded-lg border border-white/8 bg-navy-900/50 p-3 text-xs">
                <p className="font-semibold text-ink-primary">
                  {t.asset_reference}: {t.from_pool_code} to {t.to_pool_code} from {t.effective_date}, valued at PKR{" "}
                  {Number(t.valuation).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </p>
                <p className="mt-1 text-ink-secondary">
                  Basis: {t.valuation_basis} · reason: {t.reason} · proposed by {t.requested_by_name ?? "—"}
                </p>
                {canDecide && String(t.requested_by) !== String(user?.id) && (
                  <div className="mt-2 flex gap-4">
                    <button
                      type="button"
                      className="text-emerald-400"
                      onClick={() =>
                        void decideAssetTransfer(t.id, "approve")
                          .then(() => {
                            setNotice("Transfer approved and carried out.")
                            loadData()
                          })
                          .catch((err) => setActionError(extractErrorMessage(err, "Unable to approve the transfer.")))
                      }
                    >
                      Approve
                    </button>
                    <button
                      type="button"
                      className="text-red-400"
                      onClick={() => {
                        const reason = window.prompt("Why is the transfer refused?")
                        if (reason)
                          void decideAssetTransfer(t.id, "reject", reason)
                            .then(() => {
                              setNotice("Transfer refused.")
                              loadData()
                            })
                            .catch((err) => setActionError(extractErrorMessage(err, "Unable to refuse the transfer.")))
                      }}
                    >
                      Refuse
                    </button>
                  </div>
                )}
              </div>
            ))}
        </div>
      )}

      {isLoading && (
        <div className="flex items-center gap-2 py-4 text-ink-secondary">
          <Spinner className="h-4 w-4" />
          <span className="text-sm">Loading...</span>
        </div>
      )}

      {loadError && <p className="text-sm text-red-400">{loadError}</p>}

      {!isLoading && !loadError && (
        activeAssignments.length === 0 ? (
          <p className="text-sm text-ink-secondary">No assets assigned to this pool yet.</p>
        ) : (
          <Table columns={columns} data={activeAssignments} keyField={(assignment) => assignment.id} />
        )
      )}

      {transferId && (
        <TransferAssetModal
          assignmentId={transferId}
          fromPoolId={poolId}
          onClose={() => setTransferId(null)}
          onTransferred={() => {
            setTransferId(null)
            setNotice("Transfer proposed. A different finance checker or risk officer approves it before anything moves.")
            loadData()
          }}
        />
      )}

      {isModalOpen && (
        <AssignAssetModal
          poolId={poolId}
          onClose={() => setIsModalOpen(false)}
          onAssigned={() => {
            setIsModalOpen(false)
            loadData()
          }}
        />
      )}
    </Card>
  )
}
