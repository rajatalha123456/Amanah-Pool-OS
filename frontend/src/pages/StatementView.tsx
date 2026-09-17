import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { Spinner } from "../components/Spinner"
import { fetchStatements } from "../api/allocationRuns"
import type { DepositorStatement } from "../types"

export function StatementView() {
  const { id } = useParams<{ id: string }>()
  const [statements, setStatements] = useState<DepositorStatement[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!id) return
    fetchStatements(id)
      .then((data) => {
        setStatements(data)
        setIsLoading(false)
      })
      .catch(() => {
        setError("Failed to load statements")
        setIsLoading(false)
      })
  }, [id])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen">
        <Spinner className="h-6 w-6" />
      </div>
    )
  }

  if (error || statements.length === 0) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <p className="text-red-400">{error || "No statements available"}</p>
      </div>
    )
  }

  return (
    <div className="space-y-12 p-8">
      {statements.map((stmt, idx) => (
        <div key={stmt.id} className="page-break border-b border-white/10 pb-12 last:border-0">
          {idx > 0 && <div className="break-before-page my-12" />}

          <div className="max-w-4xl mx-auto bg-navy-900 border border-white/8 rounded-lg p-8">
            <div className="text-center mb-8">
              <h1 className="text-2xl font-bold text-ink-primary mb-1">Depositor Statement</h1>
              <p className="text-xs text-ink-secondary uppercase tracking-wide">
                Period: {stmt.period_start} to {stmt.period_end}
              </p>
            </div>

            <div className="mb-8">
              <h2 className="text-sm font-semibold text-ink-primary mb-3 uppercase tracking-wide">
                Account Details
              </h2>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-xs text-ink-secondary uppercase mb-1">Participant Class</p>
                  <p className="text-ink-primary font-medium">{stmt.participant_class}</p>
                </div>
                <div>
                  <p className="text-xs text-ink-secondary uppercase mb-1">Generated Date</p>
                  <p className="text-ink-primary font-medium">{stmt.generated_at}</p>
                </div>
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-sm font-semibold text-ink-primary mb-3 uppercase tracking-wide">
                Period Summary
              </h2>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div className="bg-white/5 p-4 rounded">
                  <p className="text-xs text-ink-secondary uppercase mb-1">Opening Balance</p>
                  <p className="text-lg font-semibold text-emerald-400">{stmt.opening_balance}</p>
                </div>
                <div className="bg-white/5 p-4 rounded">
                  <p className="text-xs text-ink-secondary uppercase mb-1">Net Deposits</p>
                  <p className="text-lg font-semibold text-ink-primary">{stmt.net_deposits}</p>
                </div>
                <div className="bg-white/5 p-4 rounded">
                  <p className="text-xs text-ink-secondary uppercase mb-1">Profit Allocated</p>
                  <p className="text-lg font-semibold text-gold-400">{stmt.profit_allocated}</p>
                </div>
                <div className="bg-white/5 p-4 rounded border-2 border-emerald-400/30">
                  <p className="text-xs text-ink-secondary uppercase mb-1">Closing Balance</p>
                  <p className="text-lg font-semibold text-emerald-400">{stmt.closing_balance}</p>
                </div>
              </div>
            </div>

            <div className="mb-8">
              <h2 className="text-sm font-semibold text-ink-primary mb-3 uppercase tracking-wide">
                Period Narrative
              </h2>
              <div className="bg-white/5 p-4 rounded text-sm text-ink-primary leading-relaxed">
                {stmt.narrative}
              </div>
            </div>

            <div className="text-center text-xs text-ink-secondary mt-12 pt-8 border-t border-white/8">
              <p>This is an automatically generated statement. For enquiries, contact your fund administrator.</p>
            </div>
          </div>
        </div>
      ))}

      <style>{`
        @media print {
          .page-break {
            page-break-before: always;
          }
          .break-before-page {
            page-break-before: always;
          }
        }
      `}</style>
    </div>
  )
}
