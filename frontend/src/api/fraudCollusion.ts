import { apiClient } from "./axios"

export interface GraphNode {
  id: string
  label: string
  ref: string
  pool: string
  payout_position: number | null
  is_paid_out: boolean
  risk_score: number
  risk_tier: "LOW" | "HIGH" | "CRITICAL"
  flags: string[]
  type: string
}

export interface GraphEdge {
  id: string
  source: string
  target: string
  type: "CIRCULAR_GUARANTEE" | "SHARED_ADDRESS_BRANCH"
  label: string
  severity: "HIGH" | "MEDIUM"
  color: string
}

export interface CollusionCluster {
  cluster_id: string
  cluster_type: string
  severity: "CRITICAL" | "HIGH" | "MEDIUM"
  title: string
  description: string
  members: string[]
  recommended_action: string
}

export interface FraudCollusionResponse {
  success: boolean
  overall_network_risk: number
  risk_tier: "LOW" | "MODERATE" | "HIGH" | "CRITICAL"
  cluster_count: number
  suspicious_member_count: number
  clusters: CollusionCluster[]
  graph: {
    nodes: GraphNode[]
    edges: GraphEdge[]
  }
  investigation_dossier: string
}

export async function fetchFraudCollusionAnalysis(poolId?: string): Promise<FraudCollusionResponse> {
  const response = await apiClient.get<FraudCollusionResponse>("ai/fraud-collusion/detect/", {
    params: poolId ? { pool_id: poolId } : undefined,
  })
  return response.data
}
