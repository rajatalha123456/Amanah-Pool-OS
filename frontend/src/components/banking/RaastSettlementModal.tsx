import { useState } from "react"
import { Modal } from "../Modal"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import { Badge } from "../Badge"
import { processBankingSettlement, type BankingSettlementResult } from "../../api/banking"
import { extractErrorMessage } from "../../api/errors"

interface RaastSettlementModalProps {
  amount: number | string
  senderTitle: string
  senderIban?: string
  recipientTitle?: string
  recipientIban?: string
  purpose: string
  mode?: "collection" | "disbursement"
  onClose: () => void
  onSuccess: (result: BankingSettlementResult) => void
}

type Step = "confirm" | "processing" | "receipt"

export function RaastSettlementModal({
  amount,
  senderTitle,
  senderIban = "PK92MEZN0001928172601",
  recipientTitle = "Amanah Central Escrow Vault",
  recipientIban = "PK55AMAN0000109928172601",
  purpose,
  mode = "collection",
  onClose,
  onSuccess,
}: RaastSettlementModalProps) {
  const [step, setStep] = useState<Step>("confirm")
  const [channel, setChannel] = useState<"RAAST_P2M" | "1LINK_IBFT">("RAAST_P2M")
  const [hopIndex, setHopIndex] = useState(0)
  const [receipt, setReceipt] = useState<BankingSettlementResult | null>(null)
  const [error, setError] = useState("")

  const hops = [
    "Validating Source Account & 1LINK Title Directory...",
    "Routing via SBP Raast Central Clearing Switch...",
    "Executing Real-Time Gross Settlement (RTGS)...",
    "Generating Cryptographic RRN & Audit STAN...",
  ]

  async function handleExecuteSettlement() {
    setStep("processing")
    setError("")
    setHopIndex(0)

    // Simulate animated switch progression
    const interval = setInterval(() => {
      setHopIndex((prev) => (prev < hops.length - 1 ? prev + 1 : prev))
    }, 600)

    try {
      const res = await processBankingSettlement({
        amount,
        source_title: mode === "collection" ? senderTitle : recipientTitle,
        source_iban: mode === "collection" ? senderIban : recipientIban,
        destination_title: mode === "collection" ? recipientTitle : senderTitle,
        destination_iban: mode === "collection" ? recipientIban : senderIban,
        channel,
        purpose,
      })

      clearInterval(interval)
      setHopIndex(hops.length - 1)
      setTimeout(() => {
        setReceipt(res)
        setStep("receipt")
        onSuccess(res)
      }, 700)
    } catch (err) {
      clearInterval(interval)
      setError(extractErrorMessage(err, "Banking Switch Settlement Failed."))
      setStep("confirm")
    }
  }

  return (
    <Modal
      title={
        step === "receipt"
          ? "SBP Raast Electronic Settlement Receipt"
          : "SBP Raast / 1LINK Banking Rails Gateway"
      }
      onClose={onClose}
    >
      <div className="space-y-4">
        <div role="note" className="rounded-md border border-amber-500/40 bg-amber-950/30 px-3 py-2 text-xs font-semibold text-amber-300">
          SIMULATION MODE — no real Raast/1LINK transfer is made and no funds move.
        </div>
        {step === "confirm" && (
          <div className="space-y-4 text-xs">
            <div className="rounded-lg border border-emerald-500/30 bg-emerald-950/20 p-3.5 text-ink-primary">
              <div className="flex items-center justify-between mb-2">
                <span className="font-semibold text-emerald-400 uppercase tracking-wider text-[11px]">
                  Real-Time Settlement Parameters
                </span>
                <Badge variant="emerald">ISO 20022 Enabled</Badge>
              </div>
              <div className="grid grid-cols-2 gap-2 pt-1 border-t border-white/8 text-[11px]">
                <div>
                  <span className="text-ink-muted block">Transaction Amount:</span>
                  <span className="text-lg font-bold text-white">
                    PKR {Number(amount).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                  </span>
                </div>
                <div>
                  <span className="text-ink-muted block">Settlement Purpose:</span>
                  <span className="font-medium text-ink-primary">{purpose}</span>
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-lg bg-navy-900 border border-white/5 space-y-1">
                <span className="text-ink-muted block text-[10px] uppercase font-semibold">
                  {mode === "collection" ? "Debiting Account (Sender):" : "Pool Escrow Vault:"}
                </span>
                <p className="font-semibold text-white">{senderTitle}</p>
                <p className="font-mono text-[10px] text-ink-secondary">{senderIban}</p>
              </div>

              <div className="p-3 rounded-lg bg-navy-900 border border-white/5 space-y-1">
                <span className="text-ink-muted block text-[10px] uppercase font-semibold">
                  {mode === "collection" ? "Crediting Escrow (Receiver):" : "Crediting Member Account:"}
                </span>
                <p className="font-semibold text-white">{recipientTitle}</p>
                <p className="font-mono text-[10px] text-ink-secondary">{recipientIban}</p>
              </div>
            </div>

            <div>
              <label className="mb-1.5 block font-semibold text-ink-secondary uppercase text-[10px]">
                Select Clearing Channel Rail:
              </label>
              <div className="grid grid-cols-2 gap-2">
                <button
                  type="button"
                  onClick={() => setChannel("RAAST_P2M")}
                  className={`p-2.5 rounded-lg border text-left transition-all ${
                    channel === "RAAST_P2M"
                      ? "border-emerald-500 bg-emerald-950/40 text-emerald-400"
                      : "border-white/10 bg-navy-900 text-ink-secondary hover:border-white/20"
                  }`}
                >
                  <p className="font-bold text-xs">SBP Raast Instant</p>
                  <p className="text-[10px] text-ink-muted mt-0.5">Central Bank Direct Settlement (0% Fee)</p>
                </button>

                <button
                  type="button"
                  onClick={() => setChannel("1LINK_IBFT")}
                  className={`p-2.5 rounded-lg border text-left transition-all ${
                    channel === "1LINK_IBFT"
                      ? "border-emerald-500 bg-emerald-950/40 text-emerald-400"
                      : "border-white/10 bg-navy-900 text-ink-secondary hover:border-white/20"
                  }`}
                >
                  <p className="font-bold text-xs">1LINK IBFT Switch</p>
                  <p className="text-[10px] text-ink-muted mt-0.5">Inter-Bank Switch Network</p>
                </button>
              </div>
            </div>

            {error && <p className="text-xs text-rose-400">{error}</p>}

            <div className="flex justify-end gap-2 pt-2 border-t border-white/8">
              <Button type="button" variant="secondary" onClick={onClose}>
                Cancel
              </Button>
              <Button type="button" variant="primary" onClick={handleExecuteSettlement}>
                ⚡ Confirm & Route Payment
              </Button>
            </div>
          </div>
        )}

        {step === "processing" && (
          <div className="py-8 text-center space-y-6">
            <Spinner className="h-10 w-10 mx-auto text-emerald-400" />
            <div className="space-y-1">
              <h4 className="text-sm font-bold text-white">Communicating with Central Banking Rails</h4>
              <p className="text-xs text-ink-secondary font-mono">{hops[hopIndex]}</p>
            </div>

            <div className="max-w-xs mx-auto space-y-2 text-left text-xs bg-navy-950/80 p-3.5 rounded-lg border border-white/5">
              {hops.map((hop, i) => (
                <div key={i} className="flex items-center gap-2">
                  {i < hopIndex ? (
                    <span className="text-emerald-400 font-bold text-xs">✓</span>
                  ) : i === hopIndex ? (
                    <span className="inline-block h-2 w-2 rounded-full bg-emerald-400 animate-ping" />
                  ) : (
                    <span className="text-ink-muted text-xs">○</span>
                  )}
                  <span className={`text-[11px] ${i <= hopIndex ? "text-ink-primary font-medium" : "text-ink-muted"}`}>
                    {hop.split("...")[0]}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {step === "receipt" && receipt && (
          <div className="space-y-4 text-xs">
            <div className="rounded-xl border border-emerald-500/40 bg-navy-950 p-5 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 right-0 transform translate-x-4 -translate-y-4 opacity-5">
                <span className="text-9xl font-black text-emerald-400">SBP</span>
              </div>

              <div className="flex items-center justify-between pb-3 border-b border-white/10">
                <div>
                  <p className="text-[10px] font-bold tracking-widest text-emerald-400 uppercase">
                    STATE BANK OF PAKISTAN
                  </p>
                  <h4 className="text-sm font-extrabold text-white">Raast Electronic Transfer Slip</h4>
                </div>
                <Badge variant="emerald">SETTLED (CODE 00)</Badge>
              </div>

              <div className="my-4 text-center py-2 bg-emerald-950/20 rounded border border-emerald-500/20">
                <span className="text-[10px] text-ink-muted uppercase tracking-wider block">
                  Amount Transferred & Reconciled
                </span>
                <span className="text-2xl font-black text-emerald-400">
                  PKR {receipt.amount}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-2.5 text-[11px] border-b border-white/8 pb-3">
                <div>
                  <span className="text-ink-muted block text-[10px]">Retrieval Ref No (RRN):</span>
                  <span className="font-mono font-bold text-white">{receipt.rrn}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px]">System Trace (STAN):</span>
                  <span className="font-mono font-bold text-white">{receipt.stan}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px]">End-to-End ID (E2E-ID):</span>
                  <span className="font-mono text-ink-secondary text-[10px]">{receipt.e2e_id}</span>
                </div>
                <div>
                  <span className="text-ink-muted block text-[10px]">Authorization Code:</span>
                  <span className="font-mono text-emerald-400">{receipt.auth_code}</span>
                </div>
              </div>

              <div className="pt-3 text-[10px] text-ink-muted space-y-1">
                <p>
                  <span className="text-ink-secondary font-semibold">Debited:</span> {receipt.source.account_title} ({receipt.source.bank_name})
                </p>
                <p>
                  <span className="text-ink-secondary font-semibold">Credited:</span> {receipt.beneficiary.account_title} ({receipt.beneficiary.iban})
                </p>
                <p>
                  <span className="text-ink-secondary font-semibold">Timestamp:</span> {receipt.settled_at}
                </p>
              </div>
            </div>

            <div className="flex justify-between items-center pt-2">
              <span className="text-[10px] text-emerald-400/80 font-mono">
                ✓ SBP Settlement Verified
              </span>
              <Button type="button" variant="primary" onClick={onClose} className="text-xs">
                Done / Close Receipt
              </Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  )
}
