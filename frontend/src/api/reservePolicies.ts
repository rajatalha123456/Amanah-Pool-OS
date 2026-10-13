import { apiClient } from "./axios"
import type { ReservePolicy } from "../types"

export async function fetchReservePolicies(poolId?: string): Promise<ReservePolicy[]> {
  const params: Record<string, string> = {}
  if (poolId) params.pool = poolId
  const response = await apiClient.get<ReservePolicy[]>("allocation/reserve-policies/", { params })
  return response.data
}

export async function fetchReservePolicyDetail(id: string): Promise<ReservePolicy> {
  const response = await apiClient.get<ReservePolicy>(`allocation/reserve-policies/${id}/`)
  return response.data
}

/** A reserve change is only PROPOSED (HTTP 202); a different finance checker approves it in Governance Config. */
export async function createReservePolicy(
  data: Partial<ReservePolicy> & { change_reason: string },
): Promise<void> {
  await apiClient.post("allocation/reserve-policies/", data)
}

export async function updateReservePolicy(
  id: string,
  data: Partial<ReservePolicy> & { change_reason: string },
): Promise<void> {
  await apiClient.patch(`allocation/reserve-policies/${id}/`, data)
}
