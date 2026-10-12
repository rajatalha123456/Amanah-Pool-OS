import { apiClient } from "./axios"

export interface ConsentRow {
  id: string
  purpose: string
  purpose_label: string
  status: "granted" | "withdrawn"
  granted_at: string
  method: string
  evidence_reference: string
  withdrawn_at: string | null
  withdrawal_reason: string
}

export async function fetchMyConsents(): Promise<ConsentRow[]> {
  return (await apiClient.get<ConsentRow[]>("participants/consents/mine/")).data
}

export async function withdrawConsent(id: string, reason: string): Promise<void> {
  await apiClient.post(`participants/consents/${id}/withdraw/`, { reason })
}

export async function fetchMyData(): Promise<unknown> {
  return (await apiClient.get("participants/consents/my-data/")).data
}
