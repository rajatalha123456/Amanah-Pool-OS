import { apiClient } from "./axios"
import type { AllocationRun, AllocationRunInput, SimulateAllocationResult, DepositorStatement } from "../types"

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

export async function submitRunForChecking(id: string): Promise<AllocationRun> {
  const response = await apiClient.post<AllocationRun>(
    `allocation/allocation-runs/${id}/submit-for-checking/`,
  )
  return response.data
}

export async function approveRun(id: string): Promise<AllocationRun> {
  const response = await apiClient.post<AllocationRun>(
    `allocation/allocation-runs/${id}/approve/`,
  )
  return response.data
}

export async function rejectRun(id: string, reason: string): Promise<AllocationRun> {
  const response = await apiClient.post<AllocationRun>(
    `allocation/allocation-runs/${id}/reject/`,
    { rejection_reason: reason },
  )
  return response.data
}

export async function generateStatements(id: string): Promise<DepositorStatement[]> {
  const response = await apiClient.post<DepositorStatement[]>(
    `allocation/allocation-runs/${id}/generate-statements/`,
  )
  return response.data
}

export async function fetchStatements(id: string): Promise<DepositorStatement[]> {
  const response = await apiClient.get<DepositorStatement[]>(
    `allocation/allocation-runs/${id}/statements/`,
  )
  return response.data
}
