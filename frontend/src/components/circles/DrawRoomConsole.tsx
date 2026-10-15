import { useEffect, useState } from "react"
import { useNavigate } from "react-router-dom"
import { Card } from "../Card"
import { Button } from "../Button"
import { Spinner } from "../Spinner"
import { commitCircleDraw, executeCircleDraw } from "../../api/circleGovernance"
import { extractErrorMessage } from "../../api/errors"
import {
  fetchDrawRoomStatus,
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
  const [isWorking, setIsWorking] = useState(false)
  const [clientSeed, setClientSeed] = useState<string>("")
  const [drawResult, setDrawResult] = useState<{
    server_seed: string
    provably_fair_hash: string
    message: string
  } | null>(null)

  // Turn Swap Modal
  const [isSwapModalOpen, setIsSwapModalOpen] = useState(false)
  const [swapMemberA, setSwapMemberA] = useState<string>("")
  const [swapMemberB, setSwapMemberB] = useState<string>("")
  const [swapReason, setSwapReason] = useState<string>("")
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

  // Step 1: seal. The server fixes its secret and publishes only its hash; nobody can change the outcome after this.
  async function handleCommit() {
    setIsWorking(true)
    setError(null)
    try {
      await commitCircleDraw(poolId)
      await loadStatus()
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Could not seal the draw"))
    } finally {
      setIsWorking(false)
    }
  }

  // Step 2: reveal. The members' own seed is added, the order is computed and the server secret is published.
  async function handleReveal() {
    const drawId = data?.provably_fair.draw_id
    if (!drawId) return
    setIsWorking(true)
    setError(null)
    try {
      const res = await executeCircleDraw(drawId, clientSeed)
      setDrawResult({
        server_seed: res.server_seed ?? "",
        provably_fair_hash: res.result_hash ?? "",
        message: "Draw revealed. Anyone can recompute the order from the two seeds (Rules, Draw & Closure > Verify).",
      })
      setClientSeed("")
      await loadStatus()
      if (onDrawExecuted) onDrawExecuted()
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Draw execution failed"))
    } finally {
      setIsWorking(false)
    }
  }

  async function handleSwapSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!swapMemberA || !swapMemberB) return
    try {
      setIsSwapping(true)
      const consent = window.prompt("Reference to BOTH members' recorded consent (e.g. signed form / OTP refs)")
      if (!consent) {
        setIsSwapping(false)
        return
      }
      const res = await swapCircleTurns(poolId, swapMemberA, swapMemberB, swapReason, consent)
      setSwapSuccessMsg(res.message)
      await loadStatus()
      setTimeout(() => {
        setIsSwapModalOpen(false)
        setSwapSuccessMsg(null)
      }, 1800)
    } catch (err: unknown) {
      setError(extractErrorMessage(err, "Turn swap failed"))
    } finally {
      setIsSwapping(false)
    }
  }

  function formatPKR(amount: number | null | undefined) {
    if (amount === undefined || amount === null) return "— (publish circle rules)"
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

  const committed = data.provably_fair.draw_status === "committed"
  const eligibleForSwap = data.rotation_ladder.filter((m) => m.status === "active")

  return (
    <div className="space-y-6">
      {/* Top Banner & Ceremony Hero */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left Hero Card */}
        <div className="rounded-2xl border-2 border-gold-500/60 bg-gradient-to-br from-navy-900 via-navy-950 to-navy-900 p-6 shadow-2xl lg:col-span-2">
          <div className="flex items-center justify-between">
            <span className="rounded bg-gold-500/20 px-3 py-1 text-xs font-bold uppercase tracking-wider text-gold-400">
              ROTATION / DRAW ROOM
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
              🎲 Draw ceremony (seal, then reveal)
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
                  {data.provably_fair.server_seed_hash ?? "No draw committed yet"}
                </p>
              </div>
            </div>
          </div>

          <div className="mt-4 rounded border border-emerald-500/20 bg-emerald-500/5 p-2 text-center text-[10px] font-semibold text-emerald-400">
            Draw status: {data.provably_fair.draw_status ?? "none yet"} - verify it in Rules, Draw & Closure
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

            {/* Status box */}
            <div className="my-8 rounded-2xl border-2 border-gold-500/40 bg-gradient-to-b from-navy-950 via-navy-900 to-navy-950 p-8 shadow-inner">
              <p className="text-xs uppercase tracking-widest text-ink-muted">
                Draw status
              </p>

              <div className="mt-4 flex h-20 items-center justify-center">
                <span className="text-xl font-black tracking-wide text-emerald-400">
                  {committed ? "Sealed: waiting for the members' seed" : "Not sealed yet"}
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

            {/* The two steps */}
            <div className="space-y-3 text-left text-xs">
              <div className="rounded border border-white/10 bg-navy-950 p-3">
                <p className="font-semibold text-ink-primary">Step 1: Seal the draw</p>
                <p className="mt-1 text-ink-secondary">
                  The server fixes a secret and shows only its fingerprint. After this nobody, including the organiser, can
                  change the result.
                </p>
                <p className="mt-2 break-all font-mono text-[10px] text-emerald-400">
                  {data.provably_fair.server_seed_hash ?? "Not sealed yet"}
                </p>
                <Button className="mt-2" size="sm" variant="secondary" onClick={() => void handleCommit()} disabled={isWorking || committed}>
                  {committed ? "Sealed" : isWorking ? <Spinner className="h-4 w-4" /> : "Seal the draw"}
                </Button>
              </div>

              <div className={`rounded border border-white/10 bg-navy-950 p-3 ${committed ? "" : "opacity-50"}`}>
                <p className="font-semibold text-ink-primary">Step 2: Reveal with the members' seed</p>
                <label className="mt-1 block text-ink-secondary" htmlFor="draw-client-seed">
                  Seed chosen by the members (at least 4 characters, for example words they all agree on):
                </label>
                <input
                  id="draw-client-seed"
                  type="text"
                  value={clientSeed}
                  onChange={(e) => setClientSeed(e.target.value)}
                  disabled={!committed}
                  className="mt-1 w-full rounded border border-white/10 bg-navy-900 px-3 py-1.5 font-mono text-ink-primary focus:border-gold-500"
                />
                <Button
                  className="mt-2"
                  size="sm"
                  variant="primary"
                  onClick={() => void handleReveal()}
                  disabled={isWorking || !committed || clientSeed.trim().length < 4}
                >
                  {isWorking ? <Spinner className="h-4 w-4" /> : "Reveal the draw"}
                </Button>
              </div>
              {error && <p className="text-red-400">{error}</p>}
            </div>

            <div className="mt-6 flex justify-end gap-2 border-t border-white/8 pt-4">
              <Button variant="secondary" onClick={() => setIsCeremonyOpen(false)} disabled={isWorking}>
                Close
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
                    placeholder="The reason the two members gave (written down in their own words)"
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
