import { apiClient } from "./axios"
import type { CircleClosurePreview, CircleDrawRecord, CircleRulesSummary } from "../types"

export async function fetchRulesSummary(poolId: string): Promise<CircleRulesSummary> {
  return (await apiClient.get<CircleRulesSummary>("circles/rules/summary/", { params: { pool: poolId } })).data
}

export async function publishCircleRules(
  poolId: string,
  data: { contribution_amount: string; cycle_days: string; order_policy: string; hardship_policy: string; schedule_note: string; first_due_date?: string },
): Promise<void> {
  await apiClient.post("circles/rules/publish/", { pool: poolId, ...data })
}

export async function acceptCircleRules(memberId: string, method: string, evidenceReference: string): Promise<void> {
  await apiClient.post("circles/rules/accept/", { member: memberId, method, evidence_reference: evidenceReference })
}

export async function fetchCircleDraws(poolId: string): Promise<CircleDrawRecord[]> {
  return (await apiClient.get<CircleDrawRecord[]>("circles/draws/", { params: { pool: poolId } })).data
}

export async function commitCircleDraw(poolId: string): Promise<CircleDrawRecord> {
  return (await apiClient.post<CircleDrawRecord>("circles/draws/commit/", { pool: poolId })).data
}

export async function executeCircleDraw(
  drawId: string,
  clientSeed: string,
): Promise<CircleDrawRecord & { server_seed?: string; result_hash?: string }> {
  return (await apiClient.post<CircleDrawRecord & { server_seed?: string; result_hash?: string }>(`circles/draws/${drawId}/execute/`, { client_seed: clientSeed })).data
}

export async function verifyCircleDraw(drawId: string): Promise<{ verified: boolean }> {
  return (await apiClient.get<{ verified: boolean }>(`circles/draws/${drawId}/verify/`)).data
}

export async function fetchClosurePreview(poolId: string): Promise<CircleClosurePreview> {
  return (await apiClient.get<CircleClosurePreview>("circles/closures/preview/", { params: { pool: poolId } })).data
}

export async function prepareCircleClosure(poolId: string, resolutionNote: string): Promise<void> {
  await apiClient.post("circles/closures/prepare/", { pool: poolId, resolution_note: resolutionNote })
}

export async function closeCircle(poolId: string): Promise<void> {
  await apiClient.post("circles/closures/close/", { pool: poolId })
}
