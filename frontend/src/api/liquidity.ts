import { apiClient } from "./axios"
import type { LiquidityForecast } from "../types"

export async function fetchLiquidityForecast(
  poolId: string,
  horizonDays = 30,
): Promise<LiquidityForecast> {
  const response = await apiClient.get<LiquidityForecast>(
    `pools/pools/${poolId}/liquidity-forecast/`,
    { params: { horizon_days: horizonDays } },
  )
  return response.data
}
