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

export async function createReservePolicy(
  data: Partial<ReservePolicy>,
): Promise<ReservePolicy> {
  const response = await apiClient.post<ReservePolicy>("allocation/reserve-policies/", data)
  return response.data
}

export async function updateReservePolicy(
  id: string,
  data: Partial<ReservePolicy>,
): Promise<ReservePolicy> {
  const response = await apiClient.patch<ReservePolicy>(`allocation/reserve-policies/${id}/`, data)
  return response.data
}
