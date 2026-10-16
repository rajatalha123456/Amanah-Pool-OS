import { apiClient } from "./axios"
import type { AIModelRegistry } from "../types"

export async function fetchAIModels(): Promise<AIModelRegistry[]> {
  const response = await apiClient.get<AIModelRegistry[]>("ai/models/")
  return response.data
}

export async function toggleAIModel(
  id: number,
  status: AIModelRegistry["status"],
  disabledReason?: string,
): Promise<AIModelRegistry> {
  const response = await apiClient.patch<AIModelRegistry>(`ai/models/${id}/`, {
    status,
    ...(disabledReason ? { disabled_reason: disabledReason } : {}),
  })
  return response.data
}

/** Model inventory (BRD 9): owner, purpose, provenance, validation, retirement and the confidence threshold. */
export async function updateAIModelInventory(id: number, data: Partial<AIModelRegistry>): Promise<AIModelRegistry> {
  const response = await apiClient.patch<AIModelRegistry>(`ai/models/${id}/`, data)
  return response.data
}
