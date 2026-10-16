import { apiClient } from "./axios"
import { pageParams, type Page } from "./pagination"
import type { DepositorStatement, Participant, ParticipantAccount } from "../types"

export async function fetchParticipants(page = 1): Promise<Page<Participant>> {
  const response = await apiClient.get<Page<Participant>>("participants/participants/", { params: pageParams(page) })
  return response.data
}

/** Accounts of the given participants (one page of the registry), at most 500. */
export async function fetchAccountsOfParticipants(participantIds: string[]): Promise<ParticipantAccount[]> {
  if (participantIds.length === 0) return []
  const response = await apiClient.get<Page<ParticipantAccount>>("participants/accounts/", {
    params: { participants: participantIds.join(","), ...pageParams(1, 500) },
  })
  return response.data.results
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


export interface NewParticipant {
  reference: string
  full_name: string
  participant_class: string
  email?: string
  cnic_ntn?: string
  iban?: string
  bank_name?: string
  tax_status?: string
  participant_type?: string
  registration_number?: string
  nominee_name?: string
  nominee_cnic?: string
  nominee_relationship?: string
}

export async function createParticipant(body: NewParticipant): Promise<Participant> {
  const response = await apiClient.post<Participant>("participants/participants/", body)
  return response.data
}

export async function createParticipantAccount(body: {
  participant: string
  pool: string
  account_number: string
  opened_date: string
}): Promise<ParticipantAccount> {
  const response = await apiClient.post<ParticipantAccount>("participants/accounts/", body)
  return response.data
}

export async function linkParticipantLogin(id: string, email: string): Promise<Participant> {
  const response = await apiClient.post<Participant>(`participants/participants/${id}/link-login/`, { email })
  return response.data
}
