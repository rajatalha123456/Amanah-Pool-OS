import { apiClient } from "./axios"
import type {
  ArrearsRecord,
  CircleMember,
  Contribution,
  CreateCircleMemberInput,
  DisbursePayoutInput,
  ExecuteCeremonyDisbursalInput,
  FlagArrearsInput,
  GrantHardshipInput,
  Payout,
  PayoutCeremonyReadiness,
  PayoutReceiptData,
  RecordContributionInput,
  RunDrawResponse,
} from "../types"

export async function fetchCircleMembers(poolId: string): Promise<CircleMember[]> {
  const response = await apiClient.get<CircleMember[]>("circles/circle-members/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function fetchCircleMember(memberId: string): Promise<CircleMember> {
  const response = await apiClient.get<CircleMember>(`circles/circle-members/${memberId}/`)
  return response.data
}

export async function fetchContributionsForPool(poolId: string): Promise<Contribution[]> {
  const response = await apiClient.get<Contribution[]>("circles/contributions/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function fetchContribution(contributionId: string): Promise<Contribution> {
  const response = await apiClient.get<Contribution>(`circles/contributions/${contributionId}/`)
  return response.data
}

export async function fetchContributionsForMember(memberId: string): Promise<Contribution[]> {
  const response = await apiClient.get<Contribution[]>("circles/contributions/", {
    params: { member: memberId },
  })
  return response.data
}

export async function fetchPayoutsForMember(memberId: string): Promise<Payout[]> {
  const response = await apiClient.get<Payout[]>("circles/payouts/", {
    params: { member: memberId },
  })
  return response.data
}

export async function fetchPayoutsForPool(poolId: string): Promise<Payout[]> {
  const response = await apiClient.get<Payout[]>("circles/payouts/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function createCircleMember(data: CreateCircleMemberInput): Promise<CircleMember> {
  const response = await apiClient.post<CircleMember>("circles/circle-members/", data)
  return response.data
}

export async function runDraw(poolId: string): Promise<RunDrawResponse> {
  const response = await apiClient.post<RunDrawResponse>(`circles/circle-members/run-draw/${poolId}/`)
  return response.data
}

export async function recordContribution(
  memberId: string,
  data: RecordContributionInput,
): Promise<Contribution> {
  const response = await apiClient.post<Contribution>(
    `circles/circle-members/${memberId}/record-contribution/`,
    data,
  )
  return response.data
}

export async function disbursePayout(memberId: string, data: DisbursePayoutInput): Promise<Payout> {
  const response = await apiClient.post<Payout>(
    `circles/circle-members/${memberId}/disburse-payout/`,
    data,
  )
  return response.data
}

export async function fetchArrearsRecordsForPool(poolId: string): Promise<ArrearsRecord[]> {
  const response = await apiClient.get<ArrearsRecord[]>("circles/arrears-records/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function flagArrears(memberId: string, data: FlagArrearsInput): Promise<ArrearsRecord> {
  const response = await apiClient.post<ArrearsRecord>(
    `circles/circle-members/${memberId}/flag-arrears/`,
    data,
  )
  return response.data
}

export async function grantHardship(
  arrearsId: string,
  data: GrantHardshipInput,
): Promise<ArrearsRecord> {
  const response = await apiClient.post<ArrearsRecord>(
    `circles/arrears-records/${arrearsId}/grant-hardship/`,
    data,
  )
  return response.data
}

export interface MemberHardshipRiskProfile {
  member_id: string
  member_name: string
  member_reference: string
  payout_position?: number | null
  has_received_payout: boolean
  total_contributions_paid: number
  risk_score: number
  risk_tier: "HIGH RISK" | "MODERATE RISK" | "HEALTHY"
  predictive_warning: string
  shariah_recommendation: string
  action_code: string
}

export interface CircleHardshipPredictionResult {
  success: boolean
  pool_id: string
  pool_name: string
  overall_health: "STABLE" | "AT_RISK" | "GUARDED"
  total_members_analyzed: number
  high_risk_count: number
  average_default_probability: number
  member_profiles: MemberHardshipRiskProfile[]
  generated_at: string
}

export async function predictCircleHardship(poolId: string): Promise<CircleHardshipPredictionResult> {
  const response = await apiClient.post<CircleHardshipPredictionResult>(`ai/circles/${poolId}/predict-hardship/`)
  return response.data
}

export interface DrawLadderItem {
  member_id: string
  member_reference: string
  member_name: string
  payout_position: number | null
  status: string
  status_label: "DISBURSED" | "READY_FOR_DRAW_DISBURSEMENT" | "UPCOMING"
  pot_amount: number
  joined_date: string
}

export interface DrawRoomStatusResponse {
  circle: {
    id: string
    name: string
    code: string
    status: string
    total_members: number
    monthly_contribution: number
    total_pot_payout: number
  }
  current_cycle: number
  next_recipient: {
    member_id: string
    member_name: string
    member_reference: string
    payout_position: number
    pot_payout: number
  } | null
  has_undrawn_members: boolean
  rotation_ladder: DrawLadderItem[]
  provably_fair: {
    server_seed_hash: string
    algorithm: string
    shariah_zero_riba_rule: string
    verification_endpoint: string
  }
}

export async function fetchDrawRoomStatus(poolId: string): Promise<DrawRoomStatusResponse> {
  const response = await apiClient.get<DrawRoomStatusResponse>(
    `circles/circle-members/draw-room-status/${poolId}/`,
  )
  return response.data
}

export async function executeProvablyFairDraw(
  poolId: string,
  clientSeed?: string,
  forceReshuffle = false,
): Promise<{
  status: string
  server_seed: string
  client_seed: string
  provably_fair_hash: string
  assignments: Array<{ member_id: string; position: number }>
  message: string
}> {
  const response = await apiClient.post(
    `circles/circle-members/execute-provably-fair-draw/${poolId}/`,
    { client_seed: clientSeed, force_reshuffle: forceReshuffle },
  )
  return response.data
}

export async function swapCircleTurns(
  poolId: string,
  memberAId: string,
  memberBId: string,
  reason?: string,
): Promise<{
  status: string
  message: string
  member_a: { id: string; new_position: number }
  member_b: { id: string; new_position: number }
}> {
  const response = await apiClient.post(
    `circles/circle-members/swap-turns/${poolId}/`,
    {
      member_a_id: memberAId,
      member_b_id: memberBId,
      reason,
    },
  )
  return response.data
}

export async function fetchCeremonyReadiness(poolId: string): Promise<PayoutCeremonyReadiness> {
  const response = await apiClient.get<PayoutCeremonyReadiness>(
    `circles/payouts/ceremony-readiness/${poolId}/`,
  )
  return response.data
}

export async function executeCeremonyDisbursal(
  poolId: string,
  input: ExecuteCeremonyDisbursalInput,
): Promise<{
  status: string
  message: string
  payout: Payout
  settlement_receipt: {
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
}> {
  const response = await apiClient.post(
    `circles/payouts/execute-ceremony/${poolId}/`,
    input,
  )
  return response.data
}

export async function fetchPayoutReceipt(payoutId: string): Promise<PayoutReceiptData> {
  const response = await apiClient.get<PayoutReceiptData>(
    `circles/payouts/${payoutId}/receipt/`,
  )
  return response.data
}


