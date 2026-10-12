import { apiClient } from "./axios"
import type { AIMetricsRow, AIRecommendation } from "../types"

export async function fetchAIRecommendations(disposition?: string): Promise<AIRecommendation[]> {
  const response = await apiClient.get<AIRecommendation[]>("ai/recommendations/", {
    params: disposition ? { disposition } : {},
  })
  return response.data
}

export async function fetchAIMetrics(): Promise<AIMetricsRow[]> {
  return (await apiClient.get<AIMetricsRow[]>("ai/recommendations/metrics/")).data
}

export async function disposeAIRecommendation(
  id: string,
  disposition: "accepted" | "rejected" | "overridden",
  note: string,
): Promise<AIRecommendation> {
  return (await apiClient.post<AIRecommendation>(`ai/recommendations/${id}/dispose/`, { disposition, note })).data
}
