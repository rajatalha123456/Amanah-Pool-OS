import { apiClient } from "./axios"
import type {
  LoginResponse,
  MfaSetupResponse,
  MfaVerifyResponse,
  User,
} from "../types"

export async function login(email: string, password: string): Promise<LoginResponse> {
  const response = await apiClient.post<LoginResponse>("auth/login/", {
    email,
    password,
  })
  return response.data
}

export async function setupMfa(pendingToken: string): Promise<MfaSetupResponse> {
  const response = await apiClient.post<MfaSetupResponse>("auth/mfa/setup/", {
    pending_token: pendingToken,
  })
  return response.data
}

export async function verifyMfa(
  pendingToken: string,
  code: string,
): Promise<MfaVerifyResponse> {
  const response = await apiClient.post<MfaVerifyResponse>("auth/mfa/verify/", {
    pending_token: pendingToken,
    code,
  })
  return response.data
}

export async function fetchCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>("auth/me/")
  return response.data
}
