import { apiClient } from "./axios"
import type { PeriodCloseChecklist, PeriodCloseStatus } from "../types"

export interface CreatePeriodCloseInput {
  pool: string
  period_start: string
  period_end: string
  checklist_data?: Record<string, boolean>
  checklist_items?: Record<string, boolean>
  notes?: string
}

export async function fetchPeriodCloseChecklists(poolId?: string): Promise<PeriodCloseChecklist[]> {
  const params: Record<string, string> = {}
  if (poolId) params.pool = poolId
  const response = await apiClient.get<PeriodCloseChecklist[]>("pools/period-closes/", { params })
  return response.data
}

export async function fetchPeriodCloseChecklistDetail(id: string): Promise<PeriodCloseChecklist> {
  const response = await apiClient.get<PeriodCloseChecklist>(`pools/period-closes/${id}/`)
  return response.data
}

export async function createPeriodCloseChecklist(
  data: CreatePeriodCloseInput,
): Promise<PeriodCloseChecklist> {
  const payload = {
    pool: data.pool,
    period_start: data.period_start,
    period_end: data.period_end,
    checklist_data: data.checklist_data || data.checklist_items || {
      reconciled: true,
      shariah_parameters_sealed: true,
      exceptions_cleared: true,
      allocation_signed: true,
      journals_posted: true,
    },
    decision_note: data.notes || "",
  }
  const response = await apiClient.post<PeriodCloseChecklist>("pools/period-closes/", payload)
  return response.data
}

export async function updatePeriodCloseChecklist(
  id: string,
  data: Partial<PeriodCloseChecklist>,
): Promise<PeriodCloseChecklist> {
  const response = await apiClient.patch<PeriodCloseChecklist>(`pools/period-closes/${id}/`, data)
  return response.data
}

export async function certifyPeriodClose(id: string): Promise<PeriodCloseChecklist> {
  const response = await apiClient.post<PeriodCloseChecklist>(`pools/period-closes/${id}/certify/`)
  return response.data
}

export async function lockPeriodClose(id: string): Promise<PeriodCloseChecklist> {
  const response = await apiClient.post<PeriodCloseChecklist>(`pools/period-closes/${id}/lock/`)
  return response.data
}

export interface GateVerificationResponse {
  success: boolean
  period_close_id: string
  all_passed: boolean
  gates: Record<string, {
    passed: boolean
    label: string
    description: string
    details: string
    open_count?: number
    run_id?: string
  }>
}

export interface RoleSignOffResponse {
  success: boolean
  period_close_id: string
  role: string
  status: PeriodCloseStatus
  signoffs: Record<string, {
    signed: boolean
    user_name?: string
    user_email?: string
    signed_at?: string
    notes?: string
    fatwa_ref?: string
  }>
}

export interface LockCeremonyResponse {
  success: boolean
  period_close_id: string
  status: PeriodCloseStatus
  cryptographic_seal: string
  locked_at: string
  locked_by: string
  sbp_package: SbpFilingPackage
}

export interface SbpFilingPackage {
  certificate_id: string
  regulatory_standard: string
  pool_name: string
  pool_code: string
  period_range: string
  audit_timestamp: string
  cryptographic_seal: string
  sha256_hash?: string
  financial_summary: {
    gross_income_pkr: number
    direct_expenses_pkr?: number
    distributable_profit_pkr: number
    mudarib_fee_pkr: number
    net_depositor_profit_pkr: number
    total_weighted_funds_pkr?: number
    effective_mudarib_pct?: number
  }
  signatories?: {
    locked_by: string
    pool_manager: string
    shariah_reviewer: string
    cfo_checker: string
  }
  legal_statement?: string
  status?: string
  is_locked?: boolean
}

export async function autoVerifyPeriodGates(id: string): Promise<GateVerificationResponse> {
  const response = await apiClient.post<GateVerificationResponse>(`pools/period-closes/${id}/auto-verify-gates/`)
  return response.data
}

export async function signOffPeriodRole(
  id: string,
  role: "pool_manager" | "shariah_reviewer" | "cfo_checker",
  notes = "",
  fatwaRef = "",
): Promise<RoleSignOffResponse> {
  const response = await apiClient.post<RoleSignOffResponse>(`pools/period-closes/${id}/sign-off-role/`, {
    role,
    notes,
    fatwa_ref: fatwaRef,
  })
  return response.data
}

export async function executeLockCeremony(id: string, lockNote = ""): Promise<LockCeremonyResponse> {
  const response = await apiClient.post<LockCeremonyResponse>(`pools/period-closes/${id}/lock-ceremony/`, {
    lock_note: lockNote,
  })
  return response.data
}

export async function fetchSbpFilingPackage(id: string): Promise<SbpFilingPackage> {
  const response = await apiClient.get<SbpFilingPackage>(`pools/period-closes/${id}/filing-package/`)
  return response.data
}

