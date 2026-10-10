import { apiClient } from "./axios"
import type { DepositorStatement, Participant, ParticipantAccount } from "../types"

export async function fetchParticipants(): Promise<Participant[]> {
  const response = await apiClient.get<Participant[]>("participants/participants/")
  return response.data
}

export async function fetchParticipantAccounts(poolId?: string): Promise<ParticipantAccount[]> {
  const response = await apiClient.get<ParticipantAccount[]>("participants/accounts/", {
    params: poolId ? { pool: poolId } : undefined,
  })
  return response.data
}

export async function verifyParticipantKyc(id: string, note?: string): Promise<Participant> {
  const response = await apiClient.post<Participant>(`participants/participants/${id}/verify-kyc/`, { note })
  return response.data
}

export async function rejectParticipantKyc(id: string, note?: string): Promise<Participant> {
  const response = await apiClient.post<Participant>(`participants/participants/${id}/reject-kyc/`, { note })
  return response.data
}

/** Self-service: the signed-in investor/member's own statements only. */
export async function fetchMyStatements(): Promise<DepositorStatement[]> {
  const response = await apiClient.get<DepositorStatement[]>("allocation/allocation-runs/my-statements/")
  return response.data
}

