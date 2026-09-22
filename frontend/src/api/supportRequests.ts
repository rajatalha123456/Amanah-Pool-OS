import { apiClient } from "./axios"
import type { CreateSupportRequestInput, SupportRequest } from "../types"

interface FetchSupportRequestsParams {
  pool?: string
  status?: string
  priority?: string
}

export async function fetchSupportRequests(
  params: FetchSupportRequestsParams = {},
): Promise<SupportRequest[]> {
  const response = await apiClient.get<SupportRequest[]>("governance/support-requests/", { params })
  return response.data
}

export async function fetchSupportRequest(id: string): Promise<SupportRequest> {
  const response = await apiClient.get<SupportRequest>(`governance/support-requests/${id}/`)
  return response.data
}

export async function createSupportRequest(data: CreateSupportRequestInput): Promise<SupportRequest> {
  const response = await apiClient.post<SupportRequest>("governance/support-requests/", data)
  return response.data
}

export async function assignSupportRequest(id: string, assignedToUserId: number): Promise<SupportRequest> {
  const response = await apiClient.post<SupportRequest>(`governance/support-requests/${id}/assign/`, {
    assigned_to_user_id: assignedToUserId,
  })
  return response.data
}

export async function resolveSupportRequest(id: string, resolutionNotes: string): Promise<SupportRequest> {
  const response = await apiClient.post<SupportRequest>(`governance/support-requests/${id}/resolve/`, {
    resolution_notes: resolutionNotes,
  })
  return response.data
}
