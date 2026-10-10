import { apiClient } from "./axios"

export interface PayoutTransactionItem {
  id: string
  txn_ref: string
  beneficiary_name: string
  cnic_ntn: string
  iban: string
  bank_name: string
  bic: string
  participant_class: string
  gross_profit: number
  tax_status: "filer" | "non_filer"
  wht_rate_pct: number
  wht_amount: number
  zakat_exempt: boolean
  zakat_amount: number
  net_payout: number
  routing_channel: "raast" | "one_link" | "ibt"
  status: "PENDING" | "QUEUED" | "DISPATCHED" | "SETTLED" | "FAILED"
  iban_valid: boolean
  clearing_rrn?: string | null
  latency_ms?: number | null
  response_code?: string | null
  settled_at?: string | null
}

export interface GateResult {
  name: string
  passed: boolean
  details: string
  status: "PASS" | "FAIL" | "READY"
}

export interface PayoutBatchDetail {
  batch_id: string
  batch_code: string
  allocation_run_id: string
  pool_id: string
  pool_name: string
  pool_code: string
  period_month: string
  value_date: string
  status: "draft" | "validated" | "authorized" | "dispatched" | "settled" | "partially_settled"
  total_records: number
  total_gross_profit: number
  total_wht_deducted: number
  total_zakat_deducted: number
  total_net_disbursed: number
  batch_hash: string
  iso_msg_id: string
  maker_email?: string | null
  checker_email?: string | null
  authorized_at?: string | null
  dispatched_at?: string | null
  settled_at?: string | null
  settled_records?: number
  failed_records?: number
  journal_batch_id?: string | null
  contra_voucher_code?: string | null
  gates_verified: boolean
  gate_results: Record<string, GateResult>
  transactions: PayoutTransactionItem[]
}

export interface PayoutBatchSummary {
  allocation_run_id: string
  pool_code: string
  pool_name: string
  value_date: string
  period_month: string
  batch_code: string
  status: string
  total_records: number
  total_gross_profit: number
  total_net_disbursed: number
  gates_verified: boolean
  settled_at?: string | null
  contra_voucher_code?: string | null
}

export async function fetchPayoutBatches(): Promise<{ batches: PayoutBatchSummary[] }> {
  const response = await apiClient.get<{ batches: PayoutBatchSummary[] }>("allocation/payout-clearing/")
  return response.data
}

export async function fetchPayoutBatchDetail(
  allocationRunId: string,
  forceRegenerate = false
): Promise<PayoutBatchDetail> {
  const response = await apiClient.get<PayoutBatchDetail>("allocation/payout-clearing/batch-detail/", {
    params: {
      allocation_run: allocationRunId,
      force_regenerate: forceRegenerate ? "true" : undefined,
    },
  })
  return response.data
}

export async function verifyPayoutGates(allocationRunId: string): Promise<PayoutBatchDetail> {
  const response = await apiClient.post<PayoutBatchDetail>("allocation/payout-clearing/verify-gates/", {
    allocation_run: allocationRunId,
  })
  return response.data
}

export async function authorizePayoutBatch(allocationRunId: string): Promise<PayoutBatchDetail> {
  const response = await apiClient.post<PayoutBatchDetail>("allocation/payout-clearing/authorize/", {
    allocation_run: allocationRunId,
  })
  return response.data
}

export async function dispatchPayoutSimulation(
  allocationRunId: string,
  injectEdgeCase = false
): Promise<PayoutBatchDetail> {
  const response = await apiClient.post<PayoutBatchDetail>("allocation/payout-clearing/dispatch-simulate/", {
    allocation_run: allocationRunId,
    inject_edge_case: injectEdgeCase,
  })
  return response.data
}

export async function postPayoutContraGL(allocationRunId: string): Promise<PayoutBatchDetail> {
  const response = await apiClient.post<PayoutBatchDetail>("allocation/payout-clearing/post-contra-gl/", {
    allocation_run: allocationRunId,
  })
  return response.data
}

export async function downloadPacs008Xml(allocationRunId: string): Promise<string> {
  const response = await apiClient.get<string>("allocation/payout-clearing/download-iso-pacs008/", {
    params: { allocation_run: allocationRunId },
    responseType: "text" as any,
  })
  return response.data
}
