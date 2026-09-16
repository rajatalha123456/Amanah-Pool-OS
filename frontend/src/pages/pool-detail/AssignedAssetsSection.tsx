import { useEffect, useState } from "react"
import { Card } from "../../components/Card"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { Table, type TableColumn } from "../../components/Table"
import { fetchAssetAssignments, fetchAssets, unassignAsset } from "../../api/assets"
import { extractErrorMessage } from "../../api/errors"
import { AssignAssetModal } from "./AssignAssetModal"
import type { Asset, AssetAssignment } from "../../types"

export function AssignedAssetsSection({ poolId }: { poolId: string }) {
  const [assignments, setAssignments] = useState<AssetAssignment[]>([])
  const [assetsById, setAssetsById] = useState<Record<string, Asset>>({})
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [unassigningId, setUnassigningId] = useState<string | null>(null)
  const [actionError, setActionError] = useState("")

  function loadData() {
    setIsLoading(true)
    Promise.all([fetchAssetAssignments(poolId), fetchAssets()])
      .then(([assignmentData, assetData]) => {
        setAssignments(assignmentData)
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
        <button
          type="button"
          onClick={() => handleUnassign(assignment.id)}
          disabled={unassigningId === assignment.id}
          className="text-sm font-medium text-red-400 hover:text-red-300 disabled:opacity-50"
        >
          {unassigningId === assignment.id ? "Unassigning..." : "Unassign"}
        </button>
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
