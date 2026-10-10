import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card } from "../Card"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import {
  fetchDrawRoomStatus,
  executeProvablyFairDraw,
  swapCircleTurns,
  type DrawRoomStatusResponse,
} from "../../api/circles"

interface DrawRoomConsoleProps {
  poolId: string
  onDrawExecuted?: () => void
  onDisburseRequested?: (memberId: string) => void
}

export function DrawRoomConsole({
  poolId,
  onDrawExecuted,
  onDisburseRequested,
}: DrawRoomConsoleProps) {
  const navigate = useNavigate()
  const [data, setData] = useState<DrawRoomStatusResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Ceremony Draw Modal
  const [isCeremonyOpen, setIsCeremonyOpen] = useState(false)
  const [isSpinning, setIsSpinning] = useState(false)
  const [spunMember, setSpunMember] = useState<string | null>(null)
  const [clientSeed, setClientSeed] = useState<string>(
    () => `entropy-${Math.random().toString(36).substring(2, 10)}`,
  )
  const [drawResult, setDrawResult] = useState<{
    server_seed: string
    provably_fair_hash: string
    message: string
  } | null>(null)

  // Turn Swap Modal
  const [isSwapModalOpen, setIsSwapModalOpen] = useState(false)
  const [swapMemberA, setSwapMemberA] = useState<string>("")
  const [swapMemberB, setSwapMemberB] = useState<string>("")
  const [swapReason, setSwapReason] = useState<string>(
    "Urgent family medical emergency advancement",
  )
  const [swapSuccessMsg, setSwapSuccessMsg] = useState<string | null>(null)
  const [isSwapping, setIsSwapping] = useState(false)

  async function loadStatus() {
    if (!poolId) return
    try {
      setIsLoading(true)
      setError(null)
      const res = await fetchDrawRoomStatus(poolId)
      setData(res)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load draw room status")
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    loadStatus()
  }, [poolId])

  async function handleExecuteDraw(forceReshuffle = false) {
    try {
      setIsSpinning(true)
      setDrawResult(null)

      // Visual shuffling animation effect
      const candidates = data?.rotation_ladder.map((m) => m.member_name) || ["Member"]
      let count = 0
      const interval = setInterval(() => {
        setSpunMember(candidates[Math.floor(Math.random() * candidates.length)])
        count++
        if (count > 15) {
          clearInterval(interval)
        }
      }, 100)

      const res = await executeProvablyFairDraw(poolId, clientSeed, forceReshuffle)

      setTimeout(async () => {
        setIsSpinning(false)
        setDrawResult({
          server_seed: res.server_seed,
          provably_fair_hash: res.provably_fair_hash,
          message: res.message,
        })
        await loadStatus()
        if (onDrawExecuted) onDrawExecuted()
      }, 2000)
    } catch (err: unknown) {
      setIsSpinning(false)
      setError(err instanceof Error ? err.message : "Draw execution failed")
    }
  }

  async function handleSwapSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!swapMemberA || !swapMemberB) return
    try {
      setIsSwapping(true)
      const res = await swapCircleTurns(poolId, swapMemberA, swapMemberB, swapReason)
      setSwapSuccessMsg(res.message)
      await loadStatus()
      setTimeout(() => {
        setIsSwapModalOpen(false)
        setSwapSuccessMsg(null)
      }, 1800)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Turn swap failed")
    } finally {
      setIsSwapping(false)
    }
  }

  function formatPKR(amount: number | undefined) {
    if (amount === undefined) return "₨ 0"
    return `₨ ${amount.toLocaleString("en-PK")}`
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center gap-2 py-12 text-ink-secondary">
        <Spinner className="h-6 w-6 text-gold-400" />
        <span className="text-sm">Connecting to Provably Fair Ceremony Engine...</span>
      </div>
    )
  }

  if (error || !data) {
    return (
      <Card className="border-red-500/30 bg-red-500/10">
        <p className="text-sm text-red-400">Error: {error || "Draw Room unavailable"}</p>
      </Card>
    )
  }

  const eligibleForSwap = data.rotation_ladder.filter((m) => m.status === "active")

  return (
    <div className="space-y-6">
      {/* Top Banner & Ceremony Hero */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Hero Card */}
        <div className="rounded-2xl border-2 border-gold-500/60 bg-gradient-to-br from-navy-900 via-navy-950 to-navy-900 p-6 shadow-2xl lg:col-span-2">
          <div className="flex items-center justify-between">
            <span className="rounded bg-gold-500/20 px-3 py-1 text-xs font-bold uppercase tracking-wider text-gold-400">
              BRD SCREEN 08 • ROTATION / DRAW ROOM
            </span>
            <span className="rounded border border-emerald-500/40 bg-emerald-500/10 px-2.5 py-0.5 text-xs font-semibold text-emerald-400">
              CYCLE #{data.current_cycle} ACTIVE
            </span>
          </div>

          <div className="mt-4 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <p className="text-xs font-medium text-ink-secondary uppercase">
                Active Turn Recipient (Payout Beneficiary)
              </p>
              <h2 className="mt-1 text-3xl font-extrabold tracking-tight text-white uppercase">
                {data.next_recipient?.member_name ?? "All Turns Completed"}
              </h2>
              <div className="mt-1 flex items-center gap-2 text-xs">
                <span className="font-mono text-gold-300">
                  {data.next_recipient?.member_reference ?? "—"}
                </span>
                <span className="text-ink-muted">•</span>
                <span className="font-medium text-ink-secondary">
                  Turn #{data.next_recipient?.payout_position ?? "—"} of {data.circle.total_members}
                </span>
              </div>
            </div>

            <div className="rounded-xl border border-emerald-500/30 bg-emerald-950/40 p-4 text-right">
              <span className="text-[11px] font-semibold text-emerald-400 uppercase">
                Turn Lump-Sum Pot
              </span>
              <p className="mt-1 text-2xl font-black text-emerald-300">
                {formatPKR(data.next_recipient?.pot_payout)}
              </p>
              <span className="text-[10px] text-ink-muted">
                {data.circle.total_members} members × {formatPKR(data.circle.monthly_contribution)}
              </span>
            </div>
          </div>

          {/* Action Row */}
          <div className="mt-6 flex flex-wrap items-center gap-3 border-t border-white/8 pt-4">
            {data.next_recipient && (
              <Button
                variant="primary"
                className="bg-emerald-600 px-5 py-2 text-xs font-semibold hover:bg-emerald-500"
                onClick={() => {
                  if (onDisburseRequested && data.next_recipient) {
                    onDisburseRequested(data.next_recipient.member_id)
                  } else {
                    navigate("/payout-clearing")
                  }
                }}
              >
                Verify & Release via Raast / 1LINK →
              </Button>
            )}

            <Button
              variant="secondary"
              className="border-gold-500/40 text-xs font-semibold text-gold-300 hover:bg-gold-500/10"
              onClick={() => setIsCeremonyOpen(true)}
            >
              🎲 Run Provably Fair Qur'ah (Lucky Draw)
            </Button>

            <Button
              variant="secondary"
              className="text-xs text-ink-secondary hover:text-ink-primary"
              onClick={() => setIsSwapModalOpen(true)}
            >
              ⇄ Mutual Hardship Turn Swap (Rule BR-007)
            </Button>
          </div>
        </div>

        {/* Right Provably Fair Shariah Seal */}
        <div className="rounded-2xl border border-white/10 bg-navy-900 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg">⚖️</span>
              <h3 className="text-xs font-bold uppercase tracking-wider text-ink-primary">
                Rule BR-007 Zero-Riba Guarantee
              </h3>
            </div>
            <p className="mt-2 text-xs text-ink-secondary leading-relaxed">
              Islamic ROSCA / Kameti consensus rule strictly prohibits any financial markup,
              bidding discount, or late penalty. All participants receive exactly their accumulated
              contributions under mutual Qard-Hasan.
            </p>

            <div className="mt-4 space-y-2 rounded-lg border border-white/5 bg-navy-950 p-3 text-[11px]">
              <div>
                <span className="text-ink-muted">Provably Fair Algorithm:</span>
                <p className="font-mono text-emerald-400">{data.provably_fair.algorithm}</p>
              </div>
              <div>
                <span className="text-ink-muted">Server Seed SHA-256 Digest:</span>
                <p className="font-mono text-[10px] text-ink-secondary truncate">
                  {data.provably_fair.server_seed_hash}
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 rounded border border-emerald-500/20 bg-emerald-500/5 p-2 text-center text-[10px] font-semibold text-emerald-400">
            ✓ Shariah Secretariat Provably Fair Seal Active
          </div>
        </div>
      </div>

      {/* Rotation Ladder Timeline Table */}
      <Card title="Circle Turn Rotation Ladder & Beneficiary Schedule">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-white/8 text-[11px] font-semibold tracking-wider text-ink-muted uppercase">
                <th className="py-2.5 px-3">Turn #</th>
                <th className="py-2.5 px-3">Member Details</th>
                <th className="py-2.5 px-3">Reference ID</th>
                <th className="py-2.5 px-3">Turn Status</th>
                <th className="py-2.5 px-3">Lump-Sum Payout</th>
                <th className="py-2.5 px-3 text-right">Mutual Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/5 text-xs">
              {data.rotation_ladder.map((item) => {
                const isCurrent =
                  data.next_recipient && data.next_recipient.member_id === item.member_id
                const isDisbursed = item.status === "paid_out"

                return (
                  <tr
                    key={item.member_id}
                    className={`transition-colors ${
                      isCurrent
                        ? "bg-gold-500/10 font-medium"
                        : isDisbursed
                          ? "bg-white/2 text-ink-muted"
                          : "hover:bg-white/3"
                    }`}
                  >
                    <td className="py-3 px-3 font-mono">
                      <span
                        className={`inline-flex h-6 w-6 items-center justify-center rounded-full font-bold ${
                          isCurrent
                            ? "bg-gold-500 text-navy-950 font-black shadow-md"
                            : isDisbursed
                              ? "bg-emerald-500/20 text-emerald-400"
                              : "bg-white/10 text-ink-secondary"
                        }`}
                      >
                        {item.payout_position ?? "—"}
                      </span>
                    </td>

                    <td className="py-3 px-3">
                      <div className="font-semibold text-ink-primary">{item.member_name}</div>
                      <span className="text-[10px] text-ink-muted">
                        Joined: {item.joined_date}
                      </span>
                    </td>

                    <td className="py-3 px-3 font-mono text-ink-secondary">
                      {item.member_reference}
                    </td>

                    <td className="py-3 px-3">
                      {isDisbursed && (
                        <span className="inline-flex items-center gap-1 rounded bg-emerald-500/20 px-2 py-0.5 text-[10px] font-bold text-emerald-400">
                          ✓ DISBURSED
                        </span>
                      )}
                      {isCurrent && (
                        <span className="inline-flex items-center gap-1 rounded bg-gold-500/20 px-2 py-0.5 text-[10px] font-bold text-gold-300 animate-pulse">
                          ⚡ ACTIVE BENEFICIARY
                        </span>
                      )}
                      {!isDisbursed && !isCurrent && (
                        <span className="rounded bg-white/5 px-2 py-0.5 text-[10px] text-ink-secondary">
                          UPCOMING TURN #{item.payout_position}
                        </span>
                      )}
                    </td>

                    <td className="py-3 px-3 font-mono font-medium text-emerald-400">
                      {formatPKR(item.pot_amount)}
                    </td>

                    <td className="py-3 px-3 text-right">
                      {!isDisbursed && (
                        <button
                          type="button"
                          onClick={() => {
                            setSwapMemberA(item.member_id)
                            setIsSwapModalOpen(true)
                          }}
                          className="rounded bg-white/5 px-2.5 py-1 text-[11px] text-ink-secondary transition-colors hover:bg-gold-500/20 hover:text-gold-300"
                        >
                          ⇄ Request Swap
                        </button>
                      )}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Provably Fair Qur'ah (Lucky Draw) Ceremony Modal */}
      {isCeremonyOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
          <div className="w-full max-w-lg rounded-2xl border border-gold-500/40 bg-navy-900 p-6 shadow-2xl text-center">
            <div className="flex items-center justify-between border-b border-white/8 pb-3">
              <span className="rounded bg-gold-500/20 px-2 py-0.5 text-xs font-bold text-gold-400">
                PROVABLY FAIR QUR'AH CEREMONY (قرعہ)
              </span>
              <button
                type="button"
                onClick={() => setIsCeremonyOpen(false)}
                className="text-ink-muted hover:text-ink-primary"
              >
                ✕
              </button>
            </div>

            {/* Live Spinner Box */}
            <div className="my-8 rounded-2xl border-2 border-gold-500/40 bg-gradient-to-b from-navy-950 via-navy-900 to-navy-950 p-8 shadow-inner">
              <p className="text-xs uppercase tracking-widest text-ink-muted">
                {isSpinning ? "Cryptographically Shuffling..." : "Randomized Recipient"}
              </p>

              <div className="mt-4 flex h-20 items-center justify-center">
                <span
                  className={`text-3xl font-black uppercase tracking-wide transition-all ${
                    isSpinning ? "text-gold-400 animate-bounce" : "text-emerald-400"
                  }`}
                >
                  {spunMember || data.next_recipient?.member_name || "Tap Draw to Spin"}
                </span>
              </div>

              {drawResult && (
                <div className="mt-4 rounded-lg bg-emerald-500/10 p-3 text-xs text-emerald-300">
                  <p className="font-semibold">{drawResult.message}</p>
                  <p className="mt-1 font-mono text-[10px] text-ink-muted truncate">
                    Seal: {drawResult.provably_fair_hash}
                  </p>
                </div>
              )}
            </div>

            {/* Entropy Inputs */}
            <div className="space-y-2 text-left text-xs">
              <label className="block text-ink-secondary">
                Client Entropy Seed (Generated locally in your browser):
              </label>
              <input
                type="text"
                value={clientSeed}
                onChange={(e) => setClientSeed(e.target.value)}
                className="w-full rounded border border-white/10 bg-navy-950 px-3 py-1.5 font-mono text-ink-primary focus:border-gold-500"
              />
              <span className="text-[10px] text-ink-muted">
                Ensures the server cannot predict or manipulate the turn sequence.
              </span>
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-white/8 pt-4">
              <Button
                variant="secondary"
                onClick={() => setIsCeremonyOpen(false)}
                disabled={isSpinning}
              >
                Close
              </Button>
              <Button
                variant="primary"
                className="bg-gold-600 font-bold hover:bg-gold-500"
                onClick={() => handleExecuteDraw(true)}
                disabled={isSpinning}
              >
                {isSpinning ? <Spinner className="h-4 w-4" /> : "⚡ Spin Provably Fair Draw"}
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Emergency Hardship Turn Swap Modal (Rule BR-007) */}
      {isSwapModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 backdrop-blur-md">
          <div className="w-full max-w-md rounded-2xl border border-white/10 bg-navy-900 p-6 shadow-2xl">
            <div className="flex items-center justify-between border-b border-white/8 pb-3">
              <h3 className="text-sm font-bold text-ink-primary uppercase tracking-wide">
                Mutual Consent Hardship Turn Swap
              </h3>
              <button
                type="button"
                onClick={() => setIsSwapModalOpen(false)}
                className="text-ink-muted hover:text-ink-primary"
              >
                ✕
              </button>
            </div>

            {swapSuccessMsg ? (
              <div className="my-6 rounded-lg bg-emerald-500/10 p-4 text-center text-xs text-emerald-400">
                <span className="text-xl">✓</span>
                <p className="mt-1 font-semibold">{swapSuccessMsg}</p>
              </div>
            ) : (
              <form onSubmit={handleSwapSubmit} className="mt-4 space-y-4 text-xs">
                <div>
                  <label className="block text-ink-secondary">Member Requesting Priority:</label>
                  <select
                    value={swapMemberA}
                    onChange={(e) => setSwapMemberA(e.target.value)}
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-3 py-1.5 text-ink-primary"
                    required
                  >
                    <option value="">Select Member A</option>
                    {eligibleForSwap.map((m) => (
                      <option key={m.member_id} value={m.member_id}>
                        {m.member_name} (Turn #{m.payout_position})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-ink-secondary">Member Agreeing to Swap:</label>
                  <select
                    value={swapMemberB}
                    onChange={(e) => setSwapMemberB(e.target.value)}
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-3 py-1.5 text-ink-primary"
                    required
                  >
                    <option value="">Select Member B</option>
                    {eligibleForSwap
                      .filter((m) => m.member_id !== swapMemberA)
                      .map((m) => (
                        <option key={m.member_id} value={m.member_id}>
                          {m.member_name} (Turn #{m.payout_position})
                        </option>
                      ))}
                  </select>
                </div>

                <div>
                  <label className="block text-ink-secondary">Hardship / Emergency Reason:</label>
                  <textarea
                    rows={2}
                    value={swapReason}
                    onChange={(e) => setSwapReason(e.target.value)}
                    className="mt-1 w-full rounded border border-white/10 bg-navy-950 px-3 py-1.5 text-ink-primary"
                    placeholder="e.g. Hospital admission expenses, school term deadline..."
                    required
                  />
                </div>

                <div className="rounded border border-gold-500/20 bg-gold-500/5 p-2.5 text-[11px] text-gold-300">
                  ⚖️ <strong>Rule BR-007 Compliance Attestation:</strong>
                  <br />
                  Both members explicitly affirm that this swap is executed under Islamic mutual
                  cooperation (Ta'awun) with <strong>ZERO monetary uplift or discount</strong>.
                </div>

                <div className="flex justify-end gap-2 border-t border-white/8 pt-3">
                  <Button
                    type="button"
                    variant="secondary"
                    onClick={() => setIsSwapModalOpen(false)}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="submit"
                    variant="primary"
                    className="bg-emerald-600 hover:bg-emerald-500"
                    disabled={isSwapping}
                  >
                    {isSwapping ? <Spinner className="h-4 w-4" /> : "Approve & Exchange Turns"}
                  </Button>
                </div>
              </form>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
