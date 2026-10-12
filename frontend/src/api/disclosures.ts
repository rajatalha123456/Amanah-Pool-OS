import { apiClient } from "./axios"
import type { PoolDisclosureRecord } from "../types"

export async function fetchDisclosures(poolId: string): Promise<PoolDisclosureRecord[]> {
  return (await apiClient.get<PoolDisclosureRecord[]>("investments/disclosures/", { params: { pool: poolId } })).data
}

export async function publishDisclosure(
  poolId: string,
  data: { risk_warnings: string; fee_statement: string; summary: string },
): Promise<PoolDisclosureRecord> {
  return (await apiClient.post<PoolDisclosureRecord>("investments/disclosures/publish/", { pool: poolId, ...data })).data
}

export async function approveDisclosure(disclosureId: string): Promise<void> {
  await apiClient.post(`investments/disclosures/${disclosureId}/approve/`)
}

export async function acknowledgeDisclosure(
  disclosureId: string,
  accountId: string,
  method: string,
  evidenceReference: string,
): Promise<void> {
  await apiClient.post(`investments/disclosures/${disclosureId}/acknowledge/`, {
    capital_account: accountId,
    method,
    evidence_reference: evidenceReference,
    risk_acknowledged: true,
  })
}

export async function fetchSubscriptionStatus(accountId: string): Promise<{ may_subscribe: boolean; reason: string }> {
  return (
    await apiClient.get<{ may_subscribe: boolean; reason: string }>("investments/disclosures/subscription-status/", {
      params: { capital_account: accountId },
    })
  ).data
}

export interface PoolTerms {
  product: string
  operating_model: string
  contract: { type: string; name: string; version: string }
  profit_sharing: {
    investor_share_pct: number
    manager_share_pct: number
    wakalah_fee_pct: number
    effective_from: string
  } | null
  reserve_policy: Record<string, { rate_pct: number; cap_pct: number; active: boolean }>
  redemption: { notice_days: number; gate_pct_per_30_days: string }
  shariah_decision: { code: string; title: string } | null
  jurisdiction_rule_pack: { code: string; name: string; version: string } | null
  base_currency: string
}

/** The terms of a pool as they are recorded right now (the same data a published disclosure seals). */
export async function fetchPoolTerms(poolId: string): Promise<PoolTerms> {
  return (await apiClient.get<PoolTerms>("investments/disclosures/preview/", { params: { pool: poolId } })).data
}
