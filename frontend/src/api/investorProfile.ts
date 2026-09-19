import { apiClient } from "./axios"
import type { InvestorProfile, InvestorProfileInput, VerifyKYCInput } from "../types"

export async function fetchInvestorProfile(capitalAccountId: string): Promise<InvestorProfile | null> {
  const response = await apiClient.get<InvestorProfile[]>("investments/investor-profiles/", {
    params: { capital_account: capitalAccountId },
  })
  return response.data[0] ?? null
}

export async function createInvestorProfile(data: InvestorProfileInput): Promise<InvestorProfile> {
  const response = await apiClient.post<InvestorProfile>("investments/investor-profiles/", data)
  return response.data
}

export async function updateInvestorProfile(
  id: string,
  data: InvestorProfileInput,
): Promise<InvestorProfile> {
  const response = await apiClient.patch<InvestorProfile>(`investments/investor-profiles/${id}/`, data)
  return response.data
}

export async function verifyInvestorKYC(id: string, data: VerifyKYCInput): Promise<InvestorProfile> {
  const response = await apiClient.post<InvestorProfile>(
    `investments/investor-profiles/${id}/verify-kyc/`,
    data,
  )
  return response.data
}