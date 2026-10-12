import { apiClient } from "./axios"

export interface PeriodReportRow {
  pool_code: string
  pool_name: string
  operating_model: string
  contract_type: string
  status: string
  [key: string]: string | number | null | undefined
}

export interface PeriodReport {
  tenant: string
  period_start: string
  period_end: string
  generated_at: string
  content_hash: string
  basis: string
  pools: PeriodReportRow[]
}

export async function fetchPeriodReport(start: string, end: string): Promise<PeriodReport> {
  return (await apiClient.get<PeriodReport>("core/period-report/", { params: { start, end } })).data
}

export async function downloadPeriodReportCsv(start: string, end: string): Promise<Blob> {
  return (await apiClient.get<Blob>("core/period-report/", { params: { start, end, export: "csv" }, responseType: "blob" })).data
}
