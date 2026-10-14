import { apiClient } from "./axios"
import { pageParams, type Page } from "./pagination"

export type SuspenseSide = "unidentified_receipt" | "unexplained_shortfall"
export type SuspenseStatus = "proposed" | "open" | "clearing_proposed" | "cleared" | "rejected"

export interface SuspenseItem {
  id: string
  pool: string
  pool_code: string
  side: SuspenseSide
  amount: string
  counter_account_key: string
  description: string
  reference: string
  opened_on: string
  status: SuspenseStatus
  proposed_by: number | string | null
  proposed_by_name: string | null
  opened_by_name: string | null
  clear_account_key: string
  clear_reason: string
  clear_proposed_by: number | string | null
  cleared_by_name: string | null
  cleared_on: string | null
  decision_note: string
  created_at: string
}

export interface SuspenseAgeing {
  as_of: string
  max_age_days: number
  open_items: number
  overdue_items: number
  buckets: Record<string, string>
  items_net: string
  ledger_balance: string
  itemized: boolean
  items: { id: string; age_days: number; bucket: string; overdue: boolean }[]
}

export interface PoolAccount {
  key: string
  name: string
}

const BASE = "accounting/suspense-items/"

export async function fetchSuspenseItems(poolId: string, page = 1): Promise<Page<SuspenseItem>> {
  return (await apiClient.get<Page<SuspenseItem>>(BASE, { params: { pool: poolId, ...pageParams(page) } })).data
}

export async function fetchSuspenseAgeing(poolId: string): Promise<SuspenseAgeing> {
  return (await apiClient.get<SuspenseAgeing>(`${BASE}ageing/`, { params: { pool: poolId } })).data
}

export async function fetchClearableAccounts(): Promise<PoolAccount[]> {
  return (await apiClient.get<PoolAccount[]>(`${BASE}accounts/`)).data
}

export async function proposeSuspenseItem(input: {
  pool: string
  side: SuspenseSide
  amount: string
  description: string
  reference?: string
  counter_account_key?: string
  opened_on?: string
}): Promise<SuspenseItem> {
  return (await apiClient.post<SuspenseItem>(BASE, input)).data
}

export async function decideSuspense(
  id: string,
  verb: "approve" | "reject" | "approve-clear" | "reject-clear",
  reason?: string,
): Promise<SuspenseItem> {
  return (await apiClient.post<SuspenseItem>(`${BASE}${id}/${verb}/`, reason ? { reason } : {})).data
}

export async function proposeSuspenseClearing(id: string, targetAccountKey: string, reason: string): Promise<SuspenseItem> {
  return (await apiClient.post<SuspenseItem>(`${BASE}${id}/propose-clear/`, { target_account_key: targetAccountKey, reason })).data
}
