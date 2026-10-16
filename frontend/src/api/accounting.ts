import { apiClient } from "./axios"
import { pageParams, type Page } from "./pagination"
import type {
  CreateIncomeExpenseEventInput,
  IncomeExpenseEvent,
  JournalBatch,
  PoolIncomeExpenseSummary,
} from "../types"

export async function fetchJournalBatches(poolId: string, page = 1): Promise<Page<JournalBatch>> {
  const response = await apiClient.get<Page<JournalBatch>>("accounting/journal-batches/", {
    params: { pool: poolId, ...pageParams(page) },
  })
  return response.data
}

export async function fetchIncomeExpenseEvents(poolId?: string, page = 1): Promise<Page<IncomeExpenseEvent>> {
  const response = await apiClient.get<Page<IncomeExpenseEvent>>("accounting/income-expense-events/", {
    params: { ...(poolId ? { pool: poolId } : {}), ...pageParams(page) },
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


/** Realization (BRD 4): the finance checker records the cash received or paid for a posted event. */
export async function settleIncomeExpenseEvent(id: string, settlementReference: string, settledOn: string): Promise<IncomeExpenseEvent> {
  const response = await apiClient.post<IncomeExpenseEvent>(`accounting/income-expense-events/${id}/settle/`, {
    settlement_reference: settlementReference,
    settled_on: settledOn,
  })
  return response.data
}
