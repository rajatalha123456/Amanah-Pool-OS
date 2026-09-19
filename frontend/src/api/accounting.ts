import { apiClient } from "./axios"
import type { CreateIncomeExpenseEventInput, IncomeExpenseEvent, JournalBatch } from "../types"

export async function fetchJournalBatches(poolId: string): Promise<JournalBatch[]> {
  const response = await apiClient.get<JournalBatch[]>("accounting/journal-batches/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function fetchIncomeExpenseEvents(poolId: string): Promise<IncomeExpenseEvent[]> {
  const response = await apiClient.get<IncomeExpenseEvent[]>("accounting/income-expense-events/", {
    params: { pool: poolId },
  })
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
