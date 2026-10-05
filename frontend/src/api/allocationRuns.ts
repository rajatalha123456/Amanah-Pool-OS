import { apiClient } from "./axios"
import type { AllocationRun, AllocationRunInput, SimulateAllocationResult, DepositorStatement, RestatementInput } from "../types"

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

export async function fetchAllocationRuns(poolId?: string): Promise<AllocationRun[]> {
  const params: Record<string, string> = {}
  if (poolId) {
    params.pool = poolId
  }
  const response = await apiClient.get<AllocationRun[]>("allocation/allocation-runs/", {
    params,
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

export async function shariahSignOffRun(id: string, note: string): Promise<AllocationRun> {
  const response = await apiClient.post<AllocationRun>(
    `allocation/allocation-runs/${id}/shariah-sign-off/`,
    { note },
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

export async function restateRun(
  id: string,
  data: RestatementInput,
): Promise<{ original_run: AllocationRun; draft_rerun: AllocationRun; message: string }> {
  const response = await apiClient.post<{ original_run: AllocationRun; draft_rerun: AllocationRun; message: string }>(
    `allocation/allocation-runs/${id}/restate/`,
    data,
  )
  return response.data
}
