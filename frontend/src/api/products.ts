import { apiClient } from "./axios"
import type { ContractTemplate, CreateProductInput, Product } from "../types"

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

export async function fetchContractTemplates(): Promise<ContractTemplate[]> {
  const response = await apiClient.get<ContractTemplate[]>("products/contract-templates/")
  return response.data
}
