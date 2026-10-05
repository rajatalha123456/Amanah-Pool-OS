import { useEffect, useState } from "react"
import { Card } from "../../components/Card"
import { Spinner } from "../../components/Spinner"
import { fetchLiquidityForecast } from "../../api/liquidity"
import { extractErrorMessage } from "../../api/errors"
import { LiquidityProjectionChart } from "../../components/charts/LiquidityProjectionChart"
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
    <Card title="Prudential Liquidity & Cash Runway">
      {isLoading ? (
        <div className="flex items-center gap-2 py-6 text-ink-secondary">
          <Spinner className="h-4 w-4" />
          <span className="text-sm">Calculating 30-day liquidity trajectory...</span>
        </div>
      ) : loadError ? (
        <p className="text-sm text-red-400">{loadError}</p>
      ) : !forecast || forecast.insufficient_data ? (
        <div className="rounded-lg border border-dashed border-white/10 bg-navy-900/30 p-6 text-center text-xs text-ink-muted">
          Not enough historical balance points yet to compute 30-day liquidity forecast. Minimum 3 daily cycles required.
        </div>
      ) : (
        <div className="space-y-4">
          <LiquidityProjectionChart
            currentBalance={Number(forecast.current_balance)}
            projectedBalance={Number(forecast.projected_balance)}
            trendPerDay={Number(forecast.trend_per_day)}
            horizonDays={forecast.horizon_days}
            knownOutflows={Number(forecast.known_outflows)}
          />

          <p className="text-xs text-ink-muted">
            SBP Prudential Regulations buffer model: Daily linear balance regression over {forecast.horizon_days} days factoring verified pending settlement outflows.
          </p>
        </div>
      )}
    </Card>
  )
}

