import axios from "axios"

export const ACCESS_TOKEN_KEY = "amanah_access_token"
export const REFRESH_TOKEN_KEY = "amanah_refresh_token"
export const TENANT_CODE_KEY = "amanah_tenant_code"

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
})

apiClient.interceptors.request.use((config) => {
  const accessToken = localStorage.getItem(ACCESS_TOKEN_KEY)
  if (accessToken) {
    config.headers.Authorization = `Bearer ${accessToken}`
  }

  const tenantCode = localStorage.getItem(TENANT_CODE_KEY)
  if (tenantCode) {
    config.headers["X-Tenant-Code"] = tenantCode
  }

  return config
})
