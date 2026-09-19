import { apiClient } from "./axios"
import type {
  CreatePurificationEntryInput,
  ExceptionCase,
  PurificationEntry,
} from "../types"

interface FetchExceptionsParams {
  pool?: string
  status?: string
  severity?: string
}

export async function fetchExceptions(params: FetchExceptionsParams = {}): Promise<ExceptionCase[]> {
  const response = await apiClient.get<ExceptionCase[]>("governance/exceptions/", { params })
  return response.data
}

export async function fetchExceptionCase(id: string): Promise<ExceptionCase> {
  const response = await apiClient.get<ExceptionCase>(`governance/exceptions/${id}/`)
  return response.data
}

export async function startInvestigation(id: string, investigationNotes: string): Promise<ExceptionCase> {
  const response = await apiClient.post<ExceptionCase>(`governance/exceptions/${id}/start-investigation/`, {
    investigation_notes: investigationNotes,
  })
  return response.data
}

export async function setTreatmentPlan(id: string, treatmentPlan: string): Promise<ExceptionCase> {
  const response = await apiClient.post<ExceptionCase>(`governance/exceptions/${id}/set-treatment/`, {
    treatment_plan: treatmentPlan,
  })
  return response.data
}

export async function updateExceptionAssignee(id: string, assignedToUserId: number): Promise<ExceptionCase> {
  const response = await apiClient.patch<ExceptionCase>(`governance/exceptions/${id}/`, {
    assigned_to: assignedToUserId,
  })
  return response.data
}

export async function resolveException(id: string, resolutionNotes: string): Promise<ExceptionCase> {
  const response = await apiClient.post<ExceptionCase>(`governance/exceptions/${id}/resolve/`, {
    resolution_notes: resolutionNotes,
  })
  return response.data
}

export async function dismissException(id: string, resolutionNotes: string): Promise<ExceptionCase> {
  const response = await apiClient.post<ExceptionCase>(`governance/exceptions/${id}/dismiss/`, {
    resolution_notes: resolutionNotes,
  })
  return response.data
}

export async function fetchPurificationEntries(poolId?: string): Promise<PurificationEntry[]> {
  const response = await apiClient.get<PurificationEntry[]>("governance/purification-entries/", {
    params: poolId ? { pool: poolId } : {},
  })
  return response.data
}

export async function createPurificationEntry(data: CreatePurificationEntryInput): Promise<PurificationEntry> {
  const response = await apiClient.post<PurificationEntry>("governance/purification-entries/", data)
  return response.data
}

export async function approvePurificationEntry(id: string): Promise<PurificationEntry> {
  const response = await apiClient.post<PurificationEntry>(`governance/purification-entries/${id}/approve/`)
  return response.data
}

export async function markDistributed(
  id: string,
  charityRecipient: string,
  distributedDate: string,
): Promise<PurificationEntry> {
  const response = await apiClient.post<PurificationEntry>(
    `governance/purification-entries/${id}/mark-distributed/`,
    { charity_recipient: charityRecipient, distributed_date: distributedDate },
  )
  return response.data
}
