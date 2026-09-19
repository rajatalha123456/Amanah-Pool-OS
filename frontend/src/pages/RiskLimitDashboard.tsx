import { useEffect, useState } from "react"
import { Card } from "../components/Card"
import { Spinner } from "../components/Spinner"
import { StatCard } from "../components/StatCard"
import { fetchExceptions, fetchPurificationEntries } from "../api/governance"
import { fetchRelatedPartyTransactions } from "../api/relatedParty"
import { extractErrorMessage } from "../api/errors"

type PageState = "loading" | "loaded" | "error"

interface SeverityCounts {
  low: number
  medium: number
  high: number
  critical: number
}

export function RiskLimitDashboard() {
  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [severityCounts, setSeverityCounts] = useState<SeverityCounts>({
    low: 0,
    medium: 0,
    high: 0,
    critical: 0,
  })
  const [totalExceptions, setTotalExceptions] = useState(0)
  const [pendingRelatedParty, setPendingRelatedParty] = useState(0)
  const [pendingPurification, setPendingPurification] = useState(0)

  useEffect(() => {
    setPageState("loading")
    setPageError("")

    // Pure client-side aggregation over existing endpoints — no new
    // backend. Open exceptions are fetched once and bucketed by severity
    // here; related-party and purification "pending" counts are each a
    // single fetch of the full list, filtered client-side by status,
    // since neither endpoint offers a server-side pending-only filter.
    Promise.all([
      fetchExceptions({ status: "open" }),
      fetchRelatedPartyTransactions(),
      fetchPurificationEntries(),
    ])
      .then(([openExceptions, relatedPartyTransactions, purificationEntries]) => {
        const counts: SeverityCounts = { low: 0, medium: 0, high: 0, critical: 0 }
        for (const exception of openExceptions) {
          if (exception.severity in counts) {
            counts[exception.severity as keyof SeverityCounts] += 1
          }
        }
        setSeverityCounts(counts)
        setTotalExceptions(openExceptions.length)

        setPendingRelatedParty(
          relatedPartyTransactions.filter((t) => t.disclosure_status === "pending_review").length,
        )
        setPendingPurification(
          purificationEntries.filter((e) => e.status === "identified").length,
        )

        setPageState("loaded")
      })
      .catch((err) => {
        setPageError(extractErrorMessage(err, "Failed to load the risk dashboard."))
        setPageState("error")
      })
  }, [])

  if (pageState === "loading") {
    return (
      <div className="flex items-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-5 w-5" />
        <span className="text-sm">Loading risk dashboard...</span>
      </div>
    )
  }

  if (pageState === "error") {
    return (
      <Card>
        <p className="text-sm text-red-400">{pageError}</p>
      </Card>
    )
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <StatCard label="Total Open Exceptions" value={String(totalExceptions)} deltaTone="neutral" />
        <StatCard
          label="Related-Party Pending Review"
          value={String(pendingRelatedParty)}
          deltaTone={pendingRelatedParty > 0 ? "negative" : "positive"}
        />
        <StatCard
          label="Purification Pending"
          value={String(pendingPurification)}
          deltaTone={pendingPurification > 0 ? "negative" : "positive"}
        />
      </div>

      <Card title="Open Exceptions by Severity">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatCard label="Critical" value={String(severityCounts.critical)} deltaTone={severityCounts.critical > 0 ? "negative" : "positive"} />
          <StatCard label="High" value={String(severityCounts.high)} deltaTone={severityCounts.high > 0 ? "negative" : "positive"} />
          <StatCard label="Medium" value={String(severityCounts.medium)} deltaTone="neutral" />
          <StatCard label="Low" value={String(severityCounts.low)} deltaTone="neutral" />
        </div>
      </Card>
    </div>
  )
}
