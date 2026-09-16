import { useEffect, useState } from "react"
import { Card } from "../components/Card"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { fetchAssets } from "../api/assets"
import { NewAssetModal } from "./NewAssetModal"
import type { Asset, BadgeVariant } from "../types"

type PageState = "loading" | "loaded" | "error"

const ASSET_STATUS_BADGE: Record<string, BadgeVariant> = {
  available: "emerald",
  assigned: "gold",
  matured: "navy",
  written_off: "navy",
}

function assetStatusBadgeVariant(status: string): BadgeVariant {
  return ASSET_STATUS_BADGE[status] ?? "neutral"
}

export function AssetRegistry() {
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [assets, setAssets] = useState<Asset[]>([])
  const [isModalOpen, setIsModalOpen] = useState(false)

  useEffect(() => {
    fetchAssets()
      .then((data) => {
        setAssets(data)
        setPageState("loaded")
      })
      .catch(() => {
        setPageError("Failed to load data")
        setPageState("error")
      })
  }, [])

  function handleCreated(asset: Asset) {
    setAssets((prev) => [asset, ...prev])
    setIsModalOpen(false)
  }

  const columns: TableColumn<Asset>[] = [
    { header: "Reference Code", accessor: (asset) => asset.reference_code },
    { header: "Asset Type", accessor: (asset) => asset.asset_type },
    { header: "Face Value", accessor: (asset) => asset.face_value },
    {
      header: "Status",
      accessor: (asset) => <Badge variant={assetStatusBadgeVariant(asset.status)}>{asset.status}</Badge>,
    },
  ]

  return (
    <div>
      <PageHeader
        title="Asset Registry"
        subtitle="Murabahah, ijarah and diminishing musharakah assets backing pools"
        actions={
          <Button variant="primary" onClick={() => setIsModalOpen(true)}>
            + New Asset
          </Button>
        }
      />

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading assets...</span>
        </div>
      )}

      {pageState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{pageError}</p>
        </Card>
      )}

      {pageState === "loaded" && (
        <Card>
          {assets.length === 0 ? (
            <p className="text-sm text-ink-secondary">No assets yet.</p>
          ) : (
            <Table columns={columns} data={assets} keyField={(asset) => asset.id} />
          )}
        </Card>
      )}

      {isModalOpen && (
        <NewAssetModal onClose={() => setIsModalOpen(false)} onCreated={handleCreated} />
      )}
    </div>
  )
}
