import { useEffect, useState } from "react"
import { Card } from "../Card"
import { Badge } from "../Badge"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import { Modal } from "../Modal"
import {
  fetchCeremonyReadiness,
  executeCeremonyDisbursal,
} from "../../api/circles"
import type { Payout, PayoutCeremonyReadiness, PayoutReceiptData } from "../../types"

interface PayoutReleaseCeremonyProps {
  poolId: string
  onPayoutDisbursed?: () => void
}

type CeremonyStep = "audit" | "shariah" | "rails" | "signoff" | "complete"

export function PayoutReleaseCeremony({
  poolId,
  onPayoutDisbursed,
}: PayoutReleaseCeremonyProps) {
  const [data, setData] = useState<PayoutCeremonyReadiness | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [currentStep, setCurrentStep] = useState<CeremonyStep>("audit")

  // Form & Execution State
  const [selectedRail, setSelectedRail] = useState("raast_rtgs")
  const [recipientIban, setRecipientIban] = useState("")
  const [recipientBank, setRecipientBank] = useState("Meezan Bank Limited")
  const [secondarySigner, setSecondarySigner] = useState("Mufti Farhan (Shariah Compliance Officer)")
  const [biometricAuthRef, setBiometricAuthRef] = useState("BIO-NADRA-PK-8921-VERIFIED")
  const [autoReconcile, setAutoReconcile] = useState(true)

  // Execution result
  const [isExecuting, setIsExecuting] = useState(false)
  const [settlementResult, setSettlementResult] = useState<{
    payout: Payout
    receipt: {
      utr: string
      certificate_number: string
      ceremony_hash: string
      settlement_rail: string
      recipient_name: string
      recipient_iban: string
      recipient_bank: string
      amount: number
      payout_date: string
      disbursed_by: string
      shariah_seal: string
    }
  } | null>(null)

  // Receipt Modal State
  const [selectedReceipt, setSelectedReceipt] = useState<PayoutReceiptData | null>(null)
  const [isReceiptModalOpen, setIsReceiptModalOpen] = useState(false)

  async function loadReadiness() {
    if (!poolId) return
    try {
      setIsLoading(true)
      setError(null)
      const res = await fetchCeremonyReadiness(poolId)
      setData(res)
      if (res.next_recipient) {
        setRecipientIban(res.next_recipient.default_iban)
        setRecipientBank(res.next_recipient.default_bank)
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load payout ceremony readiness")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadReadiness()
    setCurrentStep("audit")
    setSettlementResult(null)
  }, [poolId])

  async function handleExecuteDisbursal() {
    if (!data || !data.next_recipient) return
    try {
      setIsExecuting(true)
      setError(null)
      const res = await executeCeremonyDisbursal(poolId, {
        member_id: data.next_recipient.member_id,
        cycle_number: data.cycle_number,
        amount: data.next_recipient.pot_amount,
        settlement_rail: selectedRail,
        recipient_iban: recipientIban,
        recipient_bank: recipientBank,
        secondary_signer: secondarySigner,
        biometric_auth_ref: biometricAuthRef,
        auto_reconcile_contributions: autoReconcile,
      })

      setSettlementResult({
        payout: res.payout,
        receipt: res.settlement_receipt,
      })
      setCurrentStep("complete")
      if (onPayoutDisbursed) onPayoutDisbursed()
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Payout execution failed")
    } finally {
      setIsExecuting(false)
    }
  }

  if (isLoading) {
    return (
      <Card className="p-8 text-center bg-surface-primary border border-border-subtle">
        <Spinner className="mx-auto h-8 w-8 text-emerald-500" />
        <p className="mt-3 text-sm text-ink-muted">Loading Ceremony Readiness & Raast Clearing Gateway...</p>
      </Card>
    )
  }

  if (error && !data) {
    return (
      <Card className="p-6 bg-rose-950/20 border border-rose-800/40 text-rose-300">
        <div className="font-semibold text-rose-400">Ceremony Gateway Error</div>
        <div className="text-sm mt-1">{error}</div>
        <Button variant="secondary" className="mt-4" onClick={loadReadiness}>
          Retry Connection
        </Button>
      </Card>
    )
  }

  const recipient = data?.next_recipient
  const pot = data?.pot_summary

  return (
    <div className="space-y-6">
      {/* Header Banner */}
      <div className="rounded-xl p-6 bg-gradient-to-r from-emerald-950/40 via-surface-primary to-slate-900 border border-emerald-500/20 shadow-lg">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">🏛️</span>
              <h2 className="text-xl font-bold text-ink-primary tracking-tight">
                Payout Release Ceremony & Dual-Key Raast Disbursal
              </h2>
              <Badge variant="emerald">BRD Screen 09</Badge>
              <Badge variant="neutral">SBP IBD 03/2012</Badge>
            </div>
            <p className="text-xs text-ink-muted mt-1">
              Multi-signoff disbursement engine enforcing bilateral Qard-e-Hasana terms, zero time-value uplift, and instant settlement via Raast RTGS.
            </p>
          </div>

          <div className="flex items-center gap-2">
            <Button variant="secondary" size="sm" onClick={loadReadiness}>
              🔄 Refresh Readiness
            </Button>
          </div>
        </div>
      </div>

      {/* Stepper Navigation */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
        {[
          { key: "audit", label: "1. Pot Audit", icon: "💰" },
          { key: "shariah", label: "2. Shariah Shield", icon: "📜" },
          { key: "rails", label: "3. Raast Rails", icon: "⚡" },
          { key: "signoff", label: "4. Dual Signoff", icon: "🔑" },
          { key: "complete", label: "5. Settlement Seal", icon: "✅" },
        ].map((s) => {
          const isActive = currentStep === s.key
          const isDone =
            (s.key === "audit" && currentStep !== "audit") ||
            (s.key === "shariah" && ["rails", "signoff", "complete"].includes(currentStep)) ||
            (s.key === "rails" && ["signoff", "complete"].includes(currentStep)) ||
            (s.key === "signoff" && currentStep === "complete")

          return (
            <button
              key={s.key}
              onClick={() => {
                if (settlementResult && s.key !== "complete") return
                setCurrentStep(s.key as CeremonyStep)
              }}
              disabled={settlementResult !== null && s.key !== "complete"}
              className={`p-3 rounded-lg border text-left transition-all ${
                isActive
                  ? "bg-emerald-950/40 border-emerald-500 text-emerald-300 shadow-sm"
                  : isDone
                  ? "bg-surface-secondary/70 border-emerald-700/40 text-emerald-400"
                  : "bg-surface-primary/40 border-border-subtle text-ink-muted hover:border-border-default"
              }`}
            >
              <div className="text-xs font-semibold flex items-center gap-1.5">
                <span>{s.icon}</span>
                <span>{s.label}</span>
              </div>
              <div className="text-[10px] text-ink-muted mt-0.5">
                {isDone ? "Audited & Verified" : isActive ? "Active Stage" : "Pending"}
              </div>
            </button>
          )
        })}
      </div>

      {/* Main Ceremony Card */}
      <Card className="p-6 bg-surface-primary border border-border-subtle shadow-md">
        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-950/20 border border-rose-800/40 text-rose-300 text-xs">
            ⚠️ {error}
          </div>
        )}

        {/* STEP 1: POT AUDIT */}
        {currentStep === "audit" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-border-subtle">
              <div>
                <h3 className="text-base font-semibold text-ink-primary">
                  Step 1: Pot Reconciliation & Pre-Flight Contribution Audit
                </h3>
                <p className="text-xs text-ink-muted mt-0.5">
                  Verifies that all members have satisfied their monthly share before releasing funds.
                </p>
              </div>
              <Badge variant={pot?.is_pot_fully_funded ? "emerald" : "gold"}>
                {pot?.is_pot_fully_funded ? "100% Fully Funded" : "Contributions Pending"}
              </Badge>
            </div>

            {/* Recipient Highlight */}
            {recipient ? (
              <div className="p-4 rounded-xl bg-surface-secondary border border-emerald-500/30 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                <div className="flex items-center gap-3">
                  <div className="h-12 w-12 rounded-full bg-emerald-500/10 border border-emerald-500/40 flex items-center justify-center text-xl font-bold text-emerald-400">
                    #{recipient.payout_position}
                  </div>
                  <div>
                    <div className="text-xs font-mono text-emerald-400 font-semibold">
                      CYCLE #{data?.cycle_number} • TURN #{recipient.payout_position}
                    </div>
                    <div className="text-lg font-bold text-ink-primary">{recipient.member_name}</div>
                    <div className="text-xs text-ink-muted font-mono">{recipient.member_reference}</div>
                  </div>
                </div>

                <div className="text-right">
                  <div className="text-xs text-ink-muted">Aggregate Disbursal Pot</div>
                  <div className="text-2xl font-bold font-mono text-emerald-400">
                    PKR {recipient.pot_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </div>
                  <div className="text-[11px] text-ink-muted">0% Admin Fee • 0% Deduction</div>
                </div>
              </div>
            ) : (
              <div className="p-6 rounded-lg bg-surface-secondary text-center text-ink-muted">
                No active recipient found in rotation ladder. Please run a Qur'ah Draw in the Draw Room first.
              </div>
            )}

            {/* Pot Funding Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-3 rounded-lg bg-surface-secondary/50 border border-border-subtle">
                <div className="text-[11px] text-ink-muted">Total Circle Members</div>
                <div className="text-lg font-bold text-ink-primary font-mono">{data?.pool.total_members}</div>
              </div>
              <div className="p-3 rounded-lg bg-surface-secondary/50 border border-border-subtle">
                <div className="text-[11px] text-ink-muted">Monthly Share / Member</div>
                <div className="text-lg font-bold text-emerald-400 font-mono">
                  PKR {pot?.monthly_share_per_member.toLocaleString()}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-surface-secondary/50 border border-border-subtle">
                <div className="text-[11px] text-ink-muted">Collected vs Expected</div>
                <div className="text-lg font-bold text-ink-primary font-mono">
                  PKR {pot?.total_collected_pot.toLocaleString()} / {pot?.total_expected_pot.toLocaleString()}
                </div>
              </div>
              <div className="p-3 rounded-lg bg-surface-secondary/50 border border-border-subtle">
                <div className="text-[11px] text-ink-muted">Contribution Clearance</div>
                <div className="text-lg font-bold font-mono text-emerald-400">
                  {pot?.received_count} / {pot?.total_active_members} Paid
                </div>
              </div>
            </div>

            {/* Pending members alert if any */}
            {pot && pot.pending_count > 0 && (
              <div className="p-4 rounded-lg bg-amber-950/20 border border-amber-800/40 text-amber-300">
                <div className="flex items-center justify-between">
                  <div className="font-semibold text-xs flex items-center gap-1.5">
                    <span>⚠️</span>
                    <span>{pot.pending_count} Member(s) have not yet recorded their contribution for Cycle #{data?.cycle_number}</span>
                  </div>
                  <label className="flex items-center gap-2 cursor-pointer text-xs text-amber-200">
                    <input
                      type="checkbox"
                      checked={autoReconcile}
                      onChange={(e) => setAutoReconcile(e.target.checked)}
                      className="rounded border-amber-600 text-emerald-600 focus:ring-emerald-500"
                    />
                    <span>Auto-reconcile & record upon ceremony signoff</span>
                  </label>
                </div>
                <div className="mt-2 flex flex-wrap gap-2">
                  {pot.pending_members.map((m: { id: string; name: string; reference: string }) => (
                    <span key={m.id} className="px-2 py-0.5 rounded text-[11px] bg-amber-900/30 border border-amber-700/40">
                      {m.name} ({m.reference})
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end pt-4">
              <Button
                variant="primary"
                onClick={() => setCurrentStep("shariah")}
                disabled={!recipient}
              >
                Proceed to Shariah Shield Check →
              </Button>
            </div>
          </div>
        )}

        {/* STEP 2: SHARIAH SHIELD */}
        {currentStep === "shariah" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-border-subtle">
              <div>
                <h3 className="text-base font-semibold text-ink-primary">
                  Step 2: Shariah Compliance & Zero-Fee Shield
                </h3>
                <p className="text-xs text-ink-muted mt-0.5">
                  AAOIFI Standard 19 & SBP IBD Circular 03/2012 regulatory certifications.
                </p>
              </div>
              <Badge variant="emerald">Shariah Board Certified</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-surface-secondary border border-border-subtle space-y-3">
                <div className="text-xs font-semibold text-ink-primary flex items-center gap-2">
                  <span>⚖️</span>
                  <span>Rule BR-007: Zero Time-Value Uplift</span>
                </div>
                <p className="text-xs text-ink-muted">
                  No member is charged or receives interest, premium, or financial advantage for earlier rotation turns. Every participant receives exactly what they contribute over the cycle.
                </p>
                <div className="flex items-center gap-2 text-xs text-emerald-400">
                  <span>✓</span>
                  <span>Zero Riba Verification Confirmed</span>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-surface-secondary border border-border-subtle space-y-3">
                <div className="text-xs font-semibold text-ink-primary flex items-center gap-2">
                  <span>🛡️</span>
                  <span>100% Principal Purity (Zero Admin Fee)</span>
                </div>
                <p className="text-xs text-ink-muted">
                  The bank strictly absorbs all Raast RTGS, 1LINK switch fees, and operational costs. Not a single rupee is deducted from the recipient's pot.
                </p>
                <div className="flex items-center gap-2 text-xs text-emerald-400">
                  <span>✓</span>
                  <span>Full Pot Amount Guaranteed</span>
                </div>
              </div>
            </div>

            <div className="p-4 rounded-lg bg-emerald-950/20 border border-emerald-500/30 text-emerald-300 text-xs">
              <strong>Shariah Board Resolution:</strong> "The community circle operating under Qard-e-Hasana mutual assistance satisfies the requirements of mutual cooperation (Ta'awun) without contractual ambiguity (Gharar) or illicit enrichment."
            </div>

            <div className="flex justify-between pt-4">
              <Button variant="secondary" onClick={() => setCurrentStep("audit")}>
                ← Back to Pot Audit
              </Button>
              <Button variant="primary" onClick={() => setCurrentStep("rails")}>
                Proceed to Raast Clearing Rails →
              </Button>
            </div>
          </div>
        )}

        {/* STEP 3: RAAST RAILS */}
        {currentStep === "rails" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-border-subtle">
              <div>
                <h3 className="text-base font-semibold text-ink-primary">
                  Step 3: Clearing Rails & Recipient Account Routing
                </h3>
                <p className="text-xs text-ink-muted mt-0.5">
                  Select payment clearing rail and configure beneficiary IBAN.
                </p>
              </div>
              <Badge variant="neutral">Real-Time RTGS</Badge>
            </div>

            {/* Rails Options */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {data?.settlement_rails_options.map((rail: { key: string; title: string; latency: string; fee: string; recommended: boolean }) => {
                const isSelected = selectedRail === rail.key
                return (
                  <div
                    key={rail.key}
                    onClick={() => setSelectedRail(rail.key)}
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${
                      isSelected
                        ? "bg-emerald-950/40 border-emerald-500 shadow-sm"
                        : "bg-surface-secondary/60 border-border-subtle hover:border-border-default"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-semibold text-ink-primary">{rail.title}</span>
                      {rail.recommended && <Badge variant="emerald">Recommended</Badge>}
                    </div>
                    <div className="text-[11px] text-ink-muted mt-2">Latency: {rail.latency}</div>
                    <div className="text-[11px] text-emerald-400 font-mono mt-0.5">Fee: {rail.fee}</div>
                  </div>
                )
              })}
            </div>

            {/* Recipient Banking Form */}
            <div className="p-4 rounded-xl bg-surface-secondary border border-border-subtle space-y-4">
              <div className="text-xs font-semibold text-ink-primary">Beneficiary Banking Profile</div>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] text-ink-muted mb-1">Recipient Name</label>
                  <input
                    type="text"
                    disabled
                    value={recipient?.member_name || ""}
                    className="w-full px-3 py-2 rounded-lg bg-surface-primary border border-border-subtle text-ink-primary text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-ink-muted mb-1">Raast Alias / Mobile</label>
                  <input
                    type="text"
                    disabled
                    value={recipient?.raast_alias || ""}
                    className="w-full px-3 py-2 rounded-lg bg-surface-primary border border-border-subtle text-ink-primary text-xs font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-ink-muted mb-1">Beneficiary IBAN (24 Characters)</label>
                  <input
                    type="text"
                    value={recipientIban}
                    onChange={(e) => setRecipientIban(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface-primary border border-border-subtle text-ink-primary text-xs font-mono focus:border-emerald-500 focus:outline-none"
                    placeholder="PK36MEZN000100..."
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-ink-muted mb-1">Settlement Bank Name</label>
                  <input
                    type="text"
                    value={recipientBank}
                    onChange={(e) => setRecipientBank(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface-primary border border-border-subtle text-ink-primary text-xs focus:border-emerald-500 focus:outline-none"
                    placeholder="Meezan Bank Limited"
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-between pt-4">
              <Button variant="secondary" onClick={() => setCurrentStep("shariah")}>
                ← Back to Shariah Shield
              </Button>
              <Button variant="primary" onClick={() => setCurrentStep("signoff")}>
                Proceed to Dual Signoff →
              </Button>
            </div>
          </div>
        )}

        {/* STEP 4: DUAL SIGNOFF */}
        {currentStep === "signoff" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between pb-4 border-b border-border-subtle">
              <div>
                <h3 className="text-base font-semibold text-ink-primary">
                  Step 4: Dual-Key Custody & Digital Authorization
                </h3>
                <p className="text-xs text-ink-muted mt-0.5">
                  Two independent officers must counter-sign before funds can be released.
                </p>
              </div>
              <Badge variant="gold">Dual-Key Required</Badge>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Key 1: Maker */}
              <div className="p-4 rounded-xl bg-surface-secondary border border-border-subtle space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-ink-primary">Key 1: Maker (Pool Manager)</div>
                  <Badge variant="emerald">Authenticated</Badge>
                </div>
                <p className="text-xs text-ink-muted">
                  Initiates transaction and certifies that all member rotation positions are aligned with the certified Qur'ah draw.
                </p>
                <div className="p-2 rounded bg-surface-primary border border-border-subtle text-xs font-mono text-emerald-400">
                  Signed: Active Session Officer
                </div>
              </div>

              {/* Key 2: Checker */}
              <div className="p-4 rounded-xl bg-surface-secondary border border-border-subtle space-y-3">
                <div className="flex items-center justify-between">
                  <div className="text-xs font-semibold text-ink-primary">Key 2: Checker (Shariah Compliance)</div>
                  <Badge variant="navy">Counter-Signature</Badge>
                </div>
                <div>
                  <label className="block text-[11px] text-ink-muted mb-1">Shariah Officer Sign-off Name</label>
                  <input
                    type="text"
                    value={secondarySigner}
                    onChange={(e) => setSecondarySigner(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface-primary border border-border-subtle text-ink-primary text-xs focus:border-emerald-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="block text-[11px] text-ink-muted mb-1">Biometric / 2FA Token Reference</label>
                  <input
                    type="text"
                    value={biometricAuthRef}
                    onChange={(e) => setBiometricAuthRef(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-surface-primary border border-border-subtle text-ink-primary text-xs font-mono focus:border-emerald-500 focus:outline-none"
                  />
                </div>
              </div>
            </div>

            {/* Disbursal Confirmation Callout */}
            <div className="p-4 rounded-xl bg-gradient-to-r from-emerald-950/40 to-surface-secondary border border-emerald-500/30">
              <div className="flex flex-col md:flex-row items-center justify-between gap-4">
                <div>
                  <div className="text-sm font-bold text-ink-primary">Execute Instant Raast RTGS Release</div>
                  <div className="text-xs text-ink-muted mt-0.5">
                    PKR {recipient?.pot_amount.toLocaleString(undefined, { minimumFractionDigits: 2 })} will be settled to {recipient?.member_name} ({recipientIban}).
                  </div>
                </div>
                <Button
                  variant="primary"
                  size="lg"
                  disabled={isExecuting}
                  onClick={handleExecuteDisbursal}
                  className="bg-emerald-600 hover:bg-emerald-500 shadow-lg text-white"
                >
                  {isExecuting ? (
                    <>
                      <Spinner className="mr-2 h-4 w-4" />
                      Signing & Settling...
                    </>
                  ) : (
                    "⚡ Sign & Disburse Payout"
                  )}
                </Button>
              </div>
            </div>

            <div className="flex justify-start pt-2">
              <Button variant="secondary" onClick={() => setCurrentStep("rails")}>
                ← Back to Rails
              </Button>
            </div>
          </div>
        )}

        {/* STEP 5: SETTLEMENT SEAL / RECEIPT */}
        {currentStep === "complete" && settlementResult && (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-gradient-to-r from-emerald-950/60 via-surface-secondary to-slate-900 border border-emerald-500/40 text-center space-y-3">
              <div className="h-16 w-16 mx-auto rounded-full bg-emerald-500/20 border border-emerald-500 flex items-center justify-center text-3xl">
                ✨
              </div>
              <h3 className="text-xl font-bold text-emerald-400">
                Payout Ceremony Successfully Concluded!
              </h3>
              <p className="text-xs text-ink-muted max-w-lg mx-auto">
                Funds have been cleared through the real-time settlement rails under full Shariah certification.
              </p>
              <div className="inline-block px-4 py-1.5 rounded-full bg-emerald-900/40 border border-emerald-500/40 text-xs font-mono text-emerald-300">
                UTR: {settlementResult.receipt.utr}
              </div>
            </div>

            {/* Certificate Details Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-xl bg-surface-secondary border border-border-subtle space-y-2">
                <div className="text-xs font-semibold text-ink-primary">Settlement Details</div>
                <div className="flex justify-between text-xs py-1 border-b border-border-subtle">
                  <span className="text-ink-muted">Recipient Name:</span>
                  <span className="font-semibold text-ink-primary">{settlementResult.receipt.recipient_name}</span>
                </div>
                <div className="flex justify-between text-xs py-1 border-b border-border-subtle">
                  <span className="text-ink-muted">Amount Disbursed:</span>
                  <span className="font-mono font-bold text-emerald-400">
                    PKR {settlementResult.receipt.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <div className="flex justify-between text-xs py-1 border-b border-border-subtle">
                  <span className="text-ink-muted">Beneficiary IBAN:</span>
                  <span className="font-mono text-ink-primary text-[11px]">{settlementResult.receipt.recipient_iban}</span>
                </div>
                <div className="flex justify-between text-xs py-1">
                  <span className="text-ink-muted">Settlement Rail:</span>
                  <span className="font-semibold text-ink-primary uppercase">{settlementResult.receipt.settlement_rail}</span>
                </div>
              </div>

              <div className="p-4 rounded-xl bg-surface-secondary border border-border-subtle space-y-2">
                <div className="text-xs font-semibold text-ink-primary">Shariah & Audit Seal</div>
                <div className="flex justify-between text-xs py-1 border-b border-border-subtle">
                  <span className="text-ink-muted">Fatwa Certificate #:</span>
                  <span className="font-mono text-emerald-400">{settlementResult.receipt.certificate_number}</span>
                </div>
                <div className="flex justify-between text-xs py-1 border-b border-border-subtle">
                  <span className="text-ink-muted">Principal Delivery:</span>
                  <span className="text-emerald-400 font-semibold">{settlementResult.receipt.shariah_seal}</span>
                </div>
                <div className="flex flex-col text-xs py-1">
                  <span className="text-ink-muted">Ceremony Hash (SHA-256):</span>
                  <span className="font-mono text-[10px] text-ink-muted break-all mt-0.5">
                    {settlementResult.receipt.ceremony_hash}
                  </span>
                </div>
              </div>
            </div>

            <div className="flex justify-between pt-4">
              <Button
                variant="secondary"
                onClick={() => {
                  loadReadiness()
                  setCurrentStep("audit")
                  setSettlementResult(null)
                }}
              >
                🔄 Prepare Next Cycle Ceremony
              </Button>

              <Button
                variant="primary"
                onClick={() => {
                  setSelectedReceipt({
                    payout_id: settlementResult.payout.id,
                    circle_name: data?.pool.name || "Karachi Healthcare Workers Circle",
                    circle_code: data?.pool.code || "POOL-CIR-01",
                    recipient_name: settlementResult.receipt.recipient_name,
                    recipient_reference: recipient?.member_reference || "MEM-002",
                    cycle_number: data?.cycle_number || 2,
                    amount: settlementResult.receipt.amount,
                    payout_date: settlementResult.receipt.payout_date,
                    status: "DISBURSED",
                    settlement_rail: settlementResult.receipt.settlement_rail,
                    settlement_utr: settlementResult.receipt.utr,
                    recipient_iban: settlementResult.receipt.recipient_iban,
                    recipient_bank: settlementResult.receipt.recipient_bank,
                    secondary_approved_by: secondarySigner,
                    secondary_approved_at: new Date().toISOString(),
                    shariah_certificate_number: settlementResult.receipt.certificate_number,
                    biometric_auth_ref: biometricAuthRef,
                    ceremony_hash: settlementResult.receipt.ceremony_hash,
                    legal_entity: "Amanah Islamic Banking Window",
                  })
                  setIsReceiptModalOpen(true)
                }}
              >
                🖨️ View & Print Settlement Voucher
              </Button>
            </div>
          </div>
        )}
      </Card>

      {/* Historical Payouts Ledger */}
      {data && data.historical_payouts.length > 0 && (
        <Card className="p-6 bg-surface-primary border border-border-subtle shadow-md space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-ink-primary">
              Audited Payouts Ledger for this Circle ({data.historical_payouts.length})
            </h3>
            <Badge variant="neutral">Blockchain & Merkle Tracked</Badge>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="text-[11px] uppercase bg-surface-secondary text-ink-muted border-b border-border-subtle">
                <tr>
                  <th className="py-2.5 px-3">Cycle</th>
                  <th className="py-2.5 px-3">Recipient</th>
                  <th className="py-2.5 px-3">Amount</th>
                  <th className="py-2.5 px-3">Settlement UTR</th>
                  <th className="py-2.5 px-3">Rail</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-subtle">
                {data.historical_payouts.map((p: Payout) => (
                  <tr key={p.id} className="hover:bg-surface-secondary/40">
                    <td className="py-2.5 px-3 font-mono font-semibold text-emerald-400">
                      Cycle #{p.cycle_number}
                    </td>
                    <td className="py-2.5 px-3 font-semibold text-ink-primary">
                      {p.member_name || p.member}
                      <span className="block text-[10px] text-ink-muted font-mono">{p.member_reference}</span>
                    </td>
                    <td className="py-2.5 px-3 font-mono text-emerald-400">
                      PKR {parseFloat(p.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                    </td>
                    <td className="py-2.5 px-3 font-mono text-[11px] text-ink-muted">
                      {p.settlement_utr || "RAAST-LEGACY"}
                    </td>
                    <td className="py-2.5 px-3 uppercase text-[10px] text-ink-muted">
                      {p.settlement_rail || "raast_rtgs"}
                    </td>
                    <td className="py-2.5 px-3">
                      <Badge variant="emerald">DISBURSED</Badge>
                    </td>
                    <td className="py-2.5 px-3 text-right">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => {
                          setSelectedReceipt({
                            payout_id: p.id,
                            circle_name: data.pool.name,
                            circle_code: data.pool.code,
                            recipient_name: p.member_name || p.member,
                            recipient_reference: p.member_reference || "",
                            cycle_number: p.cycle_number,
                            amount: parseFloat(p.amount),
                            payout_date: p.payout_date,
                            status: p.status,
                            settlement_rail: p.settlement_rail || "raast_rtgs",
                            settlement_utr: p.settlement_utr || "RAAST-HIST-01",
                            recipient_iban: p.recipient_iban || "PK36MEZN...",
                            recipient_bank: p.recipient_bank || "Meezan Bank Limited",
                            secondary_approved_by: p.secondary_approved_by_username || "Compliance Officer",
                            secondary_approved_at: p.secondary_approved_at || p.created_at,
                            shariah_certificate_number: p.shariah_certificate_number || "CERT-QARD-2025",
                            biometric_auth_ref: p.biometric_auth_ref || "BIO-VERIFIED",
                            ceremony_hash: p.ceremony_hash || "SHA-256-RECORDED",
                            legal_entity: "Amanah Islamic Banking Window",
                          })
                          setIsReceiptModalOpen(true)
                        }}
                      >
                        📄 Voucher
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* Official Settlement Voucher Modal */}
      {selectedReceipt && (
        <Modal
          isOpen={isReceiptModalOpen}
          onClose={() => setIsReceiptModalOpen(false)}
          title="Official Shariah Settlement Voucher"
        >
          <div className="space-y-4 p-2 text-xs text-ink-primary">
            <div className="border-b border-border-subtle pb-3 flex justify-between items-start">
              <div>
                <div className="text-base font-bold text-emerald-400 font-mono">
                  AMANAH POOL OS • ISLAMIC BANKING
                </div>
                <div className="text-[11px] text-ink-muted">
                  SBP Islamic Banking Department Circular 03/2012 Certified
                </div>
              </div>
              <Badge variant="emerald">VERIFIED ZERO RIBA</Badge>
            </div>

            <div className="grid grid-cols-2 gap-3 py-2 border-b border-border-subtle text-[11px]">
              <div>
                <span className="text-ink-muted block">Circle Pool:</span>
                <span className="font-semibold">{selectedReceipt.circle_name} ({selectedReceipt.circle_code})</span>
              </div>
              <div>
                <span className="text-ink-muted block">Cycle Turn:</span>
                <span className="font-mono font-semibold">Cycle #{selectedReceipt.cycle_number}</span>
              </div>
              <div>
                <span className="text-ink-muted block">Recipient Member:</span>
                <span className="font-semibold">{selectedReceipt.recipient_name} ({selectedReceipt.recipient_reference})</span>
              </div>
              <div>
                <span className="text-ink-muted block">Settlement Date:</span>
                <span className="font-mono">{selectedReceipt.payout_date}</span>
              </div>
              <div>
                <span className="text-ink-muted block">Disbursed Principal Pot:</span>
                <span className="font-mono font-bold text-emerald-400 text-sm">
                  PKR {selectedReceipt.amount.toLocaleString(undefined, { minimumFractionDigits: 2 })}
                </span>
              </div>
              <div>
                <span className="text-ink-muted block">Bank Fee Absorption:</span>
                <span className="font-semibold text-emerald-400">100% Absorbed (PKR 0.00 Fee)</span>
              </div>
            </div>

            <div className="space-y-1.5 py-2 border-b border-border-subtle text-[11px] font-mono">
              <div className="flex justify-between">
                <span className="text-ink-muted">Settlement UTR:</span>
                <span className="text-emerald-300 font-semibold">{selectedReceipt.settlement_utr}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-muted">Recipient IBAN:</span>
                <span>{selectedReceipt.recipient_iban}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-muted">Settlement Bank:</span>
                <span>{selectedReceipt.recipient_bank}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-muted">Fatwa Certificate #:</span>
                <span className="text-emerald-400">{selectedReceipt.shariah_certificate_number}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-ink-muted">Biometric Auth:</span>
                <span>{selectedReceipt.biometric_auth_ref}</span>
              </div>
            </div>

            <div className="text-[10px] text-ink-muted space-y-1">
              <div>Cryptographic Ceremony Hash:</div>
              <div className="p-2 rounded bg-surface-secondary font-mono break-all text-[9px] text-ink-muted border border-border-subtle">
                {selectedReceipt.ceremony_hash}
              </div>
            </div>

            <div className="flex justify-between items-center pt-2">
              <Button variant="secondary" onClick={() => window.print()}>
                🖨️ Print Voucher
              </Button>
              <Button variant="primary" onClick={() => setIsReceiptModalOpen(false)}>
                Close
              </Button>
            </div>
          </div>
        </Modal>
      )}
    </div>
  )
}
