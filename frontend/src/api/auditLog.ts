import { apiClient } from "./axios"
import type { AuditLogEntry } from "../types"

export interface FetchAuditLogParams {
  model_name?: string
  date_from?: string
  date_to?: string
  tenant?: string
}

export async function fetchAuditLogs(params: FetchAuditLogParams = {}): Promise<AuditLogEntry[]> {
  const response = await apiClient.get<AuditLogEntry[]>("core/audit-log/", { params })
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
