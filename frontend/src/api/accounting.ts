import { apiClient } from "./axios"
import type {
  CreateIncomeExpenseEventInput,
  IncomeExpenseEvent,
  JournalBatch,
  PoolIncomeExpenseSummary,
} from "../types"

export async function fetchJournalBatches(poolId: string): Promise<JournalBatch[]> {
  const response = await apiClient.get<JournalBatch[]>("accounting/journal-batches/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function fetchIncomeExpenseEvents(poolId?: string): Promise<IncomeExpenseEvent[]> {
  const response = await apiClient.get<IncomeExpenseEvent[]>("accounting/income-expense-events/", {
    params: poolId ? { pool: poolId } : undefined,
  })
  return response.data
}

export async function fetchPoolIncomeExpenseSummary(poolId: string): Promise<PoolIncomeExpenseSummary> {
  const response = await apiClient.get<PoolIncomeExpenseSummary>(
    "accounting/income-expense-events/pool-summary/",
    { params: { pool: poolId } },
  )
  return response.data
}

export async function createIncomeExpenseEvent(
  data: CreateIncomeExpenseEventInput,
): Promise<IncomeExpenseEvent> {
  const response = await apiClient.post<IncomeExpenseEvent>("accounting/income-expense-events/", data)
  return response.data
}

export async function postIncomeExpenseEvent(id: string): Promise<IncomeExpenseEvent> {
  const response = await apiClient.post<IncomeExpenseEvent>(
    `accounting/income-expense-events/${id}/post/`,
  )
  return response.data
}

export async function quarantineIncomeToCharity(
  id: string,
  reason?: string,
): Promise<IncomeExpenseEvent> {
  const response = await apiClient.post<IncomeExpenseEvent>(
    `accounting/income-expense-events/${id}/quarantine-to-charity/`,
    { reason },
  )
  return response.data
}

export async function reclassifyExpense(
  id: string,
  costClassification: string,
  shariahNote?: string,
): Promise<IncomeExpenseEvent> {
  const response = await apiClient.post<IncomeExpenseEvent>(
    `accounting/income-expense-events/${id}/reclassify/`,
    {
      cost_classification: costClassification,
      shariah_note: shariahNote,
    },
  )
  return response.data
}

export async function scanOverheadLeakage(
  poolId?: string,
): Promise<{
  scanned_count: number
  flagged_leakage_count: number
  status: string
  message: string
}> {
  const response = await apiClient.post(
    "accounting/income-expense-events/scan-overhead-leakage/",
    { pool: poolId },
  )
  return response.data
}
