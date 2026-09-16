import { apiClient } from "./axios"
import type { Product } from "../types"

export async function fetchProducts(): Promise<Product[]> {
  const response = await apiClient.get<Product[]>("products/products/")
  return response.data
}
