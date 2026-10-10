import { apiClient } from "./axios"

export interface AuditSampleItem {
  id: string
  rank: number
  entity_type: string
  entity_id: string
  reference_code: string
  risk_score: number
  severity: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"
  title: string
  anomaly_reason: string
  suggested_audit_procedure: string
}

export interface AuditSamplingMetrics {
  shariah_risk: number
  financial_variance_risk: number
  operational_governance_risk: number
  total_pools_audited: number
  unpurified_count: number
  critical_exceptions_count: number
  allocation_runs_audited: number
}

export interface AuditSamplingResult {
  success: boolean
  composite_risk_score: number
  risk_tier: string
  compliance_opinion: string
  metrics: AuditSamplingMetrics
  sample_items: AuditSampleItem[]
  memorandum: string
  generated_at: string
}

export async function runAuditSamplingAnalysis(): Promise<AuditSamplingResult> {
  const response = await apiClient.post<AuditSamplingResult>("ai/audit-sampling/analyze/")
  return response.data
}
