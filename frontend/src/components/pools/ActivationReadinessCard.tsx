import { useCallback, useEffect, useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import { Spinner } from "../Spinner"
import { extractErrorMessage } from "../../api/errors"
import { fetchActivationReadiness, runConfigurationCheck } from "../../api/pools"
import { Button } from "../Button"
import { useAuth } from "../../api/auth"
import type { ActivationReadiness } from "../../types"

/**
 * BR-001: what stands between a pool and activation - approved contract, Shariah decision in force,
 * rule pack, approved economics, accounting mapping and approval matrix. Live from the server.
 */
export function ActivationReadinessCard({ poolId, refreshKey }: { poolId: string; refreshKey?: string }) {
  const [data, setData] = useState<ActivationReadiness | null>(null)
  const [error, setError] = useState("")
  const [checkResult, setCheckResult] = useState("")
  const { user } = useAuth()
  const canCheck = ["product_manager", "pool_manager", "risk_compliance"].includes(user?.role ?? "")

  const load = useCallback(async () => {
    try {
      setData(await fetchActivationReadiness(poolId))
      setError("")
    } catch (err) {
      setError(extractErrorMessage(err, "Unable to load activation readiness."))
    }
  }, [poolId])

  useEffect(() => {
    void load()
  }, [load, refreshKey])

  return (
    <Card
      title="Activation readiness (BR-001)"
      actions={data ? <Badge variant={data.ready ? "emerald" : "gold"}>{data.ready ? "Ready" : "Not ready"}</Badge> : undefined}
    >
      {error && <p className="text-sm text-red-400">{error}</p>}
      {!data && !error && (
        <div className="flex items-center gap-2 text-ink-secondary">
          <Spinner className="h-4 w-4" /> <span className="text-sm">Checking...</span>
        </div>
      )}
      {data && (
        <ul className="space-y-1.5">
          {data.checks.map((check) => (
            <li key={check.key} className="flex items-start gap-2 text-sm">
              <span className={check.passed ? "text-emerald-400" : "text-red-400"}>{check.passed ? "✓" : "✗"}</span>
              <span className="text-ink-primary">
                {check.label}
                {check.detail && <span className="ml-2 text-xs text-ink-secondary">{check.detail}</span>}
              </span>
            </li>
          ))}
        </ul>
      )}
      {canCheck && (
        <div className="mt-3 border-t border-white/8 pt-3">
          <Button
            variant="secondary"
            onClick={() =>
              runConfigurationCheck(poolId)
                .then((r) => setCheckResult(`${r.summary} (${r.note})`))
                .catch((err) => setCheckResult(extractErrorMessage(err, "The configuration check could not run.")))
            }
          >
            Run configuration check (recorded)
          </Button>
          {checkResult && <p className="mt-2 text-xs text-ink-secondary">{checkResult}</p>}
        </div>
      )}
    </Card>
  )
}
