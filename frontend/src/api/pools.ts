import { apiClient } from "./axios"
import type {
  CreatePoolInput,
  CreatePoolVersionInput,
  Pool,
  PoolVersion,
  PoolVersionDiffResponse,
  Product,
} from "../types"
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

export async function fetchPoolVersionDiff(
  poolId: string,
  v1?: string | number,
  v2?: string | number,
): Promise<PoolVersionDiffResponse> {
  const params: Record<string, string> = {}
  if (v1 !== undefined) params.v1 = String(v1)
  if (v2 !== undefined) params.v2 = String(v2)
  const response = await apiClient.get<PoolVersionDiffResponse>(
    `pools/pools/${poolId}/compare-versions/`,
    { params },
  )
  return response.data
}

export async function createPoolVersion(
  poolId: string,
  data: CreatePoolVersionInput,
): Promise<PoolVersion> {
  const response = await apiClient.post<PoolVersion>(
    `pools/pools/${poolId}/create-version/`,
    data,
  )
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
