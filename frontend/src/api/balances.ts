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
