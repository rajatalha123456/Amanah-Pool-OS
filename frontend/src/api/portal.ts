import { apiClient } from "./axios"

export type RequestType =
  | "dispute"
  | "hardship_request"
  | "statement_correction"
  | "payout_inquiry"
  | "general_complaint"
  | "other"

export const REQUEST_TYPE_LABEL: Record<RequestType, string> = {
  dispute: "Dispute a figure or decision",
  hardship_request: "Ask for hardship support",
  statement_correction: "Statement correction",
  payout_inquiry: "Payout enquiry",
  general_complaint: "Complaint",
  other: "Something else",
}

export interface MyRequest {
  id: string
  pool: string | null
  request_type: RequestType
  subject: string
  description: string
  status: string
  resolution_notes: string | null
  created_at: string
}

export async function fetchMyRequests(): Promise<MyRequest[]> {
  return (await apiClient.get<MyRequest[]>("governance/support-requests/")).data
}

export async function raiseRequest(data: { request_type: RequestType; subject: string; description: string; pool?: string }): Promise<void> {
  await apiClient.post("governance/support-requests/", { ...data, pool: data.pool || null })
}

export interface MyTaxSupport {
  participant: string
  tax_status: string
  zakat_exempt: boolean
  rows: {
    period_end: string
    pool: string
    batch_status: string
    gross_profit: string
    tax_status: string
    wht_rate_pct: number
    wht_amount: string
    zakat_amount: string
    net_payout: string
  }[]
  totals: { gross_profit: string; wht_amount: string; zakat_amount: string }
  note: string
}

export async function fetchMyTaxSupport(): Promise<MyTaxSupport | null> {
  try {
    return (await apiClient.get<MyTaxSupport>("participants/my-tax-support/")).data
  } catch {
    return null // a login with no participant record (a circle member) has no tax statement
  }
}
