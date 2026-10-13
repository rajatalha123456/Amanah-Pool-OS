import { isAxiosError } from "axios"
import { apiClient } from "./axios"
import { extractErrorMessage } from "./errors"
import type {
  NegligenceCase,
  CapitalAccount,
  CapitalStatement,
  DistributionInput,
  DistributionRun,
  DistributionSimulation,
  CreateCapitalAccountInput,
  CreateNAVSnapshotInput,
  ImpairmentEvent,
  NAVSnapshot,
  Redemption,
  RedeemInput,
  Subscription,
  SubscribeInput,
} from "../types"

export async function fetchCapitalAccounts(poolId: string): Promise<CapitalAccount[]> {
  const response = await apiClient.get<CapitalAccount[]>("investments/capital-accounts/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function fetchCapitalAccount(id: string): Promise<CapitalAccount> {
  const response = await apiClient.get<CapitalAccount>(`investments/capital-accounts/${id}/`)
  return response.data
}

export async function fetchSubscriptionsForAccount(capitalAccountId: string): Promise<Subscription[]> {
  const response = await apiClient.get<Subscription[]>("investments/subscriptions/", {
    params: { capital_account: capitalAccountId },
  })
  return response.data
}

export async function fetchRedemptionsForAccount(capitalAccountId: string): Promise<Redemption[]> {
  const response = await apiClient.get<Redemption[]>("investments/redemptions/", {
    params: { capital_account: capitalAccountId },
  })
  return response.data
}

export async function createCapitalAccount(data: CreateCapitalAccountInput): Promise<CapitalAccount> {
  const response = await apiClient.post<CapitalAccount>("investments/capital-accounts/", data)
  return response.data
}

export async function subscribe(accountId: string, data: SubscribeInput): Promise<Subscription> {
  const response = await apiClient.post<Subscription>(
    `investments/capital-accounts/${accountId}/subscribe/`,
    data,
  )
  return response.data
}

export async function redeem(accountId: string, data: RedeemInput): Promise<Redemption> {
  const response = await apiClient.post<Redemption>(
    `investments/capital-accounts/${accountId}/redeem/`,
    data,
  )
  return response.data
}

export async function fetchNAVSnapshots(poolId: string): Promise<NAVSnapshot[]> {
  const response = await apiClient.get<NAVSnapshot[]>("investments/nav-snapshots/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function createNAVSnapshot(data: CreateNAVSnapshotInput): Promise<NAVSnapshot> {
  const response = await apiClient.post<NAVSnapshot>("investments/nav-snapshots/", data)
  return response.data
}

export async function publishNAVSnapshot(id: string): Promise<NAVSnapshot> {
  const response = await apiClient.post<NAVSnapshot>(`investments/nav-snapshots/${id}/publish/`)
  return response.data
}

export async function fetchImpairmentEvents(poolId: string): Promise<ImpairmentEvent[]> {
  const response = await apiClient.get<ImpairmentEvent[]>("investments/impairment-events/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function fetchAllSubscriptions(capitalAccountId?: string): Promise<Subscription[]> {
  const response = await apiClient.get<Subscription[]>("investments/subscriptions/", {
    params: capitalAccountId ? { capital_account: capitalAccountId } : undefined,
  })
  return response.data
}

export async function fetchAllRedemptions(capitalAccountId?: string): Promise<Redemption[]> {
  const response = await apiClient.get<Redemption[]>("investments/redemptions/", {
    params: capitalAccountId ? { capital_account: capitalAccountId } : undefined,
  })
  return response.data
}

export async function createImpairmentEvent(data: {
  pool: string
  valuation_date: string
  loss_amount: string
  reason: string
}): Promise<ImpairmentEvent> {
  const response = await apiClient.post<ImpairmentEvent>("investments/impairment-events/", data)
  return response.data
}

export async function approveImpairmentEvent(id: string): Promise<ImpairmentEvent> {
  const response = await apiClient.post<ImpairmentEvent>(`investments/impairment-events/${id}/approve/`)
  return response.data
}

export async function fetchLatestNAV(poolId: string): Promise<NAVSnapshot | null> {
  try {
    const response = await apiClient.get<NAVSnapshot>("investments/nav-snapshots/latest/", {
      params: { pool: poolId },
    })
    return response.data
  } catch (error) {
    const message = extractErrorMessage(error, "")
    if (isAxiosError(error) && error.response?.status === 400 && message.includes("No published NAV")) {
      return null
    }
    throw error
  }
}


export async function fetchDistributionRuns(poolId: string): Promise<DistributionRun[]> {
  const response = await apiClient.get<DistributionRun[]>("investments/distribution-runs/", { params: { pool: poolId } })
  return response.data
}

export async function simulateDistribution(input: DistributionInput): Promise<DistributionSimulation> {
  const response = await apiClient.post<DistributionSimulation>("investments/distribution-runs/simulate/", input)
  return response.data
}

export async function createDistributionRun(input: DistributionInput): Promise<DistributionRun> {
  const response = await apiClient.post<DistributionRun>("investments/distribution-runs/", input)
  return response.data
}

export async function submitDistributionRun(id: string): Promise<DistributionRun> {
  const response = await apiClient.post<DistributionRun>(`investments/distribution-runs/${id}/submit-for-checking/`)
  return response.data
}

export async function checkDistributionRun(id: string): Promise<DistributionRun> {
  const response = await apiClient.post<DistributionRun>(`investments/distribution-runs/${id}/check/`)
  return response.data
}

export async function shariahSignOffDistributionRun(id: string, note: string): Promise<DistributionRun> {
  const response = await apiClient.post<DistributionRun>(`investments/distribution-runs/${id}/shariah-sign-off/`, { note })
  return response.data
}

/** Final release by the authorized signatory (after the independent check and the Shariah review). */
export async function approveDistributionRun(id: string): Promise<DistributionRun> {
  const response = await apiClient.post<DistributionRun>(`investments/distribution-runs/${id}/approve/`)
  return response.data
}

export async function rejectDistributionRun(id: string, reason: string): Promise<DistributionRun> {
  const response = await apiClient.post<DistributionRun>(`investments/distribution-runs/${id}/reject/`, {
    rejection_reason: reason,
  })
  return response.data
}

export async function restateDistributionRun(id: string, reason: string): Promise<DistributionRun> {
  const response = await apiClient.post<DistributionRun>(`investments/distribution-runs/${id}/restate/`, {
    restatement_reason: reason,
  })
  return response.data
}

export async function fetchCapitalStatement(accountId: string, from: string, to: string): Promise<CapitalStatement> {
  const response = await apiClient.get<CapitalStatement>(`investments/capital-accounts/${accountId}/statement/`, {
    params: { from, to },
  })
  return response.data
}

export async function fetchNegligenceCases(poolId: string): Promise<NegligenceCase[]> {
  return (await apiClient.get<NegligenceCase[]>("investments/negligence-cases/", { params: { pool: poolId } })).data
}

export async function raiseNegligenceCase(input: {
  pool: string
  title: string
  allegation: string
  period_start: string
  period_end: string
}): Promise<NegligenceCase> {
  return (await apiClient.post<NegligenceCase>("investments/negligence-cases/", input)).data
}

export async function addNegligenceNote(id: string, note: string): Promise<NegligenceCase> {
  return (await apiClient.post<NegligenceCase>(`investments/negligence-cases/${id}/add-note/`, { note })).data
}

export async function determineNegligenceCase(
  id: string,
  input: { outcome: "liable" | "cleared"; determination_note: string; liability_amount?: string },
): Promise<NegligenceCase> {
  return (await apiClient.post<NegligenceCase>(`investments/negligence-cases/${id}/determine/`, input)).data
}

export async function approveRedemption(id: string): Promise<Redemption> {
  return (await apiClient.post<Redemption>(`investments/redemptions/${id}/approve/`)).data
}

export async function rejectRedemption(id: string, reason: string): Promise<Redemption> {
  return (await apiClient.post<Redemption>(`investments/redemptions/${id}/reject/`, { reason })).data
}
