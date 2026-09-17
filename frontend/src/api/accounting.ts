import { apiClient } from "./axios"
import type { JournalBatch } from "../types"

export async function fetchJournalBatches(poolId: string): Promise<JournalBatch[]> {
  const response = await apiClient.get<JournalBatch[]>("accounting/journal-batches/", {
    params: { pool: poolId },
  })
  return response.data
}
