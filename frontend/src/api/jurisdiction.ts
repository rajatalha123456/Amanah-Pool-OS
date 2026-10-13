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

/** A rule pack change is only PROPOSED (HTTP 202); a different finance checker or the authorized signatory approves it. */
export async function createJurisdictionRulePack(
  data: Partial<JurisdictionRulePack> & { change_reason: string },
): Promise<void> {
  await apiClient.post("products/jurisdiction-rule-packs/", data)
}

export async function updateJurisdictionRulePack(
  id: string,
  data: Partial<JurisdictionRulePack> & { change_reason: string },
): Promise<void> {
  await apiClient.patch(`products/jurisdiction-rule-packs/${id}/`, data)
}

/** Proposes activating a rule pack (and optionally making it the default); a different approver applies it. */
export async function activateJurisdictionRulePack(
  id: string,
  isDefault = false,
  changeReason = "",
): Promise<void> {
  await apiClient.post(`products/jurisdiction-rule-packs/${id}/activate/`, {
    is_default: isDefault,
    change_reason: changeReason,
  })
}
