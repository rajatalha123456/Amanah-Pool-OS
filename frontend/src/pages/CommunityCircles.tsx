import { useEffect, useMemo, useState, type FormEvent } from "react"
import { useNavigate, useSearchParams } from "react-router-dom"
import { Badge } from "../components/Badge"
import { Button } from "../components/Button"
import { Card } from "../components/Card"
import { Modal } from "../components/Modal"
import { PageHeader } from "../components/PageHeader"
import { Spinner } from "../components/Spinner"
import { Table, type TableColumn } from "../components/Table"
import { useAuth } from "../api/auth"
import { useHasRole } from "../components/RoleGate"
import {
  createCircleMember,
  fetchArrearsRecordsForPool,
  fetchCircleMembers,
  fetchContributionsForPool,
  fetchPayoutsForPool,
  flagArrears,
  grantHardship,
  predictCircleHardship,
  recordContribution,
  runDraw,
  type CircleHardshipPredictionResult,
} from "../api/circles"
import { closeCircleProposal, createCircleProposal, fetchCircleProposals, recordVote } from "../api/circleProposals"
import { fetchPools } from "../api/pools"
import { extractErrorMessage } from "../api/errors"
import { FraudCollusionGraphView } from "../components/governance/FraudCollusionGraphView"
import { CircleGovernance } from "../components/circles/CircleGovernance"
import { fetchRulesSummary } from "../api/circleGovernance"
import { fetchPoolTerms, type PoolTerms } from "../api/disclosures"
import { DrawRoomConsole } from "../components/circles/DrawRoomConsole"
import { PayoutReleaseCeremony } from "../components/circles/PayoutReleaseCeremony"
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
  | "governance_ops"
  | "payout"
  | "mobile"
  | "arrears"
  | "proposals"
  | "collusion_graph"

// Roles that may use the tabs that read more than the circle itself (BRD section 3; the API enforces the same).
const TAB_ROLES: Partial<Record<Tab, string[]>> = {
  payout: ["pool_manager", "finance_maker", "finance_checker", "risk_compliance", "auditor", "shariah_board"],
  collusion_graph: ["risk_compliance", "auditor"],
}

const TABS: { key: Tab; label: string }[] = [
  { key: "setup", label: "Circle Setup" },
  { key: "roster", label: "Member Roster" },
  { key: "calendar", label: "Contribution Calendar" },
  { key: "draw", label: "Rotation / Draw Room" },
  { key: "governance_ops", label: "Rules, Draw & Closure" },
  { key: "payout", label: "Payout Release Ceremony" },
  { key: "mobile", label: "Member Mobile Experience" },
  { key: "arrears", label: "Hardship & Arrears" },
  { key: "proposals", label: "Proposals & Voting" },
  { key: "collusion_graph", label: "🕸️ Syndicate & Collusion Graph" },
]

const SETUP_STEPS = [
  {
    key: "model",
    number: "1",
    label: "Model",
    title: "Operating Model & Pool Identification",
    desc: "Core identity, operating archetype, currency, and product categorization",
  },
  {
    key: "contract",
    number: "2",
    label: "Contract",
    title: "Shariah Contract Charter & Legal Clauses",
    desc: "Qard-e-Hasana bilateral agreement, 0% interest and 0% penalty clauses",
  },
  {
    key: "economics",
    number: "3",
    label: "Economics",
    title: "Contribution, Rotation & Payout Economics",
    desc: "Monthly share per member, aggregated pool total, and rotation cadence",
  },
  {
    key: "assets",
    number: "4",
    label: "Assets",
    title: "Settlement Rails, Escrow & Collateral Assets",
    desc: "Segregated escrow account, Raast/1LINK payment rails, and balance holds",
  },
  {
    key: "governance",
    number: "5",
    label: "Governance",
    title: "Shariah Oversight, Rules & Democratic Voting",
    desc: "Jurisdiction rule pack, fatwa rulings, quorum rules, and hardship protocol",
  },
  {
    key: "review",
    number: "6",
    label: "Review",
    title: "AI Multi-Gate Audit Check & Pool Activation",
    desc: "Automated Shariah verification, integrity checksums, and operational lock",
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

interface CommunityCirclesProps {
  initialTab?: Tab
}

export function CommunityCircles({ initialTab = "setup" }: CommunityCirclesProps = {}) {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const queryTab = (searchParams.get("tab") as Tab) || initialTab
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
  const [activeTab, setActiveTab] = useState<Tab>(queryTab)
  const [setupStep, setSetupStep] = useState<number>(0)

  const [pageError, setPageError] = useState("")
  const [actionError, setActionError] = useState("")
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [isMemberModalOpen, setIsMemberModalOpen] = useState(false)
  const [isDrawConfirmOpen, setIsDrawConfirmOpen] = useState(false)
  const [lastDraw, setLastDraw] = useState<RunDrawResponse | null>(null)
  const [rules, setRules] = useState<Awaited<ReturnType<typeof fetchRulesSummary>> | null>(null)
  const [terms, setTerms] = useState<PoolTerms | null>(null)

  const [contributionModalMember, setContributionModalMember] = useState<CircleMember | null>(null)

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
      setRules(await fetchRulesSummary(poolId).catch(() => null))
      setTerms(await fetchPoolTerms(poolId).catch(() => null))
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

  function setupRows(step: number): Array<[string, string]> {
    const none = "not recorded"
    const r = rules?.rules
    const money = (v: string) => `PKR ${Number(v).toLocaleString(undefined, { minimumFractionDigits: 2 })}`
    const collected = contributions.reduce((sum, c) => sum + Number(c.amount), 0)
    const disbursed = payouts.filter((p) => p.status === "disbursed").reduce((sum, p) => sum + Number(p.amount), 0)
    if (step === 0)
      return [
        ["Circle", selectedPool?.name ?? none],
        ["Code", selectedPool?.code ?? none],
        ["Product", terms?.product ?? selectedPool?.product_detail?.name ?? none],
        ["Currency", terms?.base_currency ?? none],
        ["Status", selectedPool?.status.replace("_", " ") ?? none],
        ["Effective date", selectedPool?.effective_date ?? none],
      ]
    if (step === 1)
      return [
        ["Contract", terms ? `${terms.contract.name} (v${terms.contract.version})` : none],
        ["Contract type", terms?.contract.type.replace(/_/g, " ") ?? none],
        ["Shariah decision", terms?.shariah_decision ? `${terms.shariah_decision.code} - ${terms.shariah_decision.title}` : none],
        ["Hardship policy", r?.hardship_policy ?? "no rules published"],
      ]
    if (step === 2)
      return [
        ["Contribution per member", r ? money(r.contribution_amount) : "no rules published"],
        ["Cycle length", r ? `${r.cycle_days} days` : "no rules published"],
        ["Members", String(members.length)],
        ["Pot per cycle", r ? money(String(Number(r.contribution_amount) * members.filter((m) => m.status !== "withdrawn").length)) : none],
        ["Payout order", r?.order_policy ?? "no rules published"],
      ]
    if (step === 3)
      return [
        ["Collected to date", money(String(collected))],
        ["Disbursed to date", money(String(disbursed))],
        ["Held (collected less paid out)", money(String(collected - disbursed))],
        ["Settlement rail", "set per payout when it is requested"],
      ]
    if (step === 4)
      return [
        ["Jurisdiction rule pack", terms?.jurisdiction_rule_pack ? `${terms.jurisdiction_rule_pack.code} v${terms.jurisdiction_rule_pack.version}` : none],
        ["Circle rules", r ? `v${r.version} sealed ${r.content_hash.slice(0, 12)}...` : "not published"],
        ["Rules accepted by", rules ? `${rules.accepted} of ${rules.total} members` : none],
      ]
    const gaps = [
      !r && "published circle rules",
      rules && rules.missing.length > 0 && `${rules.missing.length} member(s) have not accepted the rules`,
      members.some((m) => m.payout_position === null) && "members without a draw position",
      members.some((m) => m.kyc_status !== "verified") && "members without verified KYC",
      !terms?.shariah_decision && "Shariah decision in force",
    ].filter(Boolean) as string[]
    return [
      ["Open items", gaps.length ? gaps.join("; ") : "none"],
      ["Members", String(members.length)],
      ["Ready for payouts", gaps.length === 0 ? "yes" : "no - see open items"],
    ]
  }

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
        cycle_number: Number(form.get("cycle_number")),
        payment_reference: String(form.get("payment_reference")),
      })
      await loadCircleData(selectedPoolId)
      setContributionModalMember(null)
    } catch (error) {
      setActionError(extractErrorMessage(error, "Unable to record contribution."))
    } finally {
      setIsSaving(false)
    }
  }

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
            {c ? `PKR ${Number(c.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}` : "-"}
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
            {TABS.filter((tab) => !TAB_ROLES[tab.key] || TAB_ROLES[tab.key]!.includes(user?.role ?? "")).map((tab) => (
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

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {setupRows(setupStep).map(([label, value]) => (
                  <div key={label} className="rounded-lg border border-white/8 bg-navy-900 p-4">
                    <p className="text-[11px] font-semibold text-ink-secondary uppercase">{label}</p>
                    <p className="mt-1 text-sm font-semibold text-ink-primary">{value}</p>
                  </div>
                ))}
              </div>
              <p className="text-[11px] text-ink-muted">
                Shown from the circle&apos;s recorded configuration. Anything not recorded says so.
              </p>

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

              <p className="mt-4 border-t border-white/8 pt-3 text-xs text-ink-secondary">
                {members.length} members ·{" "}
                {members.filter((m) => m.kyc_status === "verified").length} with verified KYC ·{" "}
                {members.filter((m) => m.payout_position === null).length} without a draw position ·{" "}
                {members.filter((m) => m.status === "paid_out").length} already paid out
              </p>
            </Card>
          )}

          {/* ========================================================================= */}
          {/* SCREEN 25: Contribution Calendar (PDF Page 26)                           */}
          {/* ========================================================================= */}
          {activeTab === "calendar" && (
            <Card title="Contribution ledger by cycle">
              <p className="mb-3 text-xs text-ink-secondary">
                One column per cycle (the circle runs one cycle per member). A cell shows the recorded receipt; &quot;-&quot; means none
                is recorded yet. Due dates follow the circle rules ({rules?.rules ? `every ${rules.rules.cycle_days} days` : "not published"}).
              </p>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/8 text-[11px] uppercase text-ink-secondary">
                      <th className="px-3 py-2">Member</th>
                      {Array.from({ length: Math.max(members.filter((m) => m.status !== "withdrawn").length, 1) }, (_, i) => (
                        <th key={i} className="px-3 py-2">Cycle {i + 1}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5">
                    {members.map((m) => (
                      <tr key={m.id}>
                        <td className="px-3 py-2 text-ink-primary">{m.member_reference}</td>
                        {Array.from({ length: Math.max(members.filter((x) => x.status !== "withdrawn").length, 1) }, (_, i) => {
                          const c = contributions.find((x) => x.member === m.id && x.cycle_number === i + 1)
                          return (
                            <td key={i} className="px-3 py-2">
                              {c ? (
                                <span className="text-emerald-400">
                                  {Number(c.amount).toLocaleString()} <span className="text-ink-muted">{c.contribution_date}</span>
                                </span>
                              ) : (
                                <span className="text-ink-muted">-</span>
                              )}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          )}

          {/* ========================================================================= */}
          {/* SCREEN 26: Rotation / Draw Room (PDF Page 27)                            */}
          {/* ========================================================================= */}
          {activeTab === "governance_ops" && selectedPoolId && <CircleGovernance poolId={selectedPoolId} />}

          {activeTab === "draw" && (
            <DrawRoomConsole
              poolId={selectedPoolId}
              onDrawExecuted={() => void loadCircleData(selectedPoolId)}
              onDisburseRequested={() => setActiveTab("payout")}
            />
          )}

          {/* ========================================================================= */}
          {/* SCREEN 09 / SCREEN 27: Payout Release Ceremony (BRD Screen 09 / PDF Page 28) */}
          {/* ========================================================================= */}
          {activeTab === "payout" && TAB_ROLES.payout!.includes(user?.role ?? "") && (
            <PayoutReleaseCeremony
              poolId={selectedPoolId}
              onPayoutDisbursed={() => void loadCircleData(selectedPoolId)}
            />
          )}

          {/* ========================================================================= */}
          {/* SCREEN 28: Member Mobile Home (PDF Page 29)                              */}
          {/* ========================================================================= */}
          {activeTab === "mobile" && (
            <Card title="Member view">
              <p className="mb-3 text-xs text-ink-secondary">
                Members do not have their own login yet. Open a member&apos;s own view (ledger, receipts, next payout) from here;
                contributions are recorded by staff from the bank receipt (Member Roster, + Pay).
              </p>
              <div className="space-y-2">
                {members.map((m) => (
                  <div key={m.id} className="flex items-center justify-between text-sm">
                    <span className="text-ink-primary">
                      {m.member_reference} - {m.member_name}
                    </span>
                    <Button variant="secondary" size="sm" onClick={() => navigate(`/circles/members/${m.id}`)}>
                      Open member view
                    </Button>
                  </div>
                ))}
              </div>
            </Card>
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

          {/* ========================================================================= */}
          {/* AI Syndicate & Fraud Collusion Graph Tab                                  */}
          {/* ========================================================================= */}
          {activeTab === "collusion_graph" && TAB_ROLES.collusion_graph!.includes(user?.role ?? "") && (
            <FraudCollusionGraphView poolId={selectedPoolId} />
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
              <input name="joined_date" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required className={inputClasses} />
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
              <input name="amount" type="number" step="0.01" min="0.01" required className={inputClasses} placeholder="As set in the circle rules" />
            </label>
            <label className={labelClasses}>
              Cycle Number
              <input name="cycle_number" type="number" min="1" step="1" required className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Contribution Date
              <input name="contribution_date" type="date" defaultValue={new Date().toISOString().slice(0, 10)} required className={inputClasses} />
            </label>
            <label className={labelClasses}>
              Bank / Raast Payment Reference
              <input name="payment_reference" required className={inputClasses} placeholder="Receipt reference from the bank statement" />
            </label>
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <Button type="submit" disabled={isSaving}>
              {isSaving ? <Spinner className="h-4 w-4" /> : "Record Contribution"}
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

  // The hardship forecaster is available to the roles the API allows (risk, pool manager, Shariah oversight).
  const mayPredict = useHasRole("risk_compliance", "pool_manager", "shariah_board", "shariah_secretariat")

  // AI Hardship Predictor State
  const [prediction, setPrediction] = useState<CircleHardshipPredictionResult | null>(null)
  const [isPredicting, setIsPredicting] = useState(false)

  const memberById = useMemo(
    () => Object.fromEntries(members.map((member) => [member.id, member])) as Record<string, CircleMember>,
    [members],
  )

  async function loadHardshipPrediction() {
    if (!poolId || !mayPredict) return
    setIsPredicting(true)
    try {
      const res = await predictCircleHardship(poolId)
      setPrediction(res)
    } catch (err) {
      console.error(err)
    } finally {
      setIsPredicting(false)
    }
  }

  useEffect(() => {
    if (poolId) {
      void loadHardshipPrediction()
    }
  }, [poolId])

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
    <div className="space-y-6">
      {/* AI Member Hardship & Default Predictor Card */}
      {mayPredict && (
      <Card
        title="AI Predictive Hardship & Default Forecaster"
        actions={
          <Button
            variant="secondary"
            onClick={() => void loadHardshipPrediction()}
            disabled={isPredicting}
            className="text-xs py-1"
          >
            {isPredicting ? <Spinner className="h-4 w-4" /> : "⚡ Refresh AI Forecast"}
          </Button>
        }
      >
        <div className="space-y-4">
          <p className="text-xs text-ink-secondary">
            Predictive machine learning scan analyzes contribution velocities, early payout collection, and member
            financial stress indicators to prevent cycle defaults before maturity.
          </p>

          {isPredicting ? (
            <div className="py-8 text-center text-xs text-ink-muted">
              <Spinner className="h-6 w-6 mx-auto mb-2 text-emerald-400" />
              Evaluating member contribution cadence and moral hazard probabilities...
            </div>
          ) : prediction ? (
            <div className="space-y-4">
              {/* Metrics Summary */}
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 rounded-lg bg-navy-950/70 p-3 border border-white/5">
                <div>
                  <span className="text-[10px] text-ink-muted uppercase font-bold block">Circle Health</span>
                  <span
                    className={`text-sm font-bold ${
                      prediction.overall_health === "STABLE"
                        ? "text-emerald-400"
                        : prediction.overall_health === "GUARDED"
                        ? "text-amber-400"
                        : "text-rose-400"
                    }`}
                  >
                    {prediction.overall_health}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-ink-muted uppercase font-bold block">Avg Default Prob</span>
                  <span className="text-sm font-bold text-white font-mono">
                    {prediction.average_default_probability}%
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-ink-muted uppercase font-bold block">High Risk Members</span>
                  <span className="text-sm font-bold text-amber-300">
                    {prediction.high_risk_count} of {prediction.total_members_analyzed}
                  </span>
                </div>
                <div>
                  <span className="text-[10px] text-ink-muted uppercase font-bold block">Shariah Directive</span>
                  <span className="text-[11px] font-medium text-emerald-400">Zero-Riba Relief Standard</span>
                </div>
              </div>

              {/* Members Risk Forecast Table */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-white/8 text-[10px] uppercase font-semibold text-ink-muted">
                      <th className="pb-2">Member</th>
                      <th className="pb-2">Payout Position</th>
                      <th className="pb-2">Default Risk Probability</th>
                      <th className="pb-2">Predictive AI Warning</th>
                      <th className="pb-2">Shariah Recommended Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-white/5 text-ink-primary">
                    {prediction.member_profiles.map((p) => (
                      <tr key={p.member_id} className="hover:bg-white/[0.02]">
                        <td className="py-2.5 font-medium">
                          <div>
                            <span className="text-white font-semibold">{p.member_name}</span>
                            <span className="block text-[10px] font-mono text-ink-muted">
                              {p.member_reference}
                            </span>
                          </div>
                        </td>
                        <td className="py-2.5">
                          <span className="font-mono">#{p.payout_position || "—"}</span>
                          {p.has_received_payout && (
                            <span className="block text-[9px] text-amber-400 font-bold">
                              PAYOUT COLLECTED
                            </span>
                          )}
                        </td>
                        <td className="py-2.5">
                          <div className="flex items-center gap-2">
                            <div className="w-16 h-1.5 rounded-full bg-navy-800 overflow-hidden">
                              <div
                                className={`h-full ${
                                  p.risk_score >= 70
                                    ? "bg-rose-500"
                                    : p.risk_score >= 40
                                    ? "bg-amber-400"
                                    : "bg-emerald-400"
                                }`}
                                style={{ width: `${p.risk_score}%` }}
                              />
                            </div>
                            <span
                              className={`font-mono font-bold text-xs ${
                                p.risk_score >= 70
                                  ? "text-rose-400"
                                  : p.risk_score >= 40
                                  ? "text-amber-400"
                                  : "text-emerald-400"
                              }`}
                            >
                              {p.risk_score}%
                            </span>
                          </div>
                        </td>
                        <td className="py-2.5 max-w-xs text-[11px] text-ink-secondary">
                          {p.predictive_warning}
                        </td>
                        <td className="py-2.5">
                          <span className="rounded bg-navy-800 px-2 py-1 text-[10px] font-semibold text-emerald-400 border border-white/5 block w-fit">
                            {p.shariah_recommendation}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <p className="text-xs text-ink-muted">No predictive data available for this pool.</p>
          )}
        </div>
      </Card>
      )}

      <Card title="Hardship & Arrears Center">
        <div className="mb-4 flex justify-between items-center">
          <p className="text-xs text-ink-secondary">
            Islamic 0% penalty hardship relief and arrears tracking.
          </p>
          {isRiskCompliance && (
            <div className="flex gap-2">
              <select
                className="rounded-md border border-white/10 bg-navy-800 px-2 py-1 text-xs text-ink-primary"
                value=""
                onChange={(e) => {
                  const m = members.find((x) => x.id === e.target.value)
                  if (m) setFlagModalMember(m)
                }}
              >
                <option value="">Flag arrears for member...</option>
                {members.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.member_reference} - {m.member_name}
                  </option>
                ))}
              </select>
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
                <input name="cycle_number" type="number" min="1" required className={inputClasses} />
              </label>
              <label className={labelClasses}>
                Expected Amount (PKR)
                <input name="expected_amount" type="number" min="0.01" step="0.01" required className={inputClasses} />
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
    </div>
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
  const [voteMemberId, setVoteMemberId] = useState("")
  const [voteMethod, setVoteMethod] = useState<"in_person" | "otp" | "e_sign">("in_person")
  const [voteEvidence, setVoteEvidence] = useState("")
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
    if (!votingProposal || !voteMemberId) return
    setActionError("")
    setIsSaving(true)
    try {
      await recordVote(votingProposal.id, {
        member_id: voteMemberId,
        decision,
        method: voteMethod,
        evidence_reference: voteEvidence,
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
              <input name="voting_deadline" type="date" required className={inputClasses} />
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
            <p className="text-xs text-ink-muted">Record the vote one member cast, with how it was cast.</p>
            <select required className={inputClasses} value={voteMemberId} onChange={(e) => setVoteMemberId(e.target.value)}>
              <option value="">Select the voting member</option>
              {members
                .filter((m) => m.status === "active")
                .map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.member_reference} - {m.member_name}
                  </option>
                ))}
            </select>
            <select className={inputClasses} value={voteMethod} onChange={(e) => setVoteMethod(e.target.value as "in_person" | "otp" | "e_sign")}>
              <option value="in_person">In person</option>
              <option value="otp">OTP</option>
              <option value="e_sign">E-signature</option>
            </select>
            {voteMethod !== "in_person" && (
              <input className={inputClasses} placeholder="OTP / e-signature reference" value={voteEvidence} onChange={(e) => setVoteEvidence(e.target.value)} />
            )}
            {actionError && <p className="text-sm text-red-400">{actionError}</p>}
            <div className="flex justify-end gap-3 pt-4">
              <Button variant="outline" onClick={() => void handleVote("reject")} disabled={isSaving || !voteMemberId}>
                Reject
              </Button>
              <Button variant="primary" onClick={() => void handleVote("approve")} disabled={isSaving || !voteMemberId}>
                Approve
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </Card>
  )
}
