import { apiClient } from "./axios"
import type { CreatePoolInput, Pool, PoolVersion, Product } from "../types"
import { fetchProducts } from "./products"

export async function fetchPools(): Promise<Pool[]> {
  const response = await apiClient.get<Pool[]>("pools/pools/")
  return response.data
}

export async function fetchPoolDetail(id: string): Promise<Pool> {
  const response = await apiClient.get<Pool>(`pools/pools/${id}/`)
  return response.data
}

export async function fetchPoolVersions(id: string): Promise<PoolVersion[]> {
  const response = await apiClient.get<PoolVersion[]>(`pools/pools/${id}/versions/`)
  return response.data
}

export async function createPool(data: CreatePoolInput): Promise<Pool> {
  const response = await apiClient.post<Pool>("pools/pools/", data)
  return response.data
}

export async function submitPoolForApproval(id: string): Promise<Pool> {
  const response = await apiClient.post<Pool>(`pools/pools/${id}/submit-for-approval/`)
  return response.data
}

export async function approvePool(id: string): Promise<Pool> {
  const response = await apiClient.post<Pool>(`pools/pools/${id}/approve/`)
  return response.data
}

export async function openPool(id: string): Promise<Pool> {
  const response = await apiClient.post<Pool>(`pools/pools/${id}/open/`)
  return response.data
}

export async function closePool(id: string): Promise<Pool> {
  const response = await apiClient.post<Pool>(`pools/pools/${id}/close/`)
  return response.data
}

export async function fetchApprovedProducts(): Promise<Product[]> {
  // The backend's ProductViewSet.get_queryset() doesn't support a
  // ?status= filter, so we fetch everything and filter client-side.
  const products = await fetchProducts()
  return products.filter((product) => product.status === "approved")
}
