import { isAxiosError } from "axios"
import { apiClient } from "./axios"
import { extractErrorMessage } from "./errors"
import type {
  CapitalAccount,
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

