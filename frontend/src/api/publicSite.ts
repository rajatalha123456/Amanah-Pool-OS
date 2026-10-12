import { apiClient } from "./axios"

export interface DemoRequestInput {
  name: string
  organisation: string
  email: string
  interest: "bank_pool" | "investment_pool" | "community_circle" | "other"
  message: string
  website: string // honeypot: left empty by people
}

export async function submitDemoRequest(data: DemoRequestInput): Promise<void> {
  await apiClient.post("public/demo-requests/", data)
}

export interface DemoRequestRow {
  id: string
  name: string
  organisation: string
  email: string
  interest: string
  message: string
  handled: boolean
  created_at: string
}

export async function fetchDemoRequests(): Promise<DemoRequestRow[]> {
  return (await apiClient.get<DemoRequestRow[]>("demo-requests/")).data
}

export async function markDemoRequestHandled(id: string): Promise<void> {
  await apiClient.post(`demo-requests/${id}/mark-handled/`)
}
