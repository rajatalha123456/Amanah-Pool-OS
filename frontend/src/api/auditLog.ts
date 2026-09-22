import { apiClient } from "./axios"
import type { AuditLogEntry, AuditLogFilters } from "../types"

export async function fetchAuditLog(filters: AuditLogFilters): Promise<AuditLogEntry[]> {
  const response = await apiClient.get<AuditLogEntry[]>("core/audit-log/", {
    params: filters,
  })
  return response.data
}

export async function downloadAuditLogCsv(filters: AuditLogFilters): Promise<void> {
  const response = await apiClient.get("core/audit-log/export/", {
    params: filters,
    responseType: "blob",
  })
  const url = window.URL.createObjectURL(new Blob([response.data]))
  const link = document.createElement("a")
  link.href = url
  link.setAttribute("download", "audit_log_export.csv")
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
