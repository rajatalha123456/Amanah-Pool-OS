import { apiClient } from "./axios"
import { pageParams, type Page } from "./pagination"

export interface GLExport {
  id: string
  pool: string
  pool_code: string
  date_from: string | null
  date_to: string | null
  row_count: number
  total_debit: string
  total_credit: string
  content_hash: string
  status: "generated" | "confirmed" | "rejected"
  exported_by_name: string | null
  gl_reference: string
  decided_by_name: string | null
  decided_at: string | null
  decision_note: string
  batch_count: number
  created_at: string
}

export interface TrialBalanceLine {
  gl_code: string
  account_name: string
  debit: string
  credit: string
  balance: string
}

export interface TrialBalance {
  pool: string
  as_of: string | null
  lines: TrialBalanceLine[]
  total_debit: string
  total_credit: string
  balanced: boolean
}

export async function fetchGLExports(poolId: string, page = 1): Promise<Page<GLExport>> {
  return (await apiClient.get<Page<GLExport>>("accounting/gl-exports/", { params: { pool: poolId, ...pageParams(page) } })).data
}

export async function fetchPendingBatchCount(poolId: string): Promise<number> {
  return (await apiClient.get<{ pending_batches: number }>("accounting/gl-exports/pending-batches/", { params: { pool: poolId } }))
    .data.pending_batches
}

/** Sends every posted batch of the pool (in the range) that has not gone to the GL yet. */
export async function createGLExport(poolId: string, dateFrom?: string, dateTo?: string): Promise<GLExport> {
  return (
    await apiClient.post<GLExport>("accounting/gl-exports/", {
      pool: poolId,
      date_from: dateFrom || null,
      date_to: dateTo || null,
    })
  ).data
}

export async function confirmGLExport(id: string, glReference: string): Promise<GLExport> {
  return (await apiClient.post<GLExport>(`accounting/gl-exports/${id}/confirm/`, { gl_reference: glReference })).data
}

export async function rejectGLExport(id: string, reason: string): Promise<GLExport> {
  return (await apiClient.post<GLExport>(`accounting/gl-exports/${id}/reject/`, { reason })).data
}

/** The stored file, exactly as it was sent. */
export async function downloadGLExport(item: GLExport): Promise<void> {
  const response = await apiClient.get(`accounting/gl-exports/${item.id}/download/`, { responseType: "blob" })
  const url = URL.createObjectURL(response.data as Blob)
  const link = document.createElement("a")
  link.href = url
  link.download = `gl_export_${item.pool_code}_${item.created_at.slice(0, 10)}.csv`
  link.click()
  URL.revokeObjectURL(url)
}

export async function fetchTrialBalance(poolId: string, asOf?: string): Promise<TrialBalance> {
  return (await apiClient.get<TrialBalance>("accounting/trial-balance/", { params: { pool: poolId, as_of: asOf || undefined } })).data
}
