import { apiClient } from "./axios"
import type { CreateTenantInput, LegalEntityRecord, TenantRecord } from "../types"

export async function fetchTenants(): Promise<TenantRecord[]> {
  const response = await apiClient.get<TenantRecord[]>("tenants/")
  return response.data
}

export async function fetchTenantDetail(id: string): Promise<TenantRecord> {
  const response = await apiClient.get<TenantRecord>(`tenants/${id}/`)
  return response.data
}

export async function createTenant(data: CreateTenantInput): Promise<TenantRecord> {
  const response = await apiClient.post<TenantRecord>("tenants/", data)
  return response.data
}

export async function suspendTenant(id: string): Promise<TenantRecord> {
  const response = await apiClient.post<TenantRecord>(`tenants/${id}/suspend/`)
  return response.data
}

export async function reactivateTenant(id: string): Promise<TenantRecord> {
  const response = await apiClient.post<TenantRecord>(`tenants/${id}/reactivate/`)
  return response.data
}

export async function fetchLegalEntities(): Promise<LegalEntityRecord[]> {
  const response = await apiClient.get<LegalEntityRecord[]>("legal-entities/")
  return response.data
}

export async function createLegalEntity(data: {
  tenant?: string
  name: string
  registration_number?: string
  jurisdiction: string
  base_currency?: string
  timezone?: string
}): Promise<LegalEntityRecord> {
  const response = await apiClient.post<LegalEntityRecord>("legal-entities/", data)
  return response.data
}
