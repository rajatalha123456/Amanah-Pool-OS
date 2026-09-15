import { apiClient } from "./axios"
import type { HealthCheckResponse } from "../types"

export async function getHealthStatus(): Promise<HealthCheckResponse> {
  const response = await apiClient.get<HealthCheckResponse>("health/")
  return response.data
}
