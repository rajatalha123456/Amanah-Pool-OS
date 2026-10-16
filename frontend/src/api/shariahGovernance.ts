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
  // The voter is always the logged-in Board member; the server takes the name from the login.
  data: {
    scholar_title?: string
    vote: "approve" | "reject" | "abstain"
    fiqh_opinion_notes: string
  }
): Promise<ShariahDecision> {
  const response = await apiClient.post<ShariahDecision>(
    `products/shariah-decisions/${decisionId}/cast-quorum-vote/`,
    data
  )
  return response.data
}



/** BRD 6.1: a Board member returns the review pack to the Secretariat with what must change. */
export async function returnShariahDecision(decisionId: string, note: string): Promise<ShariahDecision> {
  const response = await apiClient.post<ShariahDecision>(`products/shariah-decisions/${decisionId}/return-for-revision/`, { note })
  return response.data
}

/** The Secretariat sends the revised draft back to the Board; voting starts again. */
export async function resubmitShariahDecision(decisionId: string): Promise<ShariahDecision> {
  const response = await apiClient.post<ShariahDecision>(`products/shariah-decisions/${decisionId}/resubmit/`)
  return response.data
}
