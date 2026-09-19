import { useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { Badge } from "../../components/Badge"
import { Card } from "../../components/Card"
import { PageHeader } from "../../components/PageHeader"
import { Spinner } from "../../components/Spinner"
import { StatCard } from "../../components/StatCard"
import { Table, type TableColumn } from "../../components/Table"
import {
  fetchCapitalAccount,
  fetchLatestNAV,
  fetchRedemptionsForAccount,
  fetchSubscriptionsForAccount,
} from "../../api/investments"
import { extractErrorMessage } from "../../api/errors"
import type { CapitalAccount, NAVSnapshot, Redemption, Subscription } from "../../types"

type PageState = "loading" | "loaded" | "error"

export function CapitalAccountDetail() {
  const { id } = useParams<{ id: string }>()

  const [pageState, setPageState] = useState<PageState>("loading")
  const [pageError, setPageError] = useState("")
  const [account, setAccount] = useState<CapitalAccount | null>(null)
  const [latestNAV, setLatestNAV] = useState<NAVSnapshot | null>(null)
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([])
  const [redemptions, setRedemptions] = useState<Redemption[]>([])

  useEffect(() => {
    if (!id) return
    setPageState("loading")
    setPageError("")

    fetchCapitalAccount(id)
      .then((accountData) =>
        Promise.all([
          fetchLatestNAV(accountData.pool),
          fetchSubscriptionsForAccount(id),
          fetchRedemptionsForAccount(id),
        ]).then(([navData, subscriptionData, redemptionData]) => {
          setAccount(accountData)
          setLatestNAV(navData)
          setSubscriptions(subscriptionData)
          setRedemptions(redemptionData)
          setPageState("loaded")
        }),
      )
      .catch((error) => {
        setPageError(extractErrorMessage(error, "Unable to load this capital account."))
        setPageState("error")
      })
  }, [id])

  const currentValue =
    account && latestNAV
      ? (Number(account.units_held) * Number(latestNAV.nav_per_unit)).toFixed(2)
      : null

  const subscriptionColumns: TableColumn<Subscription>[] = [
    { header: "Date", accessor: (item) => item.transaction_date },
    { header: "Amount", accessor: (item) => item.amount },
    { header: "NAV / Unit", accessor: (item) => item.nav_per_unit },
    { header: "Units Allotted", accessor: (item) => item.units_allotted },
    { header: "Status", accessor: (item) => <Badge variant="emerald">{item.status}</Badge> },
  ]

  const redemptionColumns: TableColumn<Redemption>[] = [
    { header: "Date", accessor: (item) => item.transaction_date },
    { header: "Units Redeemed", accessor: (item) => item.units_redeemed },
    { header: "NAV / Unit", accessor: (item) => item.nav_per_unit },
    { header: "Amount", accessor: (item) => item.amount },
    { header: "Status", accessor: (item) => <Badge variant="gold">{item.status}</Badge> },
  ]

  return (
    <div>
      <PageHeader
        title={account ? account.investor_name : "Capital Account"}
        subtitle={account ? `${account.investor_reference} — read-only portfolio summary` : undefined}
        actions={
          <Link to="/investments" className="text-sm text-emerald-400 hover:text-emerald-300">
            ← Back to Investment Pools
          </Link>
        }
      />

      {pageState === "loading" && (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          <span className="text-sm">Loading portfolio summary...</span>
        </div>
      )}

      {pageState === "error" && (
        <Card>
          <p className="text-sm text-red-400">{pageError}</p>
        </Card>
      )}

      {pageState === "loaded" && account && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <StatCard label="Units Held" value={account.units_held} deltaTone="neutral" />
            <StatCard
              label="Current Value"
              value={currentValue ?? "—"}
              delta={latestNAV ? `NAV ${latestNAV.nav_per_unit} @ ${latestNAV.valuation_date}` : "No published NAV"}
              deltaTone={latestNAV ? "positive" : "neutral"}
            />
            <StatCard label="Status" value={account.status} deltaTone="neutral" />
            <StatCard label="Investor Reference" value={account.investor_reference} deltaTone="neutral" />
          </div>

          <Card title="Subscription History">
            {subscriptions.length === 0 ? (
              <p className="text-sm text-ink-secondary">No subscriptions recorded for this account yet.</p>
            ) : (
              <Table columns={subscriptionColumns} data={subscriptions} keyField={(item) => item.id} />
            )}
          </Card>

          <Card title="Redemption History">
            {redemptions.length === 0 ? (
              <p className="text-sm text-ink-secondary">No redemptions recorded for this account yet.</p>
            ) : (
              <Table columns={redemptionColumns} data={redemptions} keyField={(item) => item.id} />
            )}
          </Card>
        </div>
      )}
    </div>
  )
}
