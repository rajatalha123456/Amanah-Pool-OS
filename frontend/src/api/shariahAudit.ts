import { apiClient } from "./axios"
import type { ShariahAuditFinding, ShariahAuditPlan } from "../types"

export async function fetchShariahAuditPlans(): Promise<ShariahAuditPlan[]> {
  const response = await apiClient.get<ShariahAuditPlan[]>("governance/shariah-audit-plans/")
  return response.data
}

export async function fetchShariahAuditPlanDetail(id: string): Promise<ShariahAuditPlan> {
  const response = await apiClient.get<ShariahAuditPlan>(`governance/shariah-audit-plans/${id}/`)
  return response.data
}

export async function createShariahAuditPlan(
  data: Partial<ShariahAuditPlan>,
): Promise<ShariahAuditPlan> {
  const response = await apiClient.post<ShariahAuditPlan>("governance/shariah-audit-plans/", data)
  return response.data
}

export async function approveShariahAuditPlan(id: string): Promise<ShariahAuditPlan> {
  const response = await apiClient.post<ShariahAuditPlan>(`governance/shariah-audit-plans/${id}/approve/`)
  return response.data
}

export async function fetchShariahAuditFindings(planId?: string): Promise<ShariahAuditFinding[]> {
  const params: Record<string, string> = {}
  if (planId) params.audit_plan = planId
  const response = await apiClient.get<ShariahAuditFinding[]>("governance/shariah-audit-findings/", {
    params,
  })
  return response.data
}

export async function createShariahAuditFinding(
  data: Partial<ShariahAuditFinding>,
): Promise<ShariahAuditFinding> {
  const response = await apiClient.post<ShariahAuditFinding>("governance/shariah-audit-findings/", data)
  return response.data
}

export async function updateShariahAuditFinding(
  id: string,
  data: Partial<ShariahAuditFinding>,
): Promise<ShariahAuditFinding> {
  const response = await apiClient.patch<ShariahAuditFinding>(
    `governance/shariah-audit-findings/${id}/`,
    data,
  )
  return response.data
}
