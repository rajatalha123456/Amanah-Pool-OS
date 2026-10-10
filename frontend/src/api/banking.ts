import { apiClient } from "./axios"

export interface BankingSettlementPayload {
  amount: string | number
  source_title: string
  source_iban: string
  destination_title?: string
  destination_iban?: string
  channel?: "RAAST_P2M" | "RAAST_P2P" | "1LINK_IBFT" | "1LINK_BILL"
  purpose?: string
  simulate_failure_code?: string
}

export interface BankingSettlementResult {
  success: boolean
  response_code: string
  response_message: string
  e2e_id: string
  stan: string
  rrn: string
  auth_code: string
  channel: string
  channel_name: string
  amount: string
  amount_raw: string
  currency: string
  settled_at: string
  source: {
    account_title: string
    iban: string
    bank_name: string
    bank_code: string
  }
  beneficiary: {
    account_title: string
    iban: string
    bank_name: string
    bank_code: string
  }
  purpose: string
  settlement_type: string
  regulatory_stamp: string
}

export async function processBankingSettlement(
  payload: BankingSettlementPayload,
): Promise<BankingSettlementResult> {
  const response = await apiClient.post<BankingSettlementResult>("banking/settle/", payload)
  return response.data
}
