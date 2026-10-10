import { apiClient } from "./axios"
import type { BalanceImportBatch, BalanceImportInput, BalanceImportResult, DailyBalance } from "../types"

export async function importBalances(data: BalanceImportInput): Promise<BalanceImportResult> {
  const response = await apiClient.post<BalanceImportResult>("pools/balance-imports/", data)
  return response.data
}

export async function fetchImportHistory(poolId: string): Promise<BalanceImportBatch[]> {
  const response = await apiClient.get<BalanceImportBatch[]>("pools/balance-imports/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function fetchDailyBalances(poolId: string, valueDate: string): Promise<DailyBalance[]> {
  const response = await apiClient.get<DailyBalance[]>("pools/daily-balances/", {
    params: { pool: poolId, value_date: valueDate },
  })
  return response.data
}

export interface CbsRecord {
  account_no: string
  title: string
  participant_class: string
  ledger_balance: number
  uncleared_float: number
  available_balance: number
  currency: string
  branch_code: string
  status: "SETTLED" | "FLOAT_HOLD" | "DISCREPANCY"
  discrepancy_note?: string
}

export interface CbsSftpDaemonResponse {
  success: boolean
  status: "BALANCED" | "EXCEPTION" | "CHECKSUM_ERROR"
  message: string
  cbs_vendor: string
  file_name: string
  sftp_remote_path: string
  computed_sha256: string
  sidecar_sha256: string
  sftp_logs: string[]
  summary?: {
    total_records: number
    matched_records: number
    exception_count: number
    total_ledger: number
    total_float: number
    total_available: number
  }
  records: CbsRecord[]
  batch?: {
    id: string
    status: string
    value_date: string
    created_at: string
  }
}

export interface CbsSftpDaemonRequest {
  pool_id: string
  value_date: string
  cbs_vendor?: string
  scenario?: "clean" | "float_discrepancy" | "checksum_mismatch"
}

export async function triggerCbsSftpDaemon(data: CbsSftpDaemonRequest): Promise<CbsSftpDaemonResponse> {
  const response = await apiClient.post<CbsSftpDaemonResponse>("pools/balance-imports/cbs-sftp-daemon/", data)
  return response.data
}
