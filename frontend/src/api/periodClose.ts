import { apiClient } from "./axios"
import type { PeriodCloseChecklist } from "../types"

export interface CreatePeriodCloseInput {
  pool: string
  period_start: string
  period_end: string
  checklist_data?: Record<string, boolean>
  checklist_items?: Record<string, boolean>
  notes?: string
}

export async function fetchPeriodCloseChecklists(poolId?: string): Promise<PeriodCloseChecklist[]> {
  const params: Record<string, string> = {}
  if (poolId) params.pool = poolId
  const response = await apiClient.get<PeriodCloseChecklist[]>("pools/period-closes/", { params })
  return response.data
}

export async function fetchPeriodCloseChecklistDetail(id: string): Promise<PeriodCloseChecklist> {
  const response = await apiClient.get<PeriodCloseChecklist>(`pools/period-closes/${id}/`)
  return response.data
}

export async function createPeriodCloseChecklist(
  data: CreatePeriodCloseInput,
): Promise<PeriodCloseChecklist> {
  const payload = {
    pool: data.pool,
    period_start: data.period_start,
    period_end: data.period_end,
    checklist_data: data.checklist_data || data.checklist_items || {
      reconciled: true,
      shariah_parameters_sealed: true,
      exceptions_cleared: true,
      allocation_signed: true,
      journals_posted: true,
    },
    decision_note: data.notes || "",
  }
  const response = await apiClient.post<PeriodCloseChecklist>("pools/period-closes/", payload)
  return response.data
}

export async function updatePeriodCloseChecklist(
  id: string,
  data: Partial<PeriodCloseChecklist>,
): Promise<PeriodCloseChecklist> {
  const response = await apiClient.patch<PeriodCloseChecklist>(`pools/period-closes/${id}/`, data)
  return response.data
}

export async function certifyPeriodClose(id: string): Promise<PeriodCloseChecklist> {
  const response = await apiClient.post<PeriodCloseChecklist>(`pools/period-closes/${id}/certify/`)
  return response.data
}

export async function lockPeriodClose(id: string): Promise<PeriodCloseChecklist> {
  const response = await apiClient.post<PeriodCloseChecklist>(`pools/period-closes/${id}/lock/`)
  return response.data
}
