import { apiClient } from "./axios"
import type {
  ContractClauseSchemaField,
  ContractTemplate,
  CreateContractTemplateInput,
  CreateProductInput,
  Product,
} from "../types"

export async function fetchProducts(): Promise<Product[]> {
  const response = await apiClient.get<Product[]>("products/products/")
  return response.data
}

export async function createProduct(data: CreateProductInput): Promise<Product> {
  const response = await apiClient.post<Product>("products/products/", data)
  return response.data
}

export async function submitProductForReview(id: string): Promise<Product> {
  const response = await apiClient.post<Product>(`products/products/${id}/submit-for-review/`)
  return response.data
}

export async function approveProduct(id: string): Promise<Product> {
  const response = await apiClient.post<Product>(`products/products/${id}/approve/`)
  return response.data
}

export async function fetchContractTemplates(): Promise<ContractTemplate[]> {
  const response = await apiClient.get<ContractTemplate[]>("products/contract-templates/")
  return response.data
}

export async function createContractTemplate(
  data: CreateContractTemplateInput,
): Promise<ContractTemplate> {
  const response = await apiClient.post<ContractTemplate>("products/contract-templates/", data)
  return response.data
}

export async function approveContractTemplate(id: string): Promise<ContractTemplate> {
  const response = await apiClient.post<ContractTemplate>(
    `products/contract-templates/${id}/approve/`,
  )
  return response.data
}

export async function fetchClausesSchema(templateId: string): Promise<ContractClauseSchemaField[]> {
  const response = await apiClient.get<ContractClauseSchemaField[]>(
    `products/contract-templates/${templateId}/clauses-schema/`,
  )
  return response.data
}

export interface ContractAnalysisResult {
  contract_type: string
  name_suggestion: string
  depositor_psr: number | null
  mudarib_psr: number | null
  wakalah_fee_percentage: number | null
  profit_calculation_frequency: string
  loss_absorption_mechanism: string
  prohibited_terms_detected: string[]
  shariah_verdict: "COMPLIANT" | "CONTAINS_POTENTIAL_VIOLATIONS"
  confidence_score: number
  clauses: { clause_code: string; clause_title: string; content: string }[]
}

export async function analyzeContractWithAI(contract_text: string): Promise<ContractAnalysisResult> {
  const response = await apiClient.post<ContractAnalysisResult>(
    "ai/contract-analyzer/analyze/",
    { contract_text }
  )
  return response.data
}
