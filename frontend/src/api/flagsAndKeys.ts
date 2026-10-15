import { apiClient } from "./axios"

export interface FeatureFlag {
  id: string
  tenant: string
  tenant_code: string
  key: string
  enabled: boolean
  note: string
}

export interface EncryptionKeyRecord {
  id: string
  tenant: string
  tenant_code: string
  purpose: string
  provider: string
  key_reference: string
  rotation_interval_days: number
  last_rotated_on: string | null
  rotation_due_on: string | null
  overdue: boolean
  retired: boolean
}

function rows<T>(data: T[] | { results: T[] }): T[] {
  return Array.isArray(data) ? data : data.results
}

export async function fetchFeatureFlags(): Promise<FeatureFlag[]> {
  return rows((await apiClient.get("tenants/feature-flags/")).data)
}
export async function setFeatureFlag(body: { tenant: string; key: string; enabled: boolean; note: string }): Promise<void> {
  await apiClient.post("tenants/feature-flags/", body)
}
export async function toggleFeatureFlag(id: string, enabled: boolean): Promise<void> {
  await apiClient.patch(`tenants/feature-flags/${id}/`, { enabled })
}
export async function fetchEncryptionKeys(): Promise<EncryptionKeyRecord[]> {
  return rows((await apiClient.get("tenants/encryption-keys/")).data)
}
export async function registerEncryptionKey(body: Pick<EncryptionKeyRecord, "tenant" | "purpose" | "provider" | "key_reference" | "rotation_interval_days">): Promise<void> {
  await apiClient.post("tenants/encryption-keys/", body)
}
export async function recordKeyRotation(id: string): Promise<void> {
  await apiClient.post(`tenants/encryption-keys/${id}/rotated/`, {})
}
