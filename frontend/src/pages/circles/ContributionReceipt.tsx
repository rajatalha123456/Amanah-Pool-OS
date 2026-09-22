import { useEffect, useState } from "react"
import { useParams } from "react-router-dom"
import { Badge } from "../../components/Badge"
import { Button } from "../../components/Button"
import { Spinner } from "../../components/Spinner"
import { fetchContribution } from "../../api/circles"
import { extractErrorMessage } from "../../api/errors"
import type { BadgeVariant, Contribution } from "../../types"

const STATUS_BADGE: Record<string, BadgeVariant> = {
  received: "emerald",
  pending: "gold",
}

export function ContributionReceipt() {
  const { id } = useParams<{ id: string }>()
  const [contribution, setContribution] = useState<Contribution | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState("")

  useEffect(() => {
    if (!id) return
    fetchContribution(id)
      .then((data) => {
        setContribution(data)
        setIsLoading(false)
      })
      .catch((err) => {
        setError(extractErrorMessage(err, "Failed to load receipt"))
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

  if (error || !contribution) {
    return (
      <div className="flex items-center justify-center min-h-screen p-4">
        <p className="text-red-400">{error || "Receipt not found"}</p>
      </div>
    )
  }

  return (
    <div className="space-y-6 p-8">
      <div className="max-w-2xl mx-auto flex justify-end print:hidden">
        <Button variant="primary" onClick={() => window.print()}>
          Print Receipt
        </Button>
      </div>

      <div className="max-w-2xl mx-auto bg-navy-900 border border-white/8 rounded-lg p-8">
        <div className="text-center mb-8">
          <p className="text-xs text-gold-400 uppercase tracking-widest font-semibold mb-1">Amanah Pool OS</p>
          <h1 className="text-2xl font-bold text-ink-primary mb-1">Contribution Receipt</h1>
          <p className="text-xs text-ink-secondary uppercase tracking-wide">Cycle {contribution.cycle_number}</p>
        </div>

        <div className="mb-8">
          <h2 className="text-sm font-semibold text-ink-primary mb-3 uppercase tracking-wide">
            Member Details
          </h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-xs text-ink-secondary uppercase mb-1">Member Name</p>
              <p className="text-ink-primary font-medium">{contribution.member_name}</p>
            </div>
            <div>
              <p className="text-xs text-ink-secondary uppercase mb-1">Member Reference</p>
              <p className="text-ink-primary font-medium">{contribution.member_reference}</p>
            </div>
            <div>
              <p className="text-xs text-ink-secondary uppercase mb-1">Pool</p>
              <p className="text-ink-primary font-medium">
                {contribution.pool_name} ({contribution.pool_code})
              </p>
            </div>
          </div>
        </div>

        <div className="mb-8">
          <h2 className="text-sm font-semibold text-ink-primary mb-3 uppercase tracking-wide">
            Contribution Details
          </h2>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div className="bg-white/5 p-4 rounded">
              <p className="text-xs text-ink-secondary uppercase mb-1">Amount</p>
              <p className="text-lg font-semibold text-emerald-400">{contribution.amount}</p>
            </div>
            <div className="bg-white/5 p-4 rounded">
              <p className="text-xs text-ink-secondary uppercase mb-1">Status</p>
              <Badge variant={STATUS_BADGE[contribution.status] ?? "neutral"}>{contribution.status}</Badge>
            </div>
            <div className="bg-white/5 p-4 rounded">
              <p className="text-xs text-ink-secondary uppercase mb-1">Contribution Date</p>
              <p className="text-ink-primary font-medium">{contribution.contribution_date}</p>
            </div>
            <div className="bg-white/5 p-4 rounded">
              <p className="text-xs text-ink-secondary uppercase mb-1">Cycle Number</p>
              <p className="text-ink-primary font-medium">{contribution.cycle_number}</p>
            </div>
          </div>
        </div>

        <div className="text-center text-xs text-ink-secondary mt-12 pt-8 border-t border-white/8">
          <p>This is an automatically generated receipt. For enquiries, contact your circle administrator.</p>
        </div>
      </div>

      <style>{`
        @media print {
          .print\\:hidden {
            display: none;
          }
        }
      `}</style>
    </div>
  )
}
