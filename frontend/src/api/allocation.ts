import { apiClient } from "./axios"
import type { CreatePSRInput, CreateWeightageBandInput, PSR, WeightageBand } from "../types"

export async function fetchWeightageBands(poolId: string): Promise<WeightageBand[]> {
  const response = await apiClient.get<WeightageBand[]>("allocation/weightage-bands/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function createWeightageBand(data: CreateWeightageBandInput): Promise<WeightageBand> {
  const response = await apiClient.post<WeightageBand>("allocation/weightage-bands/", data)
  return response.data
}

export async function approveWeightageBand(id: string): Promise<WeightageBand> {
  const response = await apiClient.post<WeightageBand>(`allocation/weightage-bands/${id}/approve/`)
  return response.data
}

export async function fetchPSRSchedules(poolId: string): Promise<PSR[]> {
  const response = await apiClient.get<PSR[]>("allocation/psr-schedules/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function createPSR(data: CreatePSRInput): Promise<PSR> {
  const response = await apiClient.post<PSR>("allocation/psr-schedules/", data)
  return response.data
}

export async function approvePSR(id: string): Promise<PSR> {
  const response = await apiClient.post<PSR>(`allocation/psr-schedules/${id}/approve/`)
  return response.data
}
