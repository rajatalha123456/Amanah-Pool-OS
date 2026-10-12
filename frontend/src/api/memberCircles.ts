import { apiClient } from "./axios"

export interface MyCircle {
  member_id: string
  member_reference: string
  pool: string
  pool_code: string
  pool_name: string
  status: string
  payout_position: number | null
  rules: {
    version: number
    contribution_amount: string
    cycle_days: number
    schedule_note: string
    order_policy: string
    hardship_policy: string
    content_hash: string
    accepted: boolean
  } | null
  contributions: { cycle_number: number; amount: string; date: string; status: string; payment_reference: string }[]
  payouts: { cycle_number: number; amount: string; date: string; status: string }[]
  ledger: {
    cycle_number: number
    contributions_received: number
    collected: string
    payout: { recipient: string; amount: string; status: string; date: string } | null
  }[]
}

export async function fetchMyCircles(): Promise<MyCircle[]> {
  return (await apiClient.get<MyCircle[]>("circles/circle-members/my-circles/")).data
}

export async function acceptCircleRules(poolId: string, method: string, evidenceReference: string): Promise<void> {
  await apiClient.post("circles/circle-members/accept-rules/", { pool: poolId, method, evidence_reference: evidenceReference })
}

export interface MyProposal {
  id: string
  pool_name: string
  title: string
  description: string
  status: string
  voting_deadline: string
  my_vote: string | null
  can_vote: boolean
  tally: Record<string, number> | null
}

export async function fetchMyProposals(): Promise<MyProposal[]> {
  return (await apiClient.get<MyProposal[]>("circles/circle-members/my-proposals/")).data
}

export async function castMyVote(proposal: string, decision: string): Promise<void> {
  await apiClient.post("circles/circle-members/cast-vote/", { proposal, decision })
}
