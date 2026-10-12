import { apiClient } from "./axios"

export interface DashboardMetric {
  label: string
  value: string | null
  detail: string
  link: string
  tone: "normal" | "attention"
}

export interface RoleDashboard {
  audience: string
  role: string
  sections: { title: string; metrics: DashboardMetric[] }[]
}

export async function fetchRoleDashboard(): Promise<RoleDashboard | null> {
  try {
    return (await apiClient.get<RoleDashboard>("dashboard/home/")).data
  } catch {
    return null // a role with no staff dashboard
  }
}
