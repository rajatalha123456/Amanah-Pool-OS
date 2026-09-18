import { apiClient } from "./axios"
import type { CreateUserInput, UpdateUserInput, UserAdmin, UserCreateResponse } from "../types"

export async function fetchUsers(): Promise<UserAdmin[]> {
  const response = await apiClient.get<UserAdmin[]>("auth/users/")
  return response.data
}

export async function createUser(data: CreateUserInput): Promise<UserCreateResponse> {
  const response = await apiClient.post<UserCreateResponse>("auth/users/", data)
  return response.data
}

export async function updateUser(id: number, data: UpdateUserInput): Promise<UserAdmin> {
  const response = await apiClient.patch<UserAdmin>(`auth/users/${id}/`, data)
  return response.data
}
