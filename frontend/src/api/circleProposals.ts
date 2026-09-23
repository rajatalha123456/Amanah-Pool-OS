import { apiClient } from "./axios"
import type {
  CircleProposal,
  CloseProposalResponse,
  CircleVote,
  CreateCircleProposalInput,
  RecordVoteInput,
} from "../types"

export async function fetchCircleProposals(poolId: string): Promise<CircleProposal[]> {
  const response = await apiClient.get<CircleProposal[]>("circles/circle-proposals/", {
    params: { pool: poolId },
  })
  return response.data
}

export async function fetchCircleProposal(proposalId: string): Promise<CircleProposal> {
  const response = await apiClient.get<CircleProposal>(`circles/circle-proposals/${proposalId}/`)
  return response.data
}

export async function createCircleProposal(data: CreateCircleProposalInput): Promise<CircleProposal> {
  const response = await apiClient.post<CircleProposal>("circles/circle-proposals/", data)
  return response.data
}

export async function recordVote(proposalId: string, data: RecordVoteInput): Promise<CircleVote> {
  const response = await apiClient.post<CircleVote>(`circles/circle-proposals/${proposalId}/vote/`, data)
  return response.data
}

export async function closeCircleProposal(proposalId: string): Promise<CloseProposalResponse> {
  const response = await apiClient.post<CloseProposalResponse>(
    `circles/circle-proposals/${proposalId}/close/`,
  )
  return response.data
}
