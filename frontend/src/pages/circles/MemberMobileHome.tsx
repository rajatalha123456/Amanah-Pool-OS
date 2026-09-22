import { useEffect, useMemo, useState } from "react"
import { useParams } from "react-router-dom"
import { Badge } from "../../components/Badge"
import { Card } from "../../components/Card"
import { Spinner } from "../../components/Spinner"
import {
  fetchCircleMember,
  fetchCircleMembers,
  fetchContributionsForMember,
  fetchPayoutsForMember,
} from "../../api/circles"
import { extractErrorMessage } from "../../api/errors"
import type { BadgeVariant, CircleMember, Contribution, Payout } from "../../types"

type Tab = "home" | "ledger" | "help"

const MEMBER_STATUS_BADGE: Record<string, BadgeVariant> = {
  active: "emerald",
  paid_out: "navy",
  withdrawn: "neutral",
}

function memberStatusBadgeVariant(status: string): BadgeVariant {
  return MEMBER_STATUS_BADGE[status] ?? "neutral"
}

type LedgerEntry = {
  id: string
  kind: "contribution" | "payout"
  date: string
  amount: string
  status: string
}

export function MemberMobileHome() {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<Tab>("home")

  const [member, setMember] = useState<CircleMember | null>(null)
  const [poolMembers, setPoolMembers] = useState<CircleMember[]>([])
  const [contributions, setContributions] = useState<Contribution[]>([])
  const [payouts, setPayouts] = useState<Payout[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [pageError, setPageError] = useState("")

  useEffect(() => {
    if (!id) return
    let cancelled = false
    setIsLoading(true)
    setPageError("")

    fetchCircleMember(id)
      .then((memberData) => {
        if (cancelled) return
        setMember(memberData)
        return Promise.all([
          fetchCircleMembers(memberData.pool),
          fetchContributionsForMember(id),
          fetchPayoutsForMember(id),
        ])
      })
      .then((result) => {
        if (cancelled || !result) return
        const [membersData, contributionsData, payoutsData] = result
        setPoolMembers(membersData)
        setContributions(contributionsData)
        setPayouts(payoutsData)
      })
      .catch((error) => {
        if (cancelled) return
        setPageError(extractErrorMessage(error, "Unable to load member details."))
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [id])

  const currentCycle = useMemo(() => {
    const cycles = [...contributions.map((c) => c.cycle_number), ...payouts.map((p) => p.cycle_number)]
    return cycles.length > 0 ? Math.max(...cycles) : 1
  }, [contributions, payouts])

  const currentCycleContribution = useMemo(
    () => contributions.find((c) => c.cycle_number === currentCycle) ?? null,
    [contributions, currentCycle],
  )

  const nextTurnMemberId = useMemo(() => {
    const activeByPosition = [...poolMembers]
      .filter((m) => m.status === "active" && m.payout_position !== null)
      .sort((a, b) => (a.payout_position ?? 0) - (b.payout_position ?? 0))
    return activeByPosition[0]?.id ?? null
  }, [poolMembers])

  const isNextTurn = member !== null && member.id === nextTurnMemberId

  const ledgerEntries: LedgerEntry[] = useMemo(() => {
    const entries: LedgerEntry[] = [
      ...contributions.map((c) => ({
        id: `contribution-${c.id}`,
        kind: "contribution" as const,
        date: c.contribution_date,
        amount: c.amount,
        status: c.status,
      })),
      ...payouts.map((p) => ({
        id: `payout-${p.id}`,
        kind: "payout" as const,
        date: p.payout_date,
        amount: p.amount,
        status: p.status,
      })),
    ]
    return entries.sort((a, b) => (a.date < b.date ? 1 : -1))
  }, [contributions, payouts])

  return (
    <div className="mx-auto flex min-h-screen max-w-md flex-col bg-navy-950">
      <div className="flex-1 px-4 py-6">
        {isLoading ? (
          <div className="flex items-center justify-center gap-2 py-16 text-ink-secondary">
            <Spinner className="h-5 w-5" />
            Loading...
          </div>
        ) : pageError ? (
          <p className="py-8 text-center text-sm text-red-400">{pageError}</p>
        ) : !member ? (
          <p className="py-8 text-center text-sm text-ink-secondary">Member not found.</p>
        ) : (
          <>
            {activeTab === "home" && (
              <HomeTab
                member={member}
                currentCycle={currentCycle}
                currentCycleContribution={currentCycleContribution}
                isNextTurn={isNextTurn}
              />
            )}
            {activeTab === "ledger" && <LedgerTab entries={ledgerEntries} />}
            {activeTab === "help" && <HelpTab />}
          </>
        )}
      </div>

      <nav className="sticky bottom-0 flex border-t border-white/8 bg-navy-900">
        {(
          [
            { key: "home", label: "Home" },
            { key: "ledger", label: "Ledger" },
            { key: "help", label: "Help" },
          ] as { key: Tab; label: string }[]
        ).map((tab) => (
          <button
            key={tab.key}
            type="button"
            onClick={() => setActiveTab(tab.key)}
            className={`flex-1 py-3 text-center text-sm font-medium transition-colors ${
              activeTab === tab.key ? "text-emerald-400" : "text-ink-secondary"
            }`}
          >
            {tab.label}
          </button>
        ))}
      </nav>
    </div>
  )
}

function HomeTab({
  member,
  currentCycle,
  currentCycleContribution,
  isNextTurn,
}: {
  member: CircleMember
  currentCycle: number
  currentCycleContribution: Contribution | null
  isNextTurn: boolean
}) {
  return (
    <div className="space-y-4">
      <div className="text-center">
        <h1 className="text-lg font-semibold text-ink-primary">{member.member_name}</h1>
        <p className="text-xs text-ink-secondary">{member.member_reference}</p>
        <div className="mt-2">
          <Badge variant={memberStatusBadgeVariant(member.status)}>{member.status}</Badge>
        </div>
      </div>

      <Card title="Current Cycle">
        <div className="flex items-center justify-between">
          <span className="text-sm text-ink-secondary">Cycle {currentCycle}</span>
          {currentCycleContribution ? (
            <Badge variant={currentCycleContribution.status === "received" ? "emerald" : "gold"}>
              {currentCycleContribution.status === "received" ? "Paid" : "Pending"}
            </Badge>
          ) : (
            <Badge variant="neutral">Not recorded</Badge>
          )}
        </div>
      </Card>

      <Card title="Payout Position">
        <p className="text-sm text-ink-primary">
          {member.payout_position === null ? "Not drawn yet" : `Position ${member.payout_position}`}
        </p>
      </Card>

      <Card title="Next Payout">
        {isNextTurn && member.status === "active" ? (
          <p className="text-sm text-emerald-400">It's your turn once this cycle's contributions are complete.</p>
        ) : (
          <p className="text-sm text-ink-secondary">Not your turn yet.</p>
        )}
      </Card>
    </div>
  )
}

function LedgerTab({ entries }: { entries: LedgerEntry[] }) {
  return (
    <Card title="Ledger">
      {entries.length === 0 ? (
        <p className="text-sm text-ink-secondary">No contributions or payouts yet.</p>
      ) : (
        <ul className="divide-y divide-white/5">
          {entries.map((entry) => (
            <li key={entry.id} className="flex items-center justify-between py-3 text-sm">
              <div>
                <p className="text-ink-primary">{entry.kind === "contribution" ? "Contribution" : "Payout"}</p>
                <p className="text-xs text-ink-secondary">{entry.date}</p>
              </div>
              <div className="text-right">
                <p className="text-ink-primary">{entry.amount}</p>
                <Badge
                  variant={
                    entry.status === "received" || entry.status === "disbursed" ? "emerald" : "gold"
                  }
                >
                  {entry.status}
                </Badge>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Card>
  )
}

function HelpTab() {
  return (
    <div className="space-y-4">
      <Card title="How do I submit a contribution?">
        <p className="text-sm text-ink-secondary">
          Contributions are recorded by your circle's finance team once your payment is received. Contact
          your pool manager if you believe a contribution is missing.
        </p>
      </Card>
      <Card title="When will I receive my payout?">
        <p className="text-sm text-ink-secondary">
          Payouts follow the draw order shown on your Home tab. Your payout is disbursed once every active
          member has contributed for the current cycle.
        </p>
      </Card>
      <Card title="Need more help?">
        <p className="text-sm text-ink-secondary">
          Reach out to your pool manager for any other questions about your circle membership.
        </p>
      </Card>
    </div>
  )
}
