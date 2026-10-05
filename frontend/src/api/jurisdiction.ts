import { apiClient } from "./axios"
import type { JurisdictionRulePack } from "../types"

export async function fetchJurisdictionRulePacks(): Promise<JurisdictionRulePack[]> {
  const response = await apiClient.get<JurisdictionRulePack[]>("products/jurisdiction-rule-packs/")
  return response.data
}

export async function fetchJurisdictionRulePackDetail(id: string): Promise<JurisdictionRulePack> {
  const response = await apiClient.get<JurisdictionRulePack>(`products/jurisdiction-rule-packs/${id}/`)
  return response.data
}

export async function createJurisdictionRulePack(
  data: Partial<JurisdictionRulePack>,
): Promise<JurisdictionRulePack> {
  const response = await apiClient.post<JurisdictionRulePack>("products/jurisdiction-rule-packs/", data)
  return response.data
}

export async function updateJurisdictionRulePack(
  id: string,
  data: Partial<JurisdictionRulePack>,
): Promise<JurisdictionRulePack> {
  const response = await apiClient.patch<JurisdictionRulePack>(
    `products/jurisdiction-rule-packs/${id}/`,
    data,
  )
  return response.data
}

export async function activateJurisdictionRulePack(
  id: string,
  isDefault = false,
): Promise<JurisdictionRulePack> {
  const response = await apiClient.post<JurisdictionRulePack>(
    `products/jurisdiction-rule-packs/${id}/activate/`,
    { is_default: isDefault },
  )
  return response.data
}
