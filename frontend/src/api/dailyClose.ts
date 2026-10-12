import { apiClient } from "./axios"

export interface DailyCloseGate {
  key: string
  label: string
  passed: boolean
  detail: string
}

export interface DailyCloseRecord {
  id: string
  pool: string
  pool_code: string
  value_date: string
  status: "open" | "prepared" | "signed"
  gates: DailyCloseGate[]
  notes: string
  prepared_by_name: string | null
  prepared_at: string | null
  signed_by_name: string | null
  signed_at: string | null
}

export async function fetchDailyCloses(poolId: string): Promise<DailyCloseRecord[]> {
  return (await apiClient.get<DailyCloseRecord[]>("pools/daily-closes/", { params: { pool: poolId } })).data
}

export async function prepareDailyClose(poolId: string, valueDate: string, notes: string): Promise<DailyCloseRecord> {
  return (await apiClient.post<DailyCloseRecord>("pools/daily-closes/prepare/", { pool: poolId, value_date: valueDate, notes })).data
}

export async function signDailyClose(id: string): Promise<DailyCloseRecord> {
  return (await apiClient.post<DailyCloseRecord>(`pools/daily-closes/${id}/sign/`)).data
}
