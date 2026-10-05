import { apiClient } from "./axios"
import type { ReconciliationBatch } from "../types"

export interface CreateReconciliationBatchInput {
  pool: string
  reconciliation_date?: string
  batch_date?: string
  source_system?: string
  total_cbs_balance?: string
  total_gl_balance?: string
  notes?: string
}

export async function fetchReconciliationBatches(poolId?: string): Promise<ReconciliationBatch[]> {
  const params: Record<string, string> = {}
  if (poolId) params.pool = poolId
  const response = await apiClient.get<ReconciliationBatch[]>("accounting/reconciliations/", { params })
  return response.data
}

export async function fetchReconciliationBatchDetail(id: string): Promise<ReconciliationBatch> {
  const response = await apiClient.get<ReconciliationBatch>(`accounting/reconciliations/${id}/`)
  return response.data
}

export async function createReconciliationBatch(
  data: CreateReconciliationBatchInput,
): Promise<ReconciliationBatch> {
  const payload = {
    pool: data.pool,
    reconciliation_date: data.reconciliation_date || data.batch_date || new Date().toISOString().split("T")[0],
    source_system: data.source_system || "Core Banking CBS / GL",
    notes: data.notes || "",
  }
  const response = await apiClient.post<ReconciliationBatch>("accounting/reconciliations/", payload)
  return response.data
}

export async function autoMatchBatch(id: string): Promise<ReconciliationBatch> {
  const response = await apiClient.post<ReconciliationBatch>(`accounting/reconciliations/${id}/auto-match/`)
  return response.data
}

export async function clearVariance(
  batchId: string,
  itemId?: string,
  reason?: string,
): Promise<ReconciliationBatch> {
  const response = await apiClient.post<ReconciliationBatch>(
    `accounting/reconciliations/${batchId}/clear-variance/`,
    { item_id: itemId, reason, notes: reason },
  )
  return response.data
}
