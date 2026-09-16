import { apiClient } from "./axios"
import type { Asset, AssetAssignment, AssignAssetInput, CreateAssetInput } from "../types"

export async function fetchAssets(): Promise<Asset[]> {
  const response = await apiClient.get<Asset[]>("pools/assets/")
  return response.data
}

export async function createAsset(data: CreateAssetInput): Promise<Asset> {
  const response = await apiClient.post<Asset>("pools/assets/", data)
  return response.data
}

export async function fetchAssetAssignments(poolId: string): Promise<AssetAssignment[]> {
  const response = await apiClient.get<AssetAssignment[]>("pools/asset-assignments/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function assignAsset(data: AssignAssetInput): Promise<AssetAssignment> {
  const response = await apiClient.post<AssetAssignment>("pools/asset-assignments/", data)
  return response.data
}

export async function unassignAsset(id: string): Promise<AssetAssignment> {
  const response = await apiClient.post<AssetAssignment>(`pools/asset-assignments/${id}/unassign/`)
  return response.data
}
