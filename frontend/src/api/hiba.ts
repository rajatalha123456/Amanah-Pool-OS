import { apiClient } from "./axios"

export interface HibaTierImpact {
  participant_class: string
  daily_funds: number
  weightage: number
  weighted_funds: number
  baseline_allocated_amount: number
  baseline_annualized_yield: number
  incremental_hiba_share: number
  revised_allocated_amount: number
  revised_annualized_yield: number
  yield_delta_bps: number
  gap_vs_benchmark: number
}

export interface HibaMetrics {
  distributable_amount: number
  total_weighted_funds: number
  contractual_mudarib_share: number
  contractual_mudarib_pct: number
  simulated_hiba_amount: number
  effective_mudarib_share: number
  effective_mudarib_pct: number
  baseline_depositor_share: number
  revised_depositor_share: number
  optimal_hiba_needed_for_kibor: number
  avg_baseline_yield: number
  avg_revised_yield: number
  net_yield_uplift_bps: number
}

export interface ShariahChecklistItem {
  id: string
  rule: string
  standard: string
  passed: boolean
  details: string
}

export interface HibaSimulationResponse {
  success: boolean
  run_id: string
  pool_id: string
  pool_name: string
  value_date: string
  status: string
  benchmark_rate: number
  metrics: HibaMetrics
  tiers: HibaTierImpact[]
  shariah_validation: {
    all_passed: boolean
    checklist: ShariahChecklistItem[]
  }
  alco_memo: string
}

export interface SimulateHibaParams {
  target_kibor?: number
  hiba_amount?: number
  mudarib_rate?: number
}

export interface ApplyHibaParams {
  hiba_amount: number
  justification?: string
}

export async function simulateHiba(
  runId: string,
  params?: SimulateHibaParams
): Promise<HibaSimulationResponse> {
  const response = await apiClient.post<HibaSimulationResponse>(
    `allocation/allocation-runs/${runId}/simulate-hiba/`,
    params || {}
  )
  return response.data
}

export async function applyHiba(
  runId: string,
  params: ApplyHibaParams
): Promise<{ success: boolean; run_id: string; hiba_amount: number; message: string }> {
  const response = await apiClient.post(
    `allocation/allocation-runs/${runId}/apply-hiba/`,
    params
  )
  return response.data
}
