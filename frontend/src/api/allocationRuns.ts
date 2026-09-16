import { apiClient } from "./axios"
import type { AllocationRun, AllocationRunInput, SimulateAllocationResult } from "../types"

export async function simulateAllocation(data: AllocationRunInput): Promise<SimulateAllocationResult> {
  const response = await apiClient.post<SimulateAllocationResult>(
    "allocation/allocation-runs/simulate/",
    data,
  )
  return response.data
}

export async function createAllocationRun(data: AllocationRunInput): Promise<AllocationRun> {
  const response = await apiClient.post<AllocationRun>("allocation/allocation-runs/", data)
  return response.data
}

export async function fetchAllocationRuns(poolId: string): Promise<AllocationRun[]> {
  const response = await apiClient.get<AllocationRun[]>("allocation/allocation-runs/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function fetchAllocationRunDetail(id: string): Promise<AllocationRun> {
  const response = await apiClient.get<AllocationRun>(`allocation/allocation-runs/${id}/`)
  return response.data
}
