import { apiClient } from "./axios"
import type { Asset, AssetAssignment, AssetPosition, AssetProvisionEntry, AssignAssetInput, CreateAssetInput } from "../types"

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

export async function transferAsset(
  assignmentId: string,
  data: { to_pool: string; effective_date: string; reason: string },
): Promise<AssetAssignment> {
  return (await apiClient.post<AssetAssignment>(`pools/asset-assignments/${assignmentId}/transfer/`, data)).data
}

export async function fetchProvisions(): Promise<AssetProvisionEntry[]> {
  return (await apiClient.get<AssetProvisionEntry[]>("pools/asset-provisions/")).data
}

export async function requestProvision(data: {
  asset: string
  entry_type: string
  amount: string
  effective_date: string
  reason: string
}): Promise<AssetProvisionEntry> {
  return (await apiClient.post<AssetProvisionEntry>("pools/asset-provisions/", data)).data
}

export async function approveProvision(id: string): Promise<AssetProvisionEntry> {
  return (await apiClient.post<AssetProvisionEntry>(`pools/asset-provisions/${id}/approve/`)).data
}

export async function rejectProvision(id: string, reason: string): Promise<AssetProvisionEntry> {
  return (await apiClient.post<AssetProvisionEntry>(`pools/asset-provisions/${id}/reject/`, { reason })).data
}

export async function fetchAssetPosition(assetId: string): Promise<AssetPosition> {
  return (await apiClient.get<AssetPosition>("pools/asset-provisions/position/", { params: { asset: assetId } })).data
}
