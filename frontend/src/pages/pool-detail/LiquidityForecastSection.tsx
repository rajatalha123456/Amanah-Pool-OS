import { useEffect, useState } from "react"
import { Card } from "../../components/Card"
import { Spinner } from "../../components/Spinner"
import { fetchLiquidityForecast } from "../../api/liquidity"
import { extractErrorMessage } from "../../api/errors"
import type { LiquidityForecast } from "../../types"

const HORIZON_DAYS = 30

export function LiquidityForecastSection({ poolId }: { poolId: string }) {
  const [forecast, setForecast] = useState<LiquidityForecast | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState("")

  useEffect(() => {
    setIsLoading(true)
    setLoadError("")
    fetchLiquidityForecast(poolId, HORIZON_DAYS)
      .then(setForecast)
      .catch((error) => setLoadError(extractErrorMessage(error, "Unable to load liquidity forecast.")))
      .finally(() => setIsLoading(false))
  }, [poolId])

  return (
    <Card title="Liquidity Forecast">
      {isLoading ? (
        <div className="flex items-center gap-2 py-4 text-ink-secondary">
          <Spinner className="h-4 w-4" />
          <span className="text-sm">Loading...</span>
        </div>
      ) : loadError ? (
        <p className="text-sm text-red-400">{loadError}</p>
      ) : !forecast || forecast.insufficient_data ? (
        <p className="text-sm text-ink-secondary">Not enough history yet.</p>
      ) : (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-sm text-ink-secondary">Current Balance</span>
            <span className="text-sm font-medium text-ink-primary">{forecast.current_balance}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-ink-secondary">Projected Balance ({forecast.horizon_days} days)</span>
            <span className="text-sm font-medium text-ink-primary">{forecast.projected_balance}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-ink-secondary">Daily Trend</span>
            <span
              className={`flex items-center gap-1 text-sm font-medium ${
                Number(forecast.trend_per_day) >= 0 ? "text-emerald-400" : "text-gold-400"
              }`}
            >
              {Number(forecast.trend_per_day) >= 0 ? "▲" : "▼"} {forecast.trend_per_day}/day
            </span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-sm text-ink-secondary">Known Upcoming Outflows</span>
            <span className="text-sm font-medium text-ink-primary">{forecast.known_outflows}</span>
          </div>
          <p className="pt-1 text-xs text-ink-secondary">
            Simple trend-based projection from the last 30 days of balance history plus known pending
            outflows. Not an ML-based forecast.
          </p>
        </div>
      )}
    </Card>
  )
}
