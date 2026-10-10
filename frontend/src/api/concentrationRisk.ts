import { apiClient } from "./axios"

export interface ObligorRiskItem {
  obligor_name: string
  obligor_group: string
  sector: string
  credit_rating: string
  rating_agency: string
  is_sovereign: boolean
  is_related_party: boolean
  shariah_structure: string
  total_exposure: number
  portfolio_pct: number
  sbp_limit_pct: number
  utilization_pct: number
  headroom_amount: number
  excess_amount: number
  assets_count: number
  asset_references: string[]
  status: "safe" | "early_warning" | "breach"
}

export interface GroupRiskItem {
  group_name: string
  total_exposure: number
  portfolio_pct: number
  sbp_limit_pct: number
  utilization_pct: number
  obligors_count: number
  obligor_names: string[]
  status: "safe" | "early_warning" | "breach"
}

export interface SectorRiskItem {
  sector_name: string
  total_exposure: number
  portfolio_pct: number
  sbp_limit_pct: number
  utilization_pct: number
  headroom_amount: number
  excess_amount: number
  assets_count: number
  status: "safe" | "early_warning" | "breach"
}

export interface PrudentialScorecardItem {
  regulation: string
  description: string
  statutory_limit: string
  current_value: string
  passed: boolean
  status: "compliant" | "warning" | "breach"
}

export interface ConcentrationRiskAnalysis {
  success: boolean
  pool_id: string
  pool_name: string
  total_portfolio_exposure: number
  asset_count: number
  obligors: ObligorRiskItem[]
  groups: GroupRiskItem[]
  sectors: SectorRiskItem[]
  prudential_scorecard: PrudentialScorecardItem[]
  breach_summary: {
    breaches_count: number
    early_warnings_count: number
    safe_count: number
    highest_obligor_utilization: number
    highest_sector_utilization: number
  }
  as_of_timestamp: string
}

export interface RemediationSubmissionPayload {
  target_name: string
  target_type: "obligor" | "sector"
  current_exposure: number
  excess_amount: number
  action_note: string
  pool_id?: string
}

export interface RemediationSubmissionResult {
  success: boolean
  exception_case_id: string
  case_severity: string
  case_title: string
  statutory_deadline: string
  plan: {
    target_name: string
    target_type: string
    current_exposure: number
    excess_amount: number
    recommended_sell_down: number
    statutory_deadline: string
    official_memo: string
    action_steps: string[]
  }
}

export interface StressTestResult {
  success: boolean
  deposit_runoff_pct: number
  baseline_portfolio_exposure: number
  stressed_portfolio_exposure: number
  post_stress_breaches_count: number
  incremental_breaches: number
  stressed_obligors: {
    obligor_name: string
    pre_stress_pct: number
    post_stress_pct: number
    pct_delta: number
    sbp_limit_pct: number
    stressed_utilization_pct: number
    status: "safe" | "early_warning" | "breach"
  }[]
}

export async function fetchConcentrationRisk(poolId?: string): Promise<ConcentrationRiskAnalysis> {
  const params: Record<string, string> = {}
  if (poolId) {
    params.pool_id = poolId
  }
  const response = await apiClient.get<ConcentrationRiskAnalysis>("pools/assets/concentration-risk/", {
    params,
  })
  return response.data
}

export async function submitRemediationPlan(
  payload: RemediationSubmissionPayload,
): Promise<RemediationSubmissionResult> {
  const response = await apiClient.post<RemediationSubmissionResult>(
    "pools/assets/remediation-plan/",
    payload,
  )
  return response.data
}

export async function runConcentrationStressTest(
  depositRunoffPct: number,
  poolId?: string,
): Promise<StressTestResult> {
  const response = await apiClient.post<StressTestResult>("pools/assets/stress-test/", {
    deposit_runoff_pct: depositRunoffPct,
    pool_id: poolId,
  })
  return response.data
}
