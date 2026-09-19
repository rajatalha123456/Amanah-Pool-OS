import { apiClient } from "./axios"
import type {
  CreateRelatedPartyTransactionInput,
  RelatedPartyReviewInput,
  RelatedPartyTransaction,
} from "../types"

export async function fetchRelatedPartyTransactions(poolId?: string): Promise<RelatedPartyTransaction[]> {
  const response = await apiClient.get<RelatedPartyTransaction[]>("governance/related-party-transactions/", {
    params: poolId ? { pool: poolId } : undefined,
  })
  return response.data
}

export async function createRelatedPartyTransaction(
  data: CreateRelatedPartyTransactionInput,
): Promise<RelatedPartyTransaction> {
  const response = await apiClient.post<RelatedPartyTransaction>(
    "governance/related-party-transactions/",
    data,
  )
  return response.data
}

export async function reviewRelatedPartyTransaction(
  id: string,
  data: RelatedPartyReviewInput,
): Promise<RelatedPartyTransaction> {
  const response = await apiClient.post<RelatedPartyTransaction>(
    `governance/related-party-transactions/${id}/review/`,
    data,
  )
  return response.data
}