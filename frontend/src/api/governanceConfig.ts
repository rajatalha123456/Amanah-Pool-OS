import { apiClient } from "./axios"

export interface ApprovalRule {
  id: string
  action: string
  role: string
  max_amount: string | null
  is_active: boolean
}

export interface AccountMappingRow {
  id: string
  pool: string | null
  pool_code: string | null
  account_key: string
  gl_code: string
  gl_name: string
}

export interface AccountCatalogRow {
  key: string
  default_name: string
  required_for: string[]
}

export async function fetchApprovalRules(): Promise<ApprovalRule[]> {
  return (await apiClient.get<ApprovalRule[]>("accounting/approval-matrix/")).data
}

export async function fetchApprovalActions(): Promise<Array<{ key: string; label: string }>> {
  return (await apiClient.get<Array<{ key: string; label: string }>>("accounting/approval-matrix/actions/")).data
}

export interface ConfigChange {
  id: string
  kind: "approval_matrix" | "account_mapping"
  operation: "create" | "update"
  payload: Record<string, string | null>
  before: Record<string, string | null>
  reason: string
  status: "pending" | "approved" | "rejected"
  requested_by: string | number | null
  requested_by_name: string | null
  decided_by_name: string | null
  decision_note: string
  created_at: string
}

/** Configuration edits are proposals: they take effect only after an independent approver accepts them. */
export async function createApprovalRule(input: {
  action: string
  role: string
  max_amount: string | null
  change_reason: string
}): Promise<ConfigChange> {
  return (await apiClient.post<ConfigChange>("accounting/approval-matrix/", input)).data
}

export async function fetchConfigChanges(status?: string): Promise<ConfigChange[]> {
  return (await apiClient.get<ConfigChange[]>("governance/config-changes/", { params: status ? { status } : {} })).data
}

export async function approveConfigChange(id: string): Promise<ConfigChange> {
  return (await apiClient.post<ConfigChange>(`governance/config-changes/${id}/approve/`)).data
}

export async function rejectConfigChange(id: string, reason: string): Promise<ConfigChange> {
  return (await apiClient.post<ConfigChange>(`governance/config-changes/${id}/reject/`, { reason })).data
}

export async function updateApprovalRule(
  id: string,
  input: Partial<Pick<ApprovalRule, "max_amount" | "is_active">> & { change_reason: string },
): Promise<ConfigChange> {
  return (await apiClient.patch<ConfigChange>(`accounting/approval-matrix/${id}/`, input)).data
}

export async function fetchAccountMappings(): Promise<AccountMappingRow[]> {
  return (await apiClient.get<AccountMappingRow[]>("accounting/account-mappings/")).data
}

export async function fetchAccountCatalog(): Promise<AccountCatalogRow[]> {
  return (await apiClient.get<AccountCatalogRow[]>("accounting/account-mappings/catalog/")).data
}

export async function saveAccountMapping(
  input: { account_key: string; gl_code: string; gl_name: string; pool?: string | null; change_reason: string },
  existingId?: string,
): Promise<ConfigChange> {
  if (existingId) {
    return (await apiClient.patch<ConfigChange>(`accounting/account-mappings/${existingId}/`, input)).data
  }
  return (await apiClient.post<ConfigChange>("accounting/account-mappings/", input)).data
}
