import { apiClient } from "./axios"
import type { CreatePoolInput, Pool, Product } from "../types"
import { fetchProducts } from "./products"

export async function fetchPools(): Promise<Pool[]> {
  const response = await apiClient.get<Pool[]>("pools/pools/")
  return response.data
}

export async function createPool(data: CreatePoolInput): Promise<Pool> {
  const response = await apiClient.post<Pool>("pools/pools/", data)
  return response.data
}

export async function fetchApprovedProducts(): Promise<Product[]> {
  // The backend's ProductViewSet.get_queryset() doesn't support a
  // ?status= filter, so we fetch everything and filter client-side.
  const products = await fetchProducts()
  return products.filter((product) => product.status === "approved")
}
