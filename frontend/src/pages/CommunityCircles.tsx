import { useEffect, useMemo, useState, type FormEvent } from "react"
import { useNavigate } from "react-router-dom"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { Modal } from "../components/Modal"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import {
  createCircleMember,
  disbursePayout,
  fetchArrearsRecordsForPool,
  fetchCircleMembers,
  fetchContributionsForPool,
  fetchPayoutsForPool,
  flagArrears,
  grantHardship,
  recordContribution,
  runDraw,
} from "../api/circles"
import { fetchPools } from "../api/pools"
import { extractErrorMessage } from "../api/errors"
import type {
  ArrearsRecord,
  BadgeVariant,
  CircleMember,
  Contribution,
  Payout,
  Pool,
  RunDrawResponse,
} from "../types"

type Tab = "roster" | "rotation" | "arrears"
type RotationView = "table" | "calendar"

const inputClasses =
  "w-full rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
const labelClasses = "mb-1.5 block text-xs font-semibold tracking-wide text-ink-secondary uppercase"

const MEMBER_STATUS_BADGE: Record<string, BadgeVariant> = {
  active: "emerald",
  paid_out: "navy",
  withdrawn: "neutral",
}

function memberStatusBadgeVariant(status: string): BadgeVariant {
  return MEMBER_STATUS_BADGE[status] ?? "neutral"
}

const ARREARS_STATUS_BADGE: Record<string, BadgeVariant> = {
  overdue: "gold",
  hardship_granted: "emerald",
  resolved: "navy",
}

function arrearsStatusBadgeVariant(status: string): BadgeVariant {
  return ARREARS_STATUS_BADGE[status] ?? "neutral"
}

function dateKey(date: Date): string {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`
}

function parseDateKey(value: string): Date {
  const [year, month, day] = value.split("-").map(Number)
  return new Date(year, month - 1, day)
}

function formatCalendarMonth(date: Date): string {
  return date.toLocaleDateString(undefined, { month: "long", year: "numeric" })
}

export function CommunityCircles() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isPoolManager = user?.role === "pool_manager"
  const isFinanceMaker = user?.role === "finance_maker"
  const isFinanceChecker = user?.role === "finance_checker"
  const isRiskCompliance = user?.role === "risk_compliance"
  const isShariahReviewer = user?.role === "shariah_secretariat" || user?.role === "shariah_board"

  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState("")
  const [members, setMembers] = useState<CircleMember[]>([])
  const [activeTab, setActiveTab] = useState<Tab>("roster")
  const [pageError, setPageError] = useState("")
  const [actionError, setActionError] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isMemberModalOpen, setIsMemberModalOpen] = useState(false)
  const [isDrawConfirmOpen, setIsDrawConfirmOpen] = useState(false)
  const [lastDraw, setLastDraw] = useState<RunDrawResponse | null>(null)

  useEffect(() => {
    fetchPools()
      .then((data) => {
        const circlePools = data.filter(
          (pool) => pool.product_detail?.operating_model === "community_circle",
        )
        setPools(circlePools)
        setSelectedPoolId(circlePools[0]?.id ?? "")
      })
      .catch((error) => setPageError(extractErrorMessage(error, "Unable to load community circle pools.")))
      .finally(() => setIsLoading(false))
  }, [])

  useEffect(() => {
    if (!selectedPoolId) {
      setMembers([])
      return
    }

    setIsLoading(true)
    setPageError("")
    setLastDraw(null)
    fetchCircleMembers(selectedPoolId)
      .then((data) => setMembers(data))
      .catch((error) => setPageError(extractErrorMessage(error, "Unable to load circle members.")))
      .finally(() => setIsLoading(false))
  }, [selectedPoolId])

  async function refreshMembers() {
    if (!selectedPoolId) return
    const data = await fetchCircleMembers(selectedPoolId)
    setMembers(data)
  }

  function closeMemberModal() {
    setIsMemberModalOpen(false)
    setActionError("")
  }

  async function handleCreateMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      await createCircleMember({
        pool: selectedPoolId,
        member_name: String(form.get("member_name")),
        member_reference: String(form.get("member_reference")),
        joined_date: String(form.get("joined_date")),
      })
      await refreshMembers()
      closeMemberModal()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to create circle member."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleRunDraw() {
    setActionError("")
    setIsSaving(true)
    try {
      const result = await runDraw(selectedPoolId)
      setLastDraw(result)
      await refreshMembers()
      setIsDrawConfirmOpen(false)
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to run the draw."))
    } finally {
      setIsSaving(false)
    }
  }

  const hasUndrawnMembers = members.some((member) => member.payout_position === null)

  const rosterColumns: TableColumn<CircleMember>[] = [
    { header: "Member Reference", accessor: (member) => member.member_reference },
    { header: "Member Name", accessor: (member) => member.member_name },
    {
      header: "Payout Position",
      accessor: (member) =>
        member.payout_position === null ? (
          <span className="text-ink-secondary">Not drawn yet</span>
        ) : (
          member.payout_position
        ),
    },
    {
      header: "Status",
      accessor: (member) => <Badge variant={memberStatusBadgeVariant(member.status)}>{member.status}</Badge>,
    },
    { header: "Joined Date", accessor: (member) => member.joined_date },
  ]

  return (
    <div>
      <PageHeader
        title="Community Circles"
        subtitle="Manage rotating savings circle membership, draws, and payouts"
        actions={
          <div className="flex items-center gap-3">
            <select
              value={selectedPoolId}
              onChange={(event) => setSelectedPoolId(event.target.value)}
              className="rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
              disabled={pools.length === 0}
            >
              {pools.length === 0 ? <option value="">No community circle pools</option> : null}
              {pools.map((pool) => (
                <option key={pool.id} value={pool.id}>
                  {pool.name} ({pool.code})
                </option>
              ))}
            </select>
          </div>
        }
      />

      {pageError && <p className="mb-4 text-sm text-red-400">{pageError}</p>}

      {isLoading ? (
        <div className="flex items-center gap-2 py-12 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          Loading circle data...
        </div>
      ) : pools.length === 0 ? (
        <Card>
          <p className="text-sm text-ink-secondary">No community circle pools available.</p>
        </Card>
      ) : (
        <>
          <div className="mb-4 flex gap-4 border-b border-white/8 text-sm">
            <button
              type="button"
              onClick={() => setActiveTab("roster")}
              className={`border-b-2 px-1 pb-2 ${activeTab === "roster" ? "border-emerald-500 text-ink-primary" : "border-transparent text-ink-secondary"}`}
            >
              Member Roster
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("rotation")}
              className={`border-b-2 px-1 pb-2 ${activeTab === "rotation" ? "border-emerald-500 text-ink-primary" : "border-transparent text-ink-secondary"}`}
            >
              Rotation & Payouts
            </button>
            <button
              type="button"
              onClick={() => setActiveTab("arrears")}
              className={`border-b-2 px-1 pb-2 ${activeTab === "arrears" ? "border-emerald-500 text-ink-primary" : "border-transparent text-ink-secondary"}`}
            >
              Hardship & Arrears
            </button>
          </div>

          {actionError && <p className="mb-4 text-sm text-red-400">{actionError}</p>}

          {activeTab === "roster" && (
            <Card title="Member Roster">
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div>
                  {lastDraw && (
                    <p className="text-xs text-ink-secondary">
                      Draw seed: <code className="rounded bg-navy-800 px-1.5 py-0.5 text-ink-primary">{lastDraw.seed}</code>
                    </p>
                  )}
                </div>
                <div className="flex gap-2">
                  {isPoolManager && (
                    <Button
                      variant="gold"
                      disabled={!hasUndrawnMembers || isSaving}
                      title={!hasUndrawnMembers ? "All members already have a payout position" : undefined}
                      onClick={() => setIsDrawConfirmOpen(true)}
                    >
                      Run Draw
                    </Button>
                  )}
                  {isPoolManager && hasUndrawnMembers && (
                    <Button variant="primary" onClick={() => setIsMemberModalOpen(true)}>
                      + New Member
                    </Button>
                  )}
                </div>
              </div>
              {members.length === 0 ? (
                <p className="text-sm text-ink-secondary">No circle members for this pool yet.</p>
              ) : (
                <Table
                  columns={rosterColumns}
                  data={members}
                  keyField={(member) => member.id}
                  onRowClick={(member) => navigate(`/community-circles/members/${member.id}`)}
                />
              )}
            </Card>
          )}

          {activeTab === "rotation" && (
            <RotationTab
              poolId={selectedPoolId}
              members={members}
              isFinanceMaker={isFinanceMaker}
              isFinanceChecker={isFinanceChecker}
              onMembersChanged={refreshMembers}
            />
          )}

          {activeTab === "arrears" && (
            <ArrearsTab
              poolId={selectedPoolId}
              members={members}
              isRiskCompliance={isRiskCompliance}
              isShariahReviewer={isShariahReviewer}
            />
          )}
        </>
      )}

      {isMemberModalOpen && (
        <Modal title="New Circle Member" onClose={closeMemberModal}>
          <form onSubmit={handleCreateMember} className="space-y-4">
            <label className={labelClasses}>
              Member Reference
              <input name="member_reference" required className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Member Name
              <input name="member_name" required className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Joined Date
              <input name="joined_date" type="date" required className={inputClasses} />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Create Member"}
            </Button>
          </form>
        </Modal>
      )}

      {isDrawConfirmOpen && (
        <Modal title="Run Draw" onClose={() => setIsDrawConfirmOpen(false)}>
          <div className="space-y-4">
            <p className="text-sm text-ink-primary">
              This action will randomly assign a payout order to all active members who don't have one yet.
              This cannot be undone.
            </p>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => setIsDrawConfirmOpen(false)} disabled={isSaving}>
                Cancel
              </Button>
              <Button variant="gold" onClick={() => void handleRunDraw()} disabled={isSaving}>
                {isSaving ? <Spinner className="h-4 w-4" /> : "Confirm Draw"}
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}

function RotationTab({
  poolId,
  members,
  isFinanceMaker,
  isFinanceChecker,
  onMembersChanged,
}: {
  poolId: string
  members: CircleMember[]
  isFinanceMaker: boolean
  isFinanceChecker: boolean
  onMembersChanged: () => Promise<void>
}) {
  const [cycleNumber, setCycleNumber] = useState(1)
  const [contributions, setContributions] = useState<Contribution[]>([])
  const [payouts, setPayouts] = useState<Payout[]>([])
  const [isLoadingCycle, setIsLoadingCycle] = useState(false)
  const [cycleError, setCycleError] = useState("")
  const [actionError, setActionError] = useState("")
  const [isSaving, setIsSaving] = useState(false)
  const [contributionModalMember, setContributionModalMember] = useState<CircleMember | null>(null)
  const [disburseModalMember, setDisburseModalMember] = useState<CircleMember | null>(null)
  const [rotationView, setRotationView] = useState<RotationView>("table")
  const [calendarMonth, setCalendarMonth] = useState(() => new Date())
  const [selectedCalendarDate, setSelectedCalendarDate] = useState<string | null>(null)

  useEffect(() => {
    if (!poolId || members.length === 0) {
      setContributions([])
      setPayouts([])
      return
    }

    let cancelled = false
    setIsLoadingCycle(true)
    setCycleError("")

    Promise.all([fetchContributionsForPool(poolId), fetchPayoutsForPool(poolId)])
      .then(([contributionData, payoutData]) => {
        if (cancelled) return
        setContributions(contributionData)
        setPayouts(payoutData)
      })
      .catch((error) => {
        if (cancelled) return
        setCycleError(extractErrorMessage(error, "Unable to load contribution/payout data."))
      })
      .finally(() => {
        if (!cancelled) setIsLoadingCycle(false)
      })

    return () => {
      cancelled = true
    }
  }, [poolId, members])

  const activeMembersByPosition = useMemo(
    () =>
      [...members]
        .filter((member) => member.status === "active" && member.payout_position !== null)
        .sort((a, b) => (a.payout_position ?? 0) - (b.payout_position ?? 0)),
    [members],
  )

  const nextTurnMemberId = activeMembersByPosition[0]?.id ?? null

  const cycleContributionByMember = useMemo(() => {
    const map: Record<string, Contribution> = {}
    for (const contribution of contributions) {
      if (contribution.cycle_number === cycleNumber) {
        map[contribution.member] = contribution
      }
    }
    return map
  }, [contributions, cycleNumber])

  const cyclePayoutByMember = useMemo(() => {
    const map: Record<string, Payout> = {}
    for (const payout of payouts) {
      if (payout.cycle_number === cycleNumber) {
        map[payout.member] = payout
      }
    }
    return map
  }, [payouts, cycleNumber])

  const cycleContributions = useMemo(
    () => contributions.filter((contribution) => contribution.cycle_number === cycleNumber),
    [contributions, cycleNumber],
  )

  const memberById = useMemo(
    () => Object.fromEntries(members.map((member) => [member.id, member])) as Record<string, CircleMember>,
    [members],
  )

  const contributionsByDate = useMemo(() => {
    const grouped: Record<string, Contribution[]> = {}
    for (const contribution of cycleContributions) {
      grouped[contribution.contribution_date] ??= []
      grouped[contribution.contribution_date].push(contribution)
    }
    return grouped
  }, [cycleContributions])

  useEffect(() => {
    const firstContribution = cycleContributions
      .map((contribution) => contribution.contribution_date)
      .sort()[0]
    if (firstContribution) {
      const firstDate = parseDateKey(firstContribution)
      setCalendarMonth(new Date(firstDate.getFullYear(), firstDate.getMonth(), 1))
      setSelectedCalendarDate(firstContribution)
    } else {
      setCalendarMonth(new Date())
      setSelectedCalendarDate(null)
    }
  }, [cycleNumber, cycleContributions])

  const calendarDays = useMemo(() => {
    const firstDay = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1)
    const startOffset = firstDay.getDay()
    const daysInMonth = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 0).getDate()
    return Array.from({ length: 42 }, (_, index) => {
      const dayNumber = index - startOffset + 1
      if (dayNumber < 1 || dayNumber > daysInMonth) return null
      const date = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), dayNumber)
      return { date, key: dateKey(date) }
    })
  }, [calendarMonth])

  const selectedDayContributions = selectedCalendarDate
    ? contributionsByDate[selectedCalendarDate] ?? []
    : []

  function changeCalendarMonth(offset: number) {
    setCalendarMonth((current) => new Date(current.getFullYear(), current.getMonth() + offset, 1))
    setSelectedCalendarDate(null)
  }

  const allActiveMembersContributed = activeMembersByPosition.every(
    (member) => cycleContributionByMember[member.id]?.status === "received",
  )

  async function refreshCycleData() {
    const [contributionData, payoutData] = await Promise.all([
      fetchContributionsForPool(poolId),
      fetchPayoutsForPool(poolId),
    ])
    setContributions(contributionData)
    setPayouts(payoutData)
  }

  function closeContributionModal() {
    setContributionModalMember(null)
    setActionError("")
  }

  function closeDisburseModal() {
    setDisburseModalMember(null)
    setActionError("")
  }

  async function handleRecordContribution(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!contributionModalMember) return
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      await recordContribution(contributionModalMember.id, {
        amount: String(form.get("amount")),
        contribution_date: String(form.get("contribution_date")),
        cycle_number: cycleNumber,
      })
      await refreshCycleData()
      closeContributionModal()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to record contribution."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleDisburse(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!disburseModalMember) return
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      await disbursePayout(disburseModalMember.id, {
        cycle_number: cycleNumber,
        amount: String(form.get("amount")),
        payout_date: String(form.get("payout_date")),
      })
      await refreshCycleData()
      await onMembersChanged()
      closeDisburseModal()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to disburse payout."))
    } finally {
      setIsSaving(false)
    }
  }

  const rotationColumns: TableColumn<CircleMember>[] = [
    { header: "Member Reference", accessor: (member) => member.member_reference },
    { header: "Payout Position", accessor: (member) => member.payout_position ?? "—" },
    {
      header: "Contribution",
      accessor: (member) => {
        const contribution = cycleContributionByMember[member.id]
        if (!contribution) return <Badge variant="neutral">not recorded</Badge>
        return (
          <Badge variant={contribution.status === "received" ? "emerald" : "gold"}>
            {contribution.status}
          </Badge>
        )
      },
    },
    {
      header: "Payout",
      accessor: (member) => {
        const payout = cyclePayoutByMember[member.id]
        if (!payout) return <span className="text-ink-secondary">—</span>
        return (
          <span>
            {payout.amount} on {payout.payout_date}{" "}
            <Badge variant={payout.status === "disbursed" ? "emerald" : "gold"}>{payout.status}</Badge>
          </span>
        )
      },
    },
    {
      header: "Actions",
      accessor: (member) => {
        const contribution = cycleContributionByMember[member.id]
        const payout = cyclePayoutByMember[member.id]
        const isActive = member.status === "active"
        const isNextTurn = member.id === nextTurnMemberId

        return (
          <div className="flex flex-wrap gap-2">
            {isFinanceMaker && isActive && !contribution && (
              <Button
                variant="outline"
                onClick={(event) => {
                  event.stopPropagation()
                  setContributionModalMember(member)
                }}
              >
                Record Contribution
              </Button>
            )}
            {isFinanceChecker && isActive && isNextTurn && !payout && (
              <Button
                variant="gold"
                disabled={!allActiveMembersContributed}
                title={
                  !allActiveMembersContributed
                    ? "Waiting for all members to contribute this cycle"
                    : undefined
                }
                onClick={(event) => {
                  event.stopPropagation()
                  setDisburseModalMember(member)
                }}
              >
                Disburse Payout
              </Button>
            )}
          </div>
        )
      },
    },
  ]

  return (
    <Card title="Rotation & Payouts">
      <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3">
          <label className="flex items-center gap-2 text-sm text-ink-secondary">
            Cycle
            <input
              type="number"
              min="1"
              value={cycleNumber}
              onChange={(event) => setCycleNumber(Math.max(1, Number(event.target.value) || 1))}
              className="w-24 rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
            />
          </label>
          <div className="flex overflow-hidden rounded-md border border-white/10">
            <button
              type="button"
              onClick={() => setRotationView("table")}
              className={`px-3 py-2 text-sm ${rotationView === "table" ? "bg-emerald-600 text-white" : "text-ink-secondary hover:text-ink-primary"}`}
            >
              Table View
            </button>
            <button
              type="button"
              onClick={() => setRotationView("calendar")}
              className={`px-3 py-2 text-sm ${rotationView === "calendar" ? "bg-emerald-600 text-white" : "text-ink-secondary hover:text-ink-primary"}`}
            >
              Calendar View
            </button>
          </div>
        </div>
      </div>

      {cycleError && <p className="mb-4 text-sm text-red-400">{cycleError}</p>}
      {actionError && <p className="mb-4 text-sm text-red-400">{actionError}</p>}

      {isLoadingCycle ? (
        <div className="flex items-center gap-2 py-8 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          Loading cycle data...
        </div>
      ) : members.length === 0 ? (
        <p className="text-sm text-ink-secondary">No circle members for this pool yet.</p>
      ) : rotationView === "calendar" ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,1fr)_18rem]">
          <div>
            <div className="mb-3 flex items-center justify-between">
              <button
                type="button"
                onClick={() => changeCalendarMonth(-1)}
                className="px-2 text-sm text-ink-secondary hover:text-ink-primary"
              >
                Previous
              </button>
              <h3 className="text-sm font-semibold text-ink-primary">{formatCalendarMonth(calendarMonth)}</h3>
              <button
                type="button"
                onClick={() => changeCalendarMonth(1)}
                className="px-2 text-sm text-ink-secondary hover:text-ink-primary"
              >
                Next
              </button>
            </div>
            <div className="mb-2 grid grid-cols-7 gap-2 text-center text-xs font-semibold uppercase text-ink-secondary">
              {['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'].map((day) => <span key={day}>{day}</span>)}
            </div>
            <div className="grid grid-cols-7 gap-2">
              {calendarDays.map((day, index) => {
                if (!day) return <div key={`empty-${index}`} className="min-h-20 rounded-md bg-white/[0.02]" />
                const dayContributions = contributionsByDate[day.key] ?? []
                const hasPaid = dayContributions.some((contribution) => contribution.status === "received")
                const hasDue = dayContributions.some(
                  (contribution) => contribution.status === "pending" && day.key < dateKey(new Date()),
                )
                return (
                  <button
                    key={day.key}
                    type="button"
                    onClick={() => setSelectedCalendarDate(day.key)}
                    className={`min-h-20 rounded-md border p-2 text-left ${selectedCalendarDate === day.key ? "border-emerald-500 bg-emerald-500/10" : "border-white/8 bg-navy-900 hover:border-white/20"}`}
                  >
                    <span className="text-sm text-ink-primary">{day.date.getDate()}</span>
                    <span className="mt-2 flex flex-wrap gap-1">
                      {hasPaid && <Badge variant="emerald">Paid</Badge>}
                      {hasDue && <Badge variant="gold">Due</Badge>}
                      {!hasPaid && !hasDue && dayContributions.length > 0 && <Badge variant="neutral">Pending</Badge>}
                    </span>
                  </button>
                )
              })}
            </div>
          </div>
          <Card title={selectedCalendarDate ? `Contributions — ${selectedCalendarDate}` : "Select a day"}>
            {selectedDayContributions.length === 0 ? (
              <p className="text-sm text-ink-secondary">No contributions on this day.</p>
            ) : (
              <div className="space-y-3">
                {selectedDayContributions.map((contribution) => (
                  <div key={contribution.id} className="border-b border-white/8 pb-3 last:border-0 last:pb-0">
                    <p className="text-sm text-ink-primary">{memberById[contribution.member]?.member_name ?? contribution.member}</p>
                    <p className="mt-1 text-sm text-ink-secondary">Amount: {contribution.amount}</p>
                    <Badge variant={contribution.status === "received" ? "emerald" : "gold"}>
                      {contribution.status === "received" ? "Paid" : "Pending"}
                    </Badge>
                  </div>
                ))}
              </div>
            )}
          </Card>
        </div>
      ) : (
        <Table columns={rotationColumns} data={members} keyField={(member) => member.id} />
      )}

      {contributionModalMember && (
        <Modal title={`Record Contribution — ${contributionModalMember.member_reference}`} onClose={closeContributionModal}>
          <form onSubmit={handleRecordContribution} className="space-y-4">
            <p className="text-sm text-ink-secondary">Cycle {cycleNumber}</p>
            <label className={labelClasses}>
              Amount
              <input name="amount" type="number" step="0.01" min="0" required className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Contribution Date
              <input name="contribution_date" type="date" required className={inputClasses} />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Record Contribution"}
            </Button>
          </form>
        </Modal>
      )}

      {disburseModalMember && (
        <Modal title={`Disburse Payout — ${disburseModalMember.member_reference}`} onClose={closeDisburseModal}>
          <form onSubmit={handleDisburse} className="space-y-4">
            <p className="text-sm text-ink-secondary">Cycle {cycleNumber}</p>
            <label className={labelClasses}>
              Amount
              <input name="amount" type="number" step="0.01" min="0" required className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Payout Date
              <input name="payout_date" type="date" required className={inputClasses} />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Disburse Payout"}
            </Button>
          </form>
        </Modal>
      )}
    </Card>
  )
}

function ArrearsTab({
  poolId,
  members,
  isRiskCompliance,
  isShariahReviewer,
}: {
  poolId: string
  members: CircleMember[]
  isRiskCompliance: boolean
  isShariahReviewer: boolean
}) {
  const [records, setRecords] = useState<ArrearsRecord[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [loadError, setLoadError] = useState("")
  const [actionError, setActionError] = useState("")
  const [isSaving, setIsSaving] = useState(false)
  const [flagModalMember, setFlagModalMember] = useState<CircleMember | null>(null)
  const [hardshipModalRecord, setHardshipModalRecord] = useState<ArrearsRecord | null>(null)

  const memberById = useMemo(
    () => Object.fromEntries(members.map((member) => [member.id, member])) as Record<string, CircleMember>,
    [members],
  )

  useEffect(() => {
    if (!poolId) {
      setRecords([])
      return
    }
    let cancelled = false
    setIsLoading(true)
    setLoadError("")
    fetchArrearsRecordsForPool(poolId)
      .then((data) => {
        if (!cancelled) setRecords(data)
      })
      .catch((error) => {
        if (!cancelled) setLoadError(extractErrorMessage(error, "Unable to load arrears records."))
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [poolId])

  async function refreshRecords() {
    const data = await fetchArrearsRecordsForPool(poolId)
    setRecords(data)
  }

  function closeFlagModal() {
    setFlagModalMember(null)
    setActionError("")
  }

  function closeHardshipModal() {
    setHardshipModalRecord(null)
    setActionError("")
  }

  async function handleFlagArrears(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!flagModalMember) return
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      await flagArrears(flagModalMember.id, {
        cycle_number: Number(form.get("cycle_number")),
        expected_amount: String(form.get("expected_amount")),
      })
      await refreshRecords()
      closeFlagModal()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to flag arrears."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleGrantHardship(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!hardshipModalRecord) return
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      await grantHardship(hardshipModalRecord.id, {
        hardship_reason: String(form.get("hardship_reason")),
      })
      await refreshRecords()
      closeHardshipModal()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to grant hardship waiver."))
    } finally {
      setIsSaving(false)
    }
  }

  const arrearsColumns: TableColumn<ArrearsRecord>[] = [
    {
      header: "Member Reference",
      accessor: (record) => memberById[record.member]?.member_reference ?? record.member,
    },
    { header: "Cycle", accessor: (record) => record.cycle_number },
    { header: "Expected Amount", accessor: (record) => record.expected_amount },
    {
      header: "Status",
      accessor: (record) => <Badge variant={arrearsStatusBadgeVariant(record.status)}>{record.status}</Badge>,
    },
    {
      header: "Actions",
      accessor: (record) =>
        isShariahReviewer && record.status === "overdue" ? (
          <Button
            variant="gold"
            onClick={(event) => {
              event.stopPropagation()
              setHardshipModalRecord(record)
            }}
          >
            Grant Hardship
          </Button>
        ) : (
          <span className="text-ink-secondary">—</span>
        ),
    },
  ]

  return (
    <Card title="Hardship & Arrears">
      {isRiskCompliance && members.length > 0 && (
        <div className="mb-4 flex justify-end">
          <select
            onChange={(event) => {
              const member = memberById[event.target.value]
              if (member) setFlagModalMember(member)
              event.target.value = ""
            }}
            value=""
            className="rounded-md border border-white/10 bg-navy-800 px-3 py-2 text-sm text-ink-primary focus:border-emerald-500 focus:outline-none"
          >
            <option value="">Flag as Overdue...</option>
            {members.map((member) => (
              <option key={member.id} value={member.id}>
                {member.member_reference} — {member.member_name}
              </option>
            ))}
          </select>
        </div>
      )}

      {loadError && <p className="mb-4 text-sm text-red-400">{loadError}</p>}
      {actionError && <p className="mb-4 text-sm text-red-400">{actionError}</p>}

      {isLoading ? (
        <div className="flex items-center gap-2 py-8 text-ink-secondary">
          <Spinner className="h-5 w-5" />
          Loading arrears data...
        </div>
      ) : records.length === 0 ? (
        <p className="text-sm text-ink-secondary">No arrears records for this pool.</p>
      ) : (
        <Table columns={arrearsColumns} data={records} keyField={(record) => record.id} />
      )}

      {flagModalMember && (
        <Modal title={`Flag as Overdue — ${flagModalMember.member_reference}`} onClose={closeFlagModal}>
          <form onSubmit={handleFlagArrears} className="space-y-4">
            <label className={labelClasses}>
              Cycle Number
              <input name="cycle_number" type="number" min="1" required className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Expected Amount
              <input name="expected_amount" type="number" step="0.01" min="0" required className={inputClasses} />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Flag as Overdue"}
            </Button>
          </form>
        </Modal>
      )}

      {hardshipModalRecord && (
        <Modal
          title={`Grant Hardship — ${memberById[hardshipModalRecord.member]?.member_reference ?? hardshipModalRecord.member}`}
          onClose={closeHardshipModal}
        >
          <form onSubmit={handleGrantHardship} className="space-y-4">
            <p className="text-sm text-ink-secondary">Cycle {hardshipModalRecord.cycle_number}</p>
            <label className={labelClasses}>
              Hardship Reason (Shariah-compliant justification)
              <textarea
                name="hardship_reason"
                required
                rows={4}
                className={inputClasses}
              />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Grant Hardship"}
            </Button>
          </form>
        </Modal>
      )}
    </Card>
  )
}
