import { useEffect, useMemo, useState, type FormEvent } from "react"
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
  fetchCircleMembers,
  fetchContributionsForPool,
  fetchPayoutsForPool,
  recordContribution,
  runDraw,
} from "../api/circles"
import { fetchPools } from "../api/pools"
import { extractErrorMessage } from "../api/errors"
import type {
  BadgeVariant,
  CircleMember,
  Contribution,
  Payout,
  Pool,
  RunDrawResponse,
} from "../types"

type Tab = "roster" | "rotation"

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

export function CommunityCircles() {
  const { user } = useAuth()
  const isPoolManager = user?.role === "pool_manager"
  const isFinanceMaker = user?.role === "finance_maker"
  const isFinanceChecker = user?.role === "finance_checker"

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
                <Table columns={rosterColumns} data={members} keyField={(member) => member.id} />
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
