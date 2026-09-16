import { apiClient } from "./axios"
import type { Pool } from "../types"

export async function fetchPools(): Promise<Pool[]> {
  const response = await apiClient.get<Pool[]>("pools/pools/")
  return response.data
}
