import { apiClient } from "./axios"
import type { CreateShariahDecisionInput, ShariahDashboard, ShariahDecision } from "../types"

export async function fetchShariahDashboard(poolId?: string): Promise<ShariahDashboard> {
  const response = await apiClient.get<ShariahDashboard>("governance/shariah-dashboard/", {
    params: poolId ? { pool: poolId } : undefined,
  })
  return response.data
}

export async function fetchShariahDecisions(): Promise<ShariahDecision[]> {
  const response = await apiClient.get<ShariahDecision[]>("products/shariah-decisions/")
  return response.data
}

export async function createShariahDecision(data: CreateShariahDecisionInput): Promise<ShariahDecision> {
  const response = await apiClient.post<ShariahDecision>("products/shariah-decisions/", data)
  return response.data
}

export async function approveShariahDecision(id: string): Promise<ShariahDecision> {
  const response = await apiClient.post<ShariahDecision>(`products/shariah-decisions/${id}/approve/`)
  return response.data
}

export async function updateShariahDecision(
  id: string,
  data: Partial<CreateShariahDecisionInput>
): Promise<ShariahDecision> {
  const response = await apiClient.patch<ShariahDecision>(`products/shariah-decisions/${id}/`, data)
  return response.data
}

export async function deleteShariahDecision(id: string): Promise<void> {
  await apiClient.delete(`products/shariah-decisions/${id}/`)
}

export async function castShariahQuorumVote(
  decisionId: string,
  data: {
    scholar_name: string
    scholar_title?: string
    vote: "approve" | "reject"
    fiqh_opinion_notes?: string
  }
): Promise<ShariahDecision> {
  const response = await apiClient.post<ShariahDecision>(
    `products/shariah-decisions/${decisionId}/cast-quorum-vote/`,
    data
  )
  return response.data
}

