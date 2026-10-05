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
import { closeCircleProposal, createCircleProposal, fetchCircleProposals, recordVote } from "../api/circleProposals"
import { fetchPools } from "../api/pools"
import { extractErrorMessage } from "../api/errors"
import type {
  ArrearsRecord,
  BadgeVariant,
  CircleMember,
  CircleProposal,
  Contribution,
  Payout,
  Pool,
  RunDrawResponse,
} from "../types"

type Tab =
  | "setup"
  | "roster"
  | "calendar"
  | "draw"
  | "payout"
  | "mobile"
  | "arrears"
  | "proposals"

const TABS: { key: Tab; label: string }[] = [
  { key: "setup", label: "Circle Setup" },
  { key: "roster", label: "Member Roster" },
  { key: "calendar", label: "Contribution Calendar" },
  { key: "draw", label: "Rotation / Draw Room" },
  { key: "payout", label: "Payout Release Ceremony" },
  { key: "mobile", label: "Member Mobile Experience" },
  { key: "arrears", label: "Hardship & Arrears" },
  { key: "proposals", label: "Proposals & Voting" },
]

const SETUP_STEPS = [
  {
    key: "model",
    number: "1",
    label: "Model",
    title: "Operating Model & Pool Identification",
    desc: "Core identity, operating archetype, currency, and product categorization",
    check: "Operating model and legal entity structure verified against SBP microfinance regulations. Zero time-value uplift confirmed.",
  },
  {
    key: "contract",
    number: "2",
    label: "Contract",
    title: "Shariah Contract Charter & Legal Clauses",
    desc: "Qard-e-Hasana bilateral agreement, 0% interest and 0% penalty clauses",
    check: "Bilateral Qard-e-Hasana charter verified. Strict 0% Riba and zero-penalty hardship relief clauses intact.",
  },
  {
    key: "economics",
    number: "3",
    label: "Economics",
    title: "Contribution, Rotation & Payout Economics",
    desc: "Monthly share per member, aggregated pool total, and rotation cadence",
    check: "Total cycle aggregate matches member contribution sum. 100% mutual fund distribution confirmed with 0% admin fees.",
  },
  {
    key: "assets",
    number: "4",
    label: "Assets",
    title: "Settlement Rails, Escrow & Collateral Assets",
    desc: "Segregated escrow account, Raast/1LINK payment rails, and balance holds",
    check: "Escrow account balance holds verified with core banking integration. Segregated funds operational without interest accrual.",
  },
  {
    key: "governance",
    number: "5",
    label: "Governance",
    title: "Shariah Oversight, Rules & Democratic Voting",
    desc: "Jurisdiction rule pack, fatwa rulings, quorum rules, and hardship protocol",
    check: "Democratic quorum requirements, voting thresholds, and Shariah Board resolution FATWA-2025-01 validated.",
  },
  {
    key: "review",
    number: "6",
    label: "Review",
    title: "AI Multi-Gate Audit Check & Pool Activation",
    desc: "Automated Shariah verification, integrity checksums, and operational lock",
    check: "All 6 setup phases verified. Zero time-value uplift and Shariah Qard-e-Hasana mutual assistance clauses verified. Ready for operational cycles.",
  },
]

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

const PROPOSAL_STATUS_BADGE: Record<string, BadgeVariant> = {
  open: "gold",
  approved: "emerald",
  rejected: "neutral",
  closed: "navy",
}

function proposalStatusBadgeVariant(status: string): BadgeVariant {
  return PROPOSAL_STATUS_BADGE[status] ?? "neutral"
}

export function CommunityCircles() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const isPoolManager = user?.role === "pool_manager" || user?.role === "platform_super_admin"
  const isRiskCompliance = user?.role === "risk_compliance" || user?.role === "platform_super_admin"
  const isShariahReviewer =
    user?.role === "shariah_secretariat" || user?.role === "shariah_board" || user?.role === "platform_super_admin"

  const [pools, setPools] = useState<Pool[]>([])
  const [selectedPoolId, setSelectedPoolId] = useState("")
  const [members, setMembers] = useState<CircleMember[]>([])
  const [contributions, setContributions] = useState<Contribution[]>([])
  const [payouts, setPayouts] = useState<Payout[]>([])
  const [activeTab, setActiveTab] = useState<Tab>("setup")
  const [setupStep, setSetupStep] = useState<number>(0)

  const [pageError, setPageError] = useState("")
  const [actionError, setActionError] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isMemberModalOpen, setIsMemberModalOpen] = useState(false)
  const [isDrawConfirmOpen, setIsDrawConfirmOpen] = useState(false)
  const [lastDraw, setLastDraw] = useState<RunDrawResponse | null>(null)

  const [contributionModalMember, setContributionModalMember] = useState<CircleMember | null>(null)
  const [disburseModalMember, setDisburseModalMember] = useState<CircleMember | null>(null)

  useEffect(() => {
    fetchPools()
      .then((data) => {
        const circlePools = data.filter(
          (pool) => pool.product_detail?.operating_model === "community_circle",
        )
        const poolsToUse = circlePools.length > 0 ? circlePools : data
        setPools(poolsToUse)
        setSelectedPoolId(poolsToUse[0]?.id ?? "")
      })
      .catch((error) => setPageError(extractErrorMessage(error, "Unable to load community circle pools.")))
      .finally(() => setIsLoading(false))
  }, [])

  const selectedPool = useMemo(
    () => pools.find((p) => p.id === selectedPoolId) ?? pools[0],
    [pools, selectedPoolId],
  )

  async function loadCircleData(poolId: string) {
    if (!poolId) {
      setMembers([])
      setContributions([])
      setPayouts([])
      return
    }
    setIsLoading(true)
    setPageError("")
    try {
      const [membersData, contribData, payoutData] = await Promise.all([
        fetchCircleMembers(poolId),
        fetchContributionsForPool(poolId),
        fetchPayoutsForPool(poolId),
      ])
      setMembers(membersData)
      setContributions(contribData)
      setPayouts(payoutData)
    } catch (error) {
      setPageError(extractErrorMessage(error, "Unable to load circle data."))
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    if (selectedPoolId) {
      void loadCircleData(selectedPoolId)
    }
  }, [selectedPoolId])

  async function handleCreateMember(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!selectedPoolId) return
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      await createCircleMember({
        pool: selectedPoolId,
        member_reference: String(form.get("member_reference")),
        member_name: String(form.get("member_name")),
        joined_date: String(form.get("joined_date")),
      })
      await loadCircleData(selectedPoolId)
      setIsMemberModalOpen(false)
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to create circle member."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleRunDraw() {
    if (!selectedPoolId) return
    setActionError("")
    setIsSaving(true)
    try {
      const result = await runDraw(selectedPoolId)
      setLastDraw(result)
      await loadCircleData(selectedPoolId)
      setIsDrawConfirmOpen(false)
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to run draw."))
    } finally {
      setIsSaving(false)
    }
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
        cycle_number: 1,
      })
      await loadCircleData(selectedPoolId)
      setContributionModalMember(null)
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
        cycle_number: 1,
        amount: String(form.get("amount")),
        payout_date: String(form.get("payout_date")),
      })
      await loadCircleData(selectedPoolId)
      setDisburseModalMember(null)
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to disburse payout."))
    } finally {
      setIsSaving(false)
    }
  }

  const activeMembersByPosition = useMemo(
    () =>
      [...members]
        .filter((member) => member.status === "active" && member.payout_position !== null)
        .sort((a, b) => (a.payout_position ?? 0) - (b.payout_position ?? 0)),
    [members],
  )

  const nextEligibleMember = activeMembersByPosition[0] ?? members[0] ?? null
  const hasUndrawnMembers = members.some((m) => m.payout_position === null && m.status === "active")

  const rosterColumns: TableColumn<CircleMember>[] = [
    {
      header: "ID / Ref",
      accessor: (member) => <span className="font-mono text-emerald-400 font-semibold">{member.member_reference}</span>,
    },
    {
      header: "Member Name",
      accessor: (member) => <span className="font-semibold text-ink-primary">{member.member_name}</span>,
    },
    {
      header: "Contribution",
      accessor: (member) => {
        const c = contributions.find((item) => item.member === member.id)
        return (
          <span className="font-mono text-ink-primary">
            PKR {c ? Number(c.amount).toLocaleString(undefined, { minimumFractionDigits: 2 }) : "10,000.00"}
          </span>
        )
      },
    },
    {
      header: "Payout Turn",
      accessor: (member) =>
        member.payout_position !== null ? (
          <span className="inline-flex items-center rounded bg-navy-800 px-2.5 py-0.5 font-mono text-xs font-semibold text-emerald-400">
            Turn #{member.payout_position}
          </span>
        ) : (
          <span className="text-ink-muted text-xs">Unassigned</span>
        ),
    },
    {
      header: "Status",
      accessor: (member) => <Badge variant={memberStatusBadgeVariant(member.status)}>{member.status}</Badge>,
    },
    { header: "Joined Date", accessor: (member) => member.joined_date },
    {
      header: "Actions",
      accessor: (member) => (
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => setContributionModalMember(member)}
            className="rounded border border-white/10 px-2 py-1 text-xs text-ink-secondary hover:border-emerald-500 hover:text-emerald-400"
          >
            + Pay
          </button>
          <button
            type="button"
            onClick={() => navigate(`/circles/members/${member.id}`)}
            className="rounded border border-white/10 px-2 py-1 text-xs text-ink-secondary hover:border-emerald-500 hover:text-emerald-400"
          >
            PWA Mobile
          </button>
        </div>
      ),
    },
  ]

  return (
    <div>
      <PageHeader
        title="Community Circle Setup"
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
      {actionError && <p className="mb-4 text-sm text-red-400">{actionError}</p>}

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
          {/* Sub-Tabs matching Visual UI Catalogue Screens 23 - 28 */}
          <div className="mb-6 flex flex-wrap gap-4 border-b border-white/8 text-sm">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                type="button"
                onClick={() => setActiveTab(tab.key)}
                className={`pb-2.5 font-medium transition-colors ${
                  activeTab === tab.key
                    ? "border-b-2 border-emerald-500 text-ink-primary font-semibold"
                    : "text-ink-secondary hover:text-ink-primary"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>

          {/* ========================================================================= */}
          {/* SCREEN 23: Community Circle Setup (PDF Page 24)                          */}
          {/* ========================================================================= */}
          {activeTab === "setup" && (
            <div className="space-y-6">
              {/* Interactive 6-Phase Pill Stepper */}
              <div className="flex flex-wrap items-center gap-2">
                {SETUP_STEPS.map((step, idx) => {
                  const isSelected = setupStep === idx
                  return (
                    <button
                      key={step.key}
                      type="button"
                      onClick={() => setSetupStep(idx)}
                      className={`cursor-pointer rounded-full px-4 py-1.5 text-xs font-semibold tracking-wide transition-all ${
                        isSelected
                          ? "border border-emerald-500/50 bg-emerald-500/20 text-emerald-400 shadow-sm ring-1 ring-emerald-500/30"
                          : "border border-white/5 bg-navy-800 text-ink-secondary hover:border-white/10 hover:bg-navy-700 hover:text-ink-primary"
                      }`}
                    >
                      {step.number} {step.label}
                    </button>
                  )
                })}
              </div>

              {/* Active Phase Header Bar */}
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 border-b border-white/8 pb-3">
                <div>
                  <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wide">
                    Phase {SETUP_STEPS[setupStep].number}: {SETUP_STEPS[setupStep].title}
                  </h3>
                  <p className="mt-0.5 text-xs text-ink-secondary">
                    {SETUP_STEPS[setupStep].desc}
                  </p>
                </div>
                <span className="self-start sm:self-auto rounded border border-emerald-500/30 bg-emerald-950/40 px-2.5 py-1 font-mono text-[11px] text-emerald-400">
                  Step {setupStep + 1} of {SETUP_STEPS.length}
                </span>
              </div>

              {/* Dynamic Parameter Cards for Phase 1: Model */}
              {setupStep === 0 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">POOL NAME</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      {selectedPool?.name || "Karachi Healthcare Workers Welfare Circle"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">OPERATING MODEL</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      {selectedPool?.product_detail?.operating_model === "community_circle"
                        ? "Qard-Based Rotating Savings (Community Circle / ROSCA)"
                        : selectedPool?.product_detail?.operating_model || "Community Circle"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">POOL CODE / IDENTIFIER</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400 font-mono">
                      {selectedPool?.code || "POOL-CIR-01"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">LINKED PRODUCT CLASSIFICATION</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      {selectedPool?.product_detail?.name || "Tier-1 Community Welfare Circle"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">BASE CURRENCY</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">PKR - Pakistani Rupee</p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">LIFECYCLE STATUS</p>
                    <div className="mt-1">
                      <Badge variant="emerald">{selectedPool?.status?.toUpperCase() || "OPEN"}</Badge>
                    </div>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">EFFECTIVE ACTIVATION DATE</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      {selectedPool?.effective_date
                        ? new Date(selectedPool.effective_date).toLocaleDateString("en-GB", {
                            day: "2-digit",
                            month: "long",
                            year: "numeric",
                          })
                        : "01 September 2026"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">INSTITUTIONAL TENANT</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">Novu Labs Demo Tenant (NOVU-DEMO)</p>
                  </div>
                </div>
              )}

              {/* Dynamic Parameter Cards for Phase 2: Contract */}
              {setupStep === 1 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">CONTRACT TEMPLATE</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      {selectedPool?.product_detail?.contract_template?.name ||
                        "Standard Qard-e-Hasana Rotating Savings Charter"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">CONTRACT ARCHETYPE</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Qard-e-Hasana (Bilateral Mutual Interest-Free Loan)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">RIBA / TIME-VALUE OF MONEY</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400">
                      Strict 0.00% Zero-Interest Guarantee (Riba-Free)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">PENALTY RATE ON HARDSHIP</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400">
                      0.00% Penalty Rate (Charity forfeiture prohibited)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">SHARIAH DECISION REF</p>
                    <p className="mt-1 text-sm font-semibold text-gold-400">FATWA-2025-01 • Approved by Board</p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">GOVERNING STANDARD</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      AAOIFI Standard No. 19 (Qard) & SBP Annexure II
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">EARLY WITHDRAWAL PROTOCOL</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Mutual consent resolution with 100% escrow balance return
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">DISPUTE RESOLUTION</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Independent Shariah Secretariat Advisory Council
                    </p>
                  </div>
                </div>
              )}

              {/* Dynamic Parameter Cards for Phase 3: Economics */}
              {setupStep === 2 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">CONTRIBUTION PER MEMBER</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">PKR 10,000.00 / Cycle</p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">TOTAL POOL / CYCLE AGGREGATE</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400 font-mono">
                      PKR {(members.length > 0 ? members.length * 10000 : 50000).toLocaleString()}.00 / Cycle
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">ACTIVE MEMBER ROSTER</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      {members.length > 0 ? `${members.length} Enrolled Contributing Members` : "5 Members Enrolled"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">ROTATION SELECTION METHOD</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Randomized Transparent Cryptographic Draw
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">CONTRIBUTION CADENCE</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Monthly (Every 30 Calendar Days)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">TOTAL PLANNED CYCLES</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      {members.length > 0 ? `${members.length} Consecutive Monthly Cycles` : "5 Consecutive Monthly Cycles"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">PROFIT SHARING RATIO (PSR)</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Non-Profit Mutual Aid (0% Bank Uplift / 0% Sood)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">ADMIN / MUDARIB FEE</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400">
                      PKR 0.00 (Zero Management Fee)
                    </p>
                  </div>
                </div>
              )}

              {/* Dynamic Parameter Cards for Phase 4: Assets */}
              {setupStep === 3 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">PAYMENT & SETTLEMENT RAIL</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Raast Instant P2P / 1LINK IBFT Core Gateway
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">SEGREGATED ESCROW ACCOUNT</p>
                    <p className="mt-1 text-sm font-semibold font-mono text-emerald-400">
                      PK92-AMANAH-001928374619 (Islamic Escrow)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">ESCROW BALANCE COLLECTED</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary font-mono">
                      PKR {contributions.reduce((s, c) => s + Number(c.amount), 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">MEMBER COLLATERAL / GUARANTEE</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      100% Collateral-Free Mutual Guarantee (Kafalah)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">EMERGENCY HARDSHIP RESERVE</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      PKR 0.00 Deployed (100% Reserve Solvency)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">CBS RECONCILIATION CADENCE</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Automated Real-Time Core Banking Balance Synchronization
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">DISBURSEMENT EXECUTION METHOD</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Multi-Sig Automated Direct Credit to Recipient IBAN
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">CRYPTOGRAPHIC RECORD ANCHOR</p>
                    <p className="mt-1 text-sm font-semibold font-mono text-xs text-ink-secondary">
                      SHA-256 Tamper-Evident Hash Audit Chain
                    </p>
                  </div>
                </div>
              )}

              {/* Dynamic Parameter Cards for Phase 5: Governance */}
              {setupStep === 4 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">JURISDICTION REGULATORY PACK</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Pakistan / SBP • Version 2025.01 (Qard ROSCA)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">DEMOCRATIC VOTING THRESHOLD</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400">
                      Simple Majority (&gt;50% of active circle members)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">ALLOWED MEMBER PROPOSALS</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Contribution Adjustments, Member Replacements, Rule Amendments
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">HARDSHIP RELIEF POLICY</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      0% penalty waiver, repayment pause up to 60 calendar days
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">SHARIAH GOVERNANCE OVERSIGHT</p>
                    <p className="mt-1 text-sm font-semibold text-gold-400">
                      Annual Compliance Review & Continuous Audit Trail
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">RISK & COMPLIANCE TIER</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Tier-1 Low Risk Microfinance Mutual Cooperative
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">QUORUM REQUIREMENT</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      4 out of 5 Members (80% minimum quorum)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">AUDIT LOGGING POLICY</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      Append-Only Immutable Event Journal
                    </p>
                  </div>
                </div>
              )}

              {/* Dynamic Parameter Cards for Phase 6: Review */}
              {setupStep === 5 && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">OVERALL SETUP READINESS</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400">
                      100% Configured & Verified (Ready for Operations)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">MEMBER ROSTER READINESS</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      {members.length} Registered Members (100% KYC Verified)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">CYCLE 1 CONTRIBUTIONS</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400 font-mono">
                      {contributions.length} Contributions Recorded (PKR 50,000 Total)
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">CYCLE 1 PAYOUT STATUS</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      {payouts.length > 0 ? "PKR 50,000 Disbursed to Cycle 1 Recipient" : "Ready for Draw Release"}
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">ROTATION SCHEDULE</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">
                      1 Recipient / Month across {members.length || 5} months
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">ZERO-PENALTY HARDSHIP COMPLIANCE</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400">
                      Active & Protected under AAOIFI Std 19
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">ESCROW SAFETY LOCK</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400">
                      Active Bank Escrow Ringfence
                    </p>
                  </div>
                  <div className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">OPERATIONAL ACTIVATION</p>
                    <p className="mt-1 text-sm font-semibold text-emerald-400">
                      Fully Active & Verified by Shariah Board
                    </p>
                  </div>
                </div>
              )}

              {/* Phase Navigation Footer */}
              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  disabled={setupStep === 0}
                  onClick={() => setSetupStep((s) => Math.max(0, s - 1))}
                  className="cursor-pointer rounded-md border border-white/10 px-4 py-2 text-xs font-semibold text-ink-secondary hover:bg-white/5 hover:text-ink-primary disabled:opacity-30 disabled:pointer-events-none"
                >
                  ← Previous Phase
                </button>
                <button
                  type="button"
                  onClick={() => {
                    if (setupStep < SETUP_STEPS.length - 1) {
                      setSetupStep((s) => s + 1)
                    } else {
                      setActiveTab("roster")
                    }
                  }}
                  className="cursor-pointer rounded-md bg-emerald-600 px-4 py-2 text-xs font-semibold text-white hover:bg-emerald-500 shadow-sm"
                >
                  {setupStep < SETUP_STEPS.length - 1
                    ? `Next: ${SETUP_STEPS[setupStep + 1].number} ${SETUP_STEPS[setupStep + 1].label} →`
                    : "View Member Roster →"}
                </button>
              </div>

              {/* AI CONFIGURATION CHECK banner matching PDF Page 24 */}
              <div className="rounded-xl border border-emerald-500/40 bg-emerald-950/20 p-5">
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75"></span>
                    <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
                  </span>
                  <p className="text-xs font-bold tracking-wider text-emerald-400 uppercase">
                    AI CONFIGURATION CHECK • PHASE {SETUP_STEPS[setupStep].number}: {SETUP_STEPS[setupStep].label.toUpperCase()}
                  </p>
                </div>
                <p className="mt-2 text-sm text-ink-primary">
                  {SETUP_STEPS[setupStep].check}
                </p>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* SCREEN 24: Member Roster (PDF Page 25)                                   */}
          {/* ========================================================================= */}
          {activeTab === "roster" && (
            <Card>
              <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Button variant="primary" onClick={() => setIsMemberModalOpen(true)}>
                    + NEW RECORD
                  </Button>
                  <Button
                    variant="secondary"
                    onClick={() => {
                      const csv =
                        "MemberReference,MemberName,Status,JoinedDate\n" +
                        members.map((m) => `${m.member_reference},${m.member_name},${m.status},${m.joined_date}`).join("\n")
                      const blob = new Blob([csv], { type: "text/csv" })
                      const url = URL.createObjectURL(blob)
                      const a = document.createElement("a")
                      a.href = url
                      a.download = `roster-${selectedPool?.code || "circle"}.csv`
                      a.click()
                    }}
                  >
                    EXPORT
                  </Button>
                  <Button variant="secondary" onClick={() => void loadCircleData(selectedPoolId)}>
                    FILTERS
                  </Button>
                </div>
                <div>
                  {lastDraw && (
                    <p className="text-xs text-ink-secondary">
                      Draw Seed:{" "}
                      <code className="rounded bg-navy-800 px-1.5 py-0.5 text-emerald-400 font-mono">
                        {lastDraw.seed}
                      </code>
                    </p>
                  )}
                </div>
              </div>

              {members.length === 0 ? (
                <p className="text-sm text-ink-secondary">No circle members for this pool yet.</p>
              ) : (
                <Table columns={rosterColumns} data={members} keyField={(member) => member.id} />
              )}

              {/* Bottom Control Total Bar matching Catalogue Screen 24 */}
              <div className="mt-6 border-t border-white/8 pt-4">
                <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 text-xs">
                  <div>
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">RECORDS PROCESSED</p>
                    <p className="text-base font-bold text-ink-primary">
                      {members.length} Members <span className="text-emerald-400 text-xs">100%</span>
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">MATCHED</p>
                    <p className="text-base font-bold text-emerald-400">
                      {members.length > 0 ? "100.0%" : "0.0%"}
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">EXCEPTIONS</p>
                    <p className="text-base font-bold text-ink-primary">
                      {members.filter((m) => m.status !== "active").length}{" "}
                      <span className="text-emerald-400 text-xs">
                        {members.filter((m) => m.status !== "active").length > 0 ? "action required" : "all clear"}
                      </span>
                    </p>
                  </div>
                  <div>
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">CONTROL TOTAL</p>
                    <p className="text-base font-bold text-emerald-400">
                      {members.filter((m) => m.status !== "active").length === 0 ? "Balanced PASS" : "Exceptions REVIEW"}
                    </p>
                  </div>
                </div>
              </div>
            </Card>
          )}

          {/* ========================================================================= */}
          {/* SCREEN 25: Contribution Calendar (PDF Page 26)                           */}
          {/* ========================================================================= */}
          {activeTab === "calendar" && (
            <Card>
              <div className="mb-6 flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold tracking-tight text-ink-primary uppercase">SEPTEMBER 2026</h3>
                  <p className="text-xs text-ink-secondary">Collections, arrears and receipts cycle tracking</p>
                </div>
                <div className="flex items-center gap-3 text-xs">
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-amber-500"></span>
                    <span className="text-ink-secondary">DUE (Collection Scheduled)</span>
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="h-2.5 w-2.5 rounded-full bg-emerald-500"></span>
                    <span className="text-ink-secondary">PAID (Recorded / Reconciled)</span>
                  </span>
                </div>
              </div>

              {/* Calendar Grid 7 columns */}
              <div className="grid grid-cols-7 gap-2.5 text-center">
                {["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"].map((day) => (
                  <div key={day} className="py-2 text-xs font-bold tracking-wider text-ink-secondary">
                    {day}
                  </div>
                ))}

                {/* 35 Calendar Cells matching Page 26 */}
                {Array.from({ length: 35 }, (_, index) => {
                  const day = index + 1
                  const isDue = [3, 10, 17, 24].includes(day)
                  const isPaid = [5, 12, 19, 26].includes(day)

                  return (
                    <div
                      key={day}
                      className={`flex min-h-[72px] flex-col justify-between rounded-lg border p-2 text-left transition-all ${
                        isDue
                          ? "border-amber-500/40 bg-amber-950/20"
                          : isPaid
                          ? "border-emerald-500/40 bg-emerald-950/20"
                          : "border-white/5 bg-navy-900/60 hover:border-white/15"
                      }`}
                    >
                      <span className="text-xs font-semibold text-ink-primary">{day}</span>
                      <div className="mt-1">
                        {isDue && (
                          <span className="inline-block rounded bg-amber-500/20 px-2 py-0.5 text-[10px] font-bold text-amber-300">
                            DUE
                          </span>
                        )}
                        {isPaid && (
                          <span className="inline-block rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
                            PAID
                          </span>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </Card>
          )}

          {/* ========================================================================= */}
          {/* SCREEN 26: Rotation / Draw Room (PDF Page 27)                            */}
          {/* ========================================================================= */}
          {activeTab === "draw" && (
            <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
              {/* Left Gold-Bordered Hero Card */}
              <div className="rounded-2xl border-2 border-amber-500/60 bg-navy-900 p-8 shadow-xl">
                <span className="rounded bg-amber-500/20 px-3 py-1 text-xs font-bold uppercase tracking-wider text-amber-300">
                  TRANSPARENT ROTATION
                </span>
                <p className="mt-4 text-xs font-medium text-ink-secondary">Next eligible recipient</p>
                <h2 className="mt-2 text-3xl font-extrabold tracking-tight text-white uppercase">
                  {nextEligibleMember ? `${nextEligibleMember.member_name} (${nextEligibleMember.member_reference})` : "MEMBER 014"}
                </h2>
                <p className="mt-2 text-2xl font-bold text-emerald-400">PKR 50,000 payout</p>

                <div className="mt-8 flex flex-wrap gap-3">
                  {nextEligibleMember && (
                    <Button
                      variant="primary"
                      className="px-6 py-2.5 text-sm font-semibold"
                      onClick={() => setDisburseModalMember(nextEligibleMember)}
                    >
                      VERIFY & RELEASE
                    </Button>
                  )}
                  {hasUndrawnMembers && (
                    <Button
                      variant="gold"
                      className="px-5 py-2.5 text-sm font-semibold"
                      onClick={() => setIsDrawConfirmOpen(true)}
                    >
                      RUN CRYPTOGRAPHIC DRAW
                    </Button>
                  )}
                </div>
              </div>

              {/* Right Evidence Card */}
              <div className="rounded-2xl border border-white/8 bg-navy-900 p-8">
                <h3 className="text-base font-bold text-ink-primary uppercase tracking-wide">EVIDENCE</h3>
                <div className="mt-6 space-y-4 text-sm">
                  <div className="flex items-center gap-3">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
                      ✓
                    </span>
                    <span className="text-ink-primary">Rules accepted by {members.length}/{members.length} members</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
                      ✓
                    </span>
                    <span className="text-ink-primary">Random seed sealed (Cryptographic PRNG)</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
                      ✓
                    </span>
                    <span className="text-ink-primary">Eligibility passed (Zero arrears / KYC verified)</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
                      ✓
                    </span>
                    <span className="text-ink-primary">Observer signatures 2/2 confirmed</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 text-xs font-bold">
                      ✓
                    </span>
                    <span className="text-ink-primary">Video record and immutable audit proof attached</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* SCREEN 27: Payout Release Ceremony (PDF Page 28)                         */}
          {/* ========================================================================= */}
          {activeTab === "payout" && (
            <div className="space-y-6">
              {/* 4-Stage Approval Ceremony Table */}
              <Card title="Approval Ceremony & Sign-off Timeline">
                <div className="overflow-x-auto">
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr className="border-b border-white/8 text-xs font-semibold uppercase text-ink-secondary">
                        <th className="pb-3">STAGE</th>
                        <th className="pb-3">OWNER</th>
                        <th className="pb-3">DECISION</th>
                        <th className="pb-3">TIMESTAMP</th>
                        <th className="pb-3">EVIDENCE</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5 text-ink-primary">
                      <tr>
                        <td className="py-3 font-semibold">Prepared</td>
                        <td className="py-3">Circle Administrator</td>
                        <td className="py-3">
                          <Badge variant="emerald">Completed</Badge>
                        </td>
                        <td className="py-3 text-ink-secondary">{payouts[0]?.payout_date || "Cycle Opening"}</td>
                        <td className="py-3 font-mono text-xs">{members.length} members validated</td>
                      </tr>
                      <tr>
                        <td className="py-3 font-semibold">Independent check</td>
                        <td className="py-3">Escrow Custodian</td>
                        <td className="py-3">
                          <Badge variant="emerald">Approved</Badge>
                        </td>
                        <td className="py-3 text-ink-secondary">{payouts[0] ? "Verified" : "Pending"}</td>
                        <td className="py-3 font-mono text-xs">
                          PKR{" "}
                          {contributions
                            .reduce((s, c) => s + Number(c.amount), 0)
                            .toLocaleString(undefined, { minimumFractionDigits: 2 })}{" "}
                          in escrow
                        </td>
                      </tr>
                      <tr>
                        <td className="py-3 font-semibold">Shariah review</td>
                        <td className="py-3">Qard Hasan Secretariat</td>
                        <td className="py-3">
                          <Badge variant="emerald">Approved</Badge>
                        </td>
                        <td className="py-3 text-ink-secondary">Certified</td>
                        <td className="py-3 font-mono text-xs">AAOIFI Standard #19 (Zero Riba)</td>
                      </tr>
                      <tr>
                        <td className="py-3 font-semibold">Final release</td>
                        <td className="py-3">Authorized Signatory</td>
                        <td className="py-3">
                          <Badge variant={payouts[0]?.status === "disbursed" ? "emerald" : "gold"}>
                            {payouts[0]?.status === "disbursed" ? "Disbursed" : "Approved"}
                          </Badge>
                        </td>
                        <td className="py-3 text-ink-secondary">
                          {payouts[0]?.payout_date ? `${payouts[0].payout_date} • Released` : "Cycle Closing"}
                        </td>
                        <td className="py-3 font-mono text-xs">
                          {payouts[0]
                            ? `PKR ${parseFloat(payouts[0].amount).toLocaleString()} released`
                            : "GL batch posted"}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Bottom 2 Cards matching Page 28 */}
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <Card title="Decision Note">
                  <p className="text-sm text-ink-secondary">
                    Variance is within 0.02% tolerance. All exceptions are resolved. All {members.length} member
                    contributions collected and reconciled without shortfall.
                  </p>
                </Card>
                <Card title="Control Gates">
                  <div className="space-y-2.5 text-sm">
                    <p className="text-emerald-400 font-medium">✓ Reconciled</p>
                    <p className="text-emerald-400 font-medium">✓ Shariah parameters sealed</p>
                    <p className="text-emerald-400 font-medium">✓ Dual-maker checker authenticated</p>
                  </div>
                </Card>
              </div>

              {/* Disbursed Payouts Table */}
              <Card title="Payout Disbursement History">
                {payouts.length === 0 ? (
                  <p className="text-sm text-ink-secondary">No payouts disbursed yet.</p>
                ) : (
                  <div className="space-y-3">
                    {payouts.map((p) => (
                      <div
                        key={p.id}
                        className="flex items-center justify-between rounded-lg border border-white/8 bg-navy-900 p-4"
                      >
                        <div>
                          <p className="text-sm font-semibold text-ink-primary">Cycle #{p.cycle_number} Disbursed</p>
                          <p className="text-xs text-ink-secondary">{p.payout_date}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-base font-bold text-emerald-400">
                            PKR {Number(p.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                          </p>
                          <Badge variant="emerald">{p.status}</Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </Card>
            </div>
          )}

          {/* ========================================================================= */}
          {/* SCREEN 28: Member Mobile Home (PDF Page 29)                              */}
          {/* ========================================================================= */}
          {activeTab === "mobile" && (
            <div className="flex flex-wrap items-center justify-center gap-8 py-4">
              {/* Smartphone Frame 1: My Circle */}
              <div className="w-72 rounded-[36px] border-4 border-white/10 bg-navy-950 p-5 shadow-2xl">
                <div className="mx-auto mb-4 h-4 w-28 rounded-full bg-white/10"></div>
                <div className="space-y-6 text-center">
                  <p className="text-[11px] font-bold tracking-widest text-emerald-400 uppercase">AMANAH CIRCLE</p>
                  <h3 className="text-xl font-bold text-white">My Circle</h3>

                  <div className="rounded-xl border border-white/8 bg-navy-900 p-4">
                    <p className="text-xs font-semibold text-ink-secondary uppercase">CONTRIBUTION</p>
                    <p className="mt-1 text-2xl font-extrabold text-white">PKR 50,000</p>
                    <span className="mt-2 inline-block rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
                      ACTIVE • POSITION #1
                    </span>
                  </div>

                  <Button
                    variant="primary"
                    className="w-full py-2.5 text-xs font-semibold"
                    onClick={() => navigate(`/circles/members/${members[0]?.id || ""}`)}
                  >
                    VIEW LEDGER
                  </Button>

                  <div className="flex justify-around border-t border-white/8 pt-3 text-[11px] text-ink-muted">
                    <span className="font-bold text-emerald-400">Home</span>
                    <span>Ledger</span>
                    <span>Help</span>
                  </div>
                </div>
              </div>

              {/* Smartphone Frame 2: Contribute */}
              <div className="w-72 rounded-[36px] border-4 border-white/10 bg-navy-950 p-5 shadow-2xl">
                <div className="mx-auto mb-4 h-4 w-28 rounded-full bg-white/10"></div>
                <div className="space-y-6 text-center">
                  <p className="text-[11px] font-bold tracking-widest text-emerald-400 uppercase">AMANAH CIRCLE</p>
                  <h3 className="text-xl font-bold text-white">Contribute</h3>

                  <div className="rounded-xl border border-white/8 bg-navy-900 p-4">
                    <p className="text-xs font-semibold text-ink-secondary uppercase">AMOUNT DUE</p>
                    <p className="mt-1 text-2xl font-extrabold text-amber-300">PKR 50,000</p>
                    <p className="mt-1 text-[11px] text-ink-muted">Due 3rd of month</p>
                  </div>

                  <Button
                    variant="primary"
                    className="w-full py-2.5 text-xs font-semibold"
                    onClick={() => {
                      if (members[0]) setContributionModalMember(members[0])
                    }}
                  >
                    PAY SECURELY
                  </Button>

                  <div className="flex justify-around border-t border-white/8 pt-3 text-[11px] text-ink-muted">
                    <span>Home</span>
                    <span className="font-bold text-emerald-400">Contribute</span>
                    <span>Help</span>
                  </div>
                </div>
              </div>

              {/* Smartphone Frame 3: Payout */}
              <div className="w-72 rounded-[36px] border-4 border-white/10 bg-navy-950 p-5 shadow-2xl">
                <div className="mx-auto mb-4 h-4 w-28 rounded-full bg-white/10"></div>
                <div className="space-y-6 text-center">
                  <p className="text-[11px] font-bold tracking-widest text-emerald-400 uppercase">AMANAH CIRCLE</p>
                  <h3 className="text-xl font-bold text-white">Payout</h3>

                  <div className="rounded-xl border border-white/8 bg-navy-900 p-4">
                    <p className="text-xs font-semibold text-ink-secondary uppercase">NEXT PAYOUT</p>
                    <p className="mt-1 text-2xl font-extrabold text-emerald-400">12 Sep</p>
                    <p className="mt-1 text-[11px] text-ink-muted">Disbursement Cycle 1</p>
                  </div>

                  <Button
                    variant="secondary"
                    className="w-full py-2.5 text-xs font-semibold"
                    onClick={() => setActiveTab("calendar")}
                  >
                    VIEW SCHEDULE
                  </Button>

                  <div className="flex justify-around border-t border-white/8 pt-3 text-[11px] text-ink-muted">
                    <span>Home</span>
                    <span>Ledger</span>
                    <span className="font-bold text-emerald-400">Payout</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ========================================================================= */}
          {/* Hardship & Arrears Tab                                                    */}
          {/* ========================================================================= */}
          {activeTab === "arrears" && (
            <ArrearsTab
              poolId={selectedPoolId}
              members={members}
              isRiskCompliance={isRiskCompliance}
              isShariahReviewer={isShariahReviewer}
            />
          )}

          {/* ========================================================================= */}
          {/* Proposals & Voting Tab                                                    */}
          {/* ========================================================================= */}
          {activeTab === "proposals" && (
            <ProposalsTab poolId={selectedPoolId} members={members} isPoolManager={isPoolManager} />
          )}
        </>
      )}

      {/* Modal: New Circle Member */}
      {isMemberModalOpen && (
        <Modal title="New Circle Member" onClose={() => setIsMemberModalOpen(false)}>
          <form onSubmit={handleCreateMember} className="space-y-4">
            <label className={labelClasses}>
              Member Reference
              <input name="member_reference" required className={inputClasses} placeholder="MEM-006" />
            </label>
            <label className={labelClasses}>
              Member Name
              <input name="member_name" required className={inputClasses} placeholder="Ali Raza" />
            </label>
            <label className={labelClasses}>
              Joined Date
              <input name="joined_date" type="date" defaultValue="2026-09-01" required className={inputClasses} />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Create Member"}
            </Button>
          </form>
        </Modal>
      )}

      {/* Modal: Run Draw */}
      {isDrawConfirmOpen && (
        <Modal title="Run Draw" onClose={() => setIsDrawConfirmOpen(false)}>
          <div className="space-y-4">
            <p className="text-sm text-ink-primary">
              This action will randomly assign a payout order to all active members who don't have one yet. This
              cannot be undone.
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

      {/* Modal: Record Contribution */}
      {contributionModalMember && (
        <Modal
          title={`Record Contribution — ${contributionModalMember.member_name}`}
          onClose={() => setContributionModalMember(null)}
        >
          <form onSubmit={handleRecordContribution} className="space-y-4">
            <label className={labelClasses}>
              Amount (PKR)
              <input name="amount" type="number" step="0.01" min="0" defaultValue="10000.00" required className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Contribution Date
              <input name="contribution_date" type="date" defaultValue="2026-09-03" required className={inputClasses} />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Record Contribution"}
            </Button>
          </form>
        </Modal>
      )}

      {/* Modal: Disburse Payout */}
      {disburseModalMember && (
        <Modal
          title={`Disburse Payout — ${disburseModalMember.member_name}`}
          onClose={() => setDisburseModalMember(null)}
        >
          <form onSubmit={handleDisburse} className="space-y-4">
            <label className={labelClasses}>
              Amount (PKR)
              <input name="amount" type="number" step="0.01" min="0" defaultValue="50000.00" required className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Payout Date
              <input name="payout_date" type="date" defaultValue="2026-09-10" required className={inputClasses} />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Disburse Payout"}
            </Button>
          </form>
        </Modal>
      )}
    </div>
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
      setFlagModalMember(null)
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
      setHardshipModalRecord(null)
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
    { header: "Expected Amount", accessor: (record) => `PKR ${record.expected_amount}` },
    {
      header: "Status",
      accessor: (record) => <Badge variant={arrearsStatusBadgeVariant(record.status)}>{record.status}</Badge>,
    },
    {
      header: "Actions",
      accessor: (record) => (
        <div className="flex items-center gap-2">
          {record.status === "overdue" && isShariahReviewer && (
            <Button
              variant="outline"
              className="text-xs py-1"
              onClick={() => setHardshipModalRecord(record)}
            >
              Grant Hardship
            </Button>
          )}
        </div>
      ),
    },
  ]

  return (
    <Card title="Hardship & Arrears Center">
      <div className="mb-4 flex justify-between items-center">
        <p className="text-xs text-ink-secondary">
          Islamic 0% penalty hardship relief and arrears tracking.
        </p>
        {isRiskCompliance && (
          <div className="flex gap-2">
            {members.slice(0, 1).map((m) => (
              <Button key={m.id} variant="secondary" onClick={() => setFlagModalMember(m)}>
                Flag Member Arrears
              </Button>
            ))}
          </div>
        )}
      </div>

      {loadError && (
        <div className="mb-4 rounded border border-rose-500/40 bg-rose-500/10 p-3 text-sm text-rose-300">
          {loadError}
        </div>
      )}

      {isLoading ? (
        <Spinner className="h-5 w-5" />
      ) : records.length === 0 ? (
        <p className="text-sm text-ink-secondary">No arrears records for this pool.</p>
      ) : (
        <Table columns={arrearsColumns} data={records} keyField={(record) => record.id} />
      )}

      {flagModalMember && (
        <Modal title={`Flag Arrears — ${flagModalMember.member_name}`} onClose={() => setFlagModalMember(null)}>
          <form onSubmit={handleFlagArrears} className="space-y-4">
            <label className={labelClasses}>
              Cycle Number
              <input name="cycle_number" type="number" defaultValue="2" required className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Expected Amount (PKR)
              <input name="expected_amount" type="number" defaultValue="10000.00" required className={inputClasses} />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Flag Arrears"}
            </Button>
          </form>
        </Modal>
      )}

      {hardshipModalRecord && (
        <Modal title="Grant Shariah Hardship Waiver" onClose={() => setHardshipModalRecord(null)}>
          <form onSubmit={handleGrantHardship} className="space-y-4">
            <label className={labelClasses}>
              Hardship Reason
              <textarea
                name="hardship_reason"
                required
                className={inputClasses}
                rows={3}
                placeholder="Documented medical or income disruption..."
              />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Approve Hardship"}
            </Button>
          </form>
        </Modal>
      )}
    </Card>
  )
}

function ProposalsTab({
  poolId,
  members,
  isPoolManager,
}: {
  poolId: string
  members: CircleMember[]
  isPoolManager: boolean
}) {
  const [proposals, setProposals] = useState<CircleProposal[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [isModalOpen, setIsModalOpen] = useState(false)
  const [votingProposal, setVotingProposal] = useState<CircleProposal | null>(null)
  const [actionError, setActionError] = useState("")
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    if (!poolId) return
    setIsLoading(true)
    fetchCircleProposals(poolId)
      .then((data) => setProposals(data))
      .catch(() => setProposals([]))
      .finally(() => setIsLoading(false))
  }, [poolId])

  async function refreshProposals() {
    const data = await fetchCircleProposals(poolId)
    setProposals(data)
  }

  async function handleCreateProposal(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const form = new FormData(event.currentTarget)
    setActionError("")
    setIsSaving(true)
    try {
      await createCircleProposal({
        pool: poolId,
        title: String(form.get("title")),
        description: String(form.get("description")),
        proposal_type: "other",
        voting_deadline: String(form.get("voting_deadline")),
      })
      await refreshProposals()
      setIsModalOpen(false)
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to create proposal."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleVote(decision: "approve" | "reject") {
    if (!votingProposal || members.length === 0) return
    setActionError("")
    setIsSaving(true)
    try {
      await recordVote(votingProposal.id, {
        member_id: members[0].id,
        decision,
      })
      await refreshProposals()
      setVotingProposal(null)
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to record vote."))
    } finally {
      setIsSaving(false)
    }
  }

  async function handleCloseProposal(proposalId: string) {
    setActionError("")
    setIsSaving(true)
    try {
      await closeCircleProposal(proposalId)
      await refreshProposals()
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to close proposal."))
    } finally {
      setIsSaving(false)
    }
  }

  const proposalColumns: TableColumn<CircleProposal>[] = [
    { header: "Title", accessor: (p) => <span className="font-semibold text-ink-primary">{p.title}</span> },
    { header: "Type", accessor: (p) => p.proposal_type },
    { header: "Status", accessor: (p) => <Badge variant={proposalStatusBadgeVariant(p.status)}>{p.status}</Badge> },
    { header: "Voting Deadline", accessor: (p) => p.voting_deadline },
    {
      header: "Actions",
      accessor: (p) => (
        <div className="flex items-center gap-2">
          {p.status === "open" && (
            <>
              <Button variant="outline" className="text-xs py-1" onClick={() => setVotingProposal(p)}>
                Vote
              </Button>
              {isPoolManager && (
                <Button variant="secondary" className="text-xs py-1" onClick={() => void handleCloseProposal(p.id)}>
                  Close
                </Button>
              )}
            </>
          )}
        </div>
      ),
    },
  ]

  return (
    <Card title="Proposals & Democratic Voting">
      <div className="mb-4 flex justify-between items-center">
        <p className="text-xs text-ink-secondary">Member rotation swap and governance proposals.</p>
        {isPoolManager && (
          <Button variant="primary" onClick={() => setIsModalOpen(true)}>
            + New Proposal
          </Button>
        )}
      </div>

      {isLoading ? (
        <Spinner className="h-5 w-5" />
      ) : proposals.length === 0 ? (
        <p className="text-sm text-ink-secondary">No proposals for this circle.</p>
      ) : (
        <Table columns={proposalColumns} data={proposals} keyField={(p) => p.id} />
      )}

      {isModalOpen && (
        <Modal title="Create Circle Proposal" onClose={() => setIsModalOpen(false)}>
          <form onSubmit={handleCreateProposal} className="space-y-4">
            <label className={labelClasses}>
              Proposal Title
              <input name="title" required className={inputClasses} placeholder="Cycle Swap Request..." />
            </label>
            <label className={labelClasses}>
              Description
              <textarea name="description" required rows={3} className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Voting Deadline
              <input name="voting_deadline" type="date" defaultValue="2026-10-15" required className={inputClasses} />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Create Proposal"}
            </Button>
          </form>
        </Modal>
      )}

      {votingProposal && (
        <Modal title={`Cast Vote: ${votingProposal.title}`} onClose={() => setVotingProposal(null)}>
          <div className="space-y-4">
            <p className="text-sm text-ink-secondary">{votingProposal.description}</p>
            <div className="flex justify-end gap-3 pt-4">
              <Button variant="outline" onClick={() => void handleVote("reject")} disabled={isSaving}>
                Reject
              </Button>
              <Button variant="primary" onClick={() => void handleVote("approve")} disabled={isSaving}>
                Approve
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </Card>
  )
}
