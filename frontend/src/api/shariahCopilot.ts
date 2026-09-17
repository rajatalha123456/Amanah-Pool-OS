import { apiClient } from "./axios"
import type {
  EvidencePack,
  ShariahDocument,
  ShariahDocumentUploadInput,
  ShariahQueryFilters,
  ShariahReviewResult,
} from "../types"

export async function uploadDocument(input: ShariahDocumentUploadInput): Promise<ShariahDocument> {
  const formData = new FormData()
  formData.append("file", input.file)
  formData.append("document_name", input.document_name)
  formData.append("document_type", input.document_type)
  formData.append("approval_status", input.approval_status)
  if (input.product_category) formData.append("product_category", input.product_category)
  if (input.jurisdiction) formData.append("jurisdiction", input.jurisdiction)
  if (input.approved_by) formData.append("approved_by", input.approved_by)

  const response = await apiClient.post<ShariahDocument>("ai/shariah-copilot/documents/upload/", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  })
  return response.data
}

export async function fetchDocuments(currentOnly = true): Promise<ShariahDocument[]> {
  const response = await apiClient.get<ShariahDocument[]>("ai/shariah-copilot/documents/", {
    params: { current_only: currentOnly },
  })
  return response.data
}

export async function askQuestion(question: string, filters: ShariahQueryFilters = {}): Promise<EvidencePack> {
  const response = await apiClient.post<EvidencePack>("ai/shariah-copilot/ask/", { question, filters })
  return response.data
}

export async function submitReview(evidencePackId: string, approve: boolean): Promise<ShariahReviewResult> {
  const response = await apiClient.post<ShariahReviewResult>(`ai/shariah-copilot/review/${evidencePackId}/`, {
    approve,
  })
  return response.data
}
