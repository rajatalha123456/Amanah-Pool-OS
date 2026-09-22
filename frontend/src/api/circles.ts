import { apiClient } from "./axios"
import type {
  ArrearsRecord,
  CircleMember,
  Contribution,
  CreateCircleMemberInput,
  DisbursePayoutInput,
  FlagArrearsInput,
  GrantHardshipInput,
  Payout,
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
