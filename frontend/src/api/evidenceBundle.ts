import { apiClient } from "./axios"

export interface EvidenceArtifact {
  meta: {
    artifact_id: string
    name: string
    [key: string]: any
  }
  hash: string
  verified: boolean
}

export interface EvidenceBundlePayload {
  bundle_id: string
  pool_id: string
  pool_name: string
  pool_code: string
  period_month: string
  target_date: string
  audit_type: string
  regulatory_framework?: string
  compiled_at: string
  compiled_by_email: string
  master_bundle_seal: string
  artifacts_count: number
  artifacts_available: number
  artifacts_verified: number
  all_verified: boolean
  artifacts: EvidenceArtifact[]
  xml_pacs008_available: boolean
}

export async function compileEvidenceBundle(params: {
  pool_id?: string
  period_date?: string
  audit_type?: string
}): Promise<EvidenceBundlePayload> {
  const response = await apiClient.post<EvidenceBundlePayload>("core/evidence-bundle/compile/", params)
  return response.data
}

export async function downloadEvidenceBundleZip(params: {
  pool_id?: string
  period_date?: string
  audit_type?: string
}): Promise<void> {
  const response = await apiClient.get("core/evidence-bundle/download/", {
    params,
    responseType: "blob",
  })

  const blob = new Blob([response.data], { type: "application/zip" })
  const url = window.URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = `SBP_Evidence_Bundle_${params.period_date || "2026-09"}.zip`
  document.body.appendChild(a)
  a.click()
  window.URL.revokeObjectURL(url)
  document.body.removeChild(a)
}
