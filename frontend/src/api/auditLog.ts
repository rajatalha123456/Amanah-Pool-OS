import { apiClient } from "./axios"
import { pageParams, type Page } from "./pagination"
import type { AuditLogEntry } from "../types"

export interface FetchAuditLogParams {
  model_name?: string
  date_from?: string
  date_to?: string
  tenant?: string
}

export async function fetchAuditLogs(params: FetchAuditLogParams = {}, page = 1): Promise<Page<AuditLogEntry>> {
  const response = await apiClient.get<Page<AuditLogEntry>>("core/audit-log/", { params: { ...params, ...pageParams(page) } })
  return response.data
}

export const fetchAuditLog = fetchAuditLogs

export async function exportAuditLogsCsv(params: FetchAuditLogParams = {}): Promise<Blob> {
  const response = await apiClient.get("core/audit-log/export/", {
    params,
    responseType: "blob",
  })
  return response.data
}

export async function downloadAuditLogCsv(params: FetchAuditLogParams = {}): Promise<void> {
  const blob = await exportAuditLogsCsv(params)
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `audit_log_export_${new Date().toISOString().slice(0, 10)}.csv`
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}
