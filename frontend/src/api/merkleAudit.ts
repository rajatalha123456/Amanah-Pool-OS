import { apiClient } from "./axios"

export interface MerkleFieldDiff {
  field: string
  before: string
  after: string
}

export interface MerkleChainBlock {
  height: number
  entry_id: string
  timestamp: string | null
  actor_email: string
  actor_role: string
  action: string
  model_name: string
  object_id: string
  reason: string
  ip_address: string
  leaf_hash: string
  rolling_merkle_root: string
  is_tampered: boolean
  tamper_detected_at_this_block?: boolean
  field_diffs: MerkleFieldDiff[]
}

export interface TamperedBlockInfo {
  height: number
  entry_id: string
  action: string
  model_name: string
  tamper_evidence: string
}

export interface MerkleVerificationResult {
  status: "VERIFIED" | "TAMPER_DETECTED"
  total_blocks: number
  tampered_count: number
  genesis_block_hash: string
  current_merkle_root?: string
  compromised_merkle_root?: string
  broken_at_block_height?: number | null
  verified_at: string
  chain_blocks: MerkleChainBlock[]
  tampered_blocks: TamperedBlockInfo[]
}

export async function fetchMerkleVerification(params: {
  model_name?: string
  date_from?: string
  date_to?: string
} = {}): Promise<MerkleVerificationResult> {
  const response = await apiClient.post<MerkleVerificationResult>("core/audit-log/verify-merkle/", params)
  return response.data
}

export async function simulateMerkleTamper(targetHeight?: number): Promise<MerkleVerificationResult> {
  const response = await apiClient.post<MerkleVerificationResult>("core/audit-log/simulate-tamper/", {
    target_height: targetHeight,
  })
  return response.data
}
