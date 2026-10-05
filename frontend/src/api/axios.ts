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

let isRefreshing = false
let failedQueue: Array<{
  resolve: (token: string) => void
  reject: (error: unknown) => void
}> = []

const processQueue = (error: unknown, token: string | null = null) => {
  failedQueue.forEach((promise) => {
    if (error) {
      promise.reject(error)
    } else if (token) {
      promise.resolve(token)
    }
  })
  failedQueue = []
}

function handleSessionExpired() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
  localStorage.removeItem(TENANT_CODE_KEY)
  window.dispatchEvent(new Event("amanah_auth_expired"))
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      const url = String(originalRequest.url || "")
      // Skip token refresh attempts for auth endpoints
      if (url.includes("auth/login") || url.includes("auth/refresh") || url.includes("auth/mfa")) {
        handleSessionExpired()
        return Promise.reject(error)
      }

      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          failedQueue.push({ resolve, reject })
        })
          .then((newToken) => {
            originalRequest.headers.Authorization = `Bearer ${newToken}`
            return apiClient(originalRequest)
          })
          .catch((err) => Promise.reject(err))
      }

      originalRequest._retry = true
      isRefreshing = true

      const refreshToken = localStorage.getItem(REFRESH_TOKEN_KEY)
      if (!refreshToken) {
        isRefreshing = false
        handleSessionExpired()
        return Promise.reject(error)
      }

      try {
        const baseURL = import.meta.env.VITE_API_BASE_URL || "/api/v1/"
        const response = await axios.post<{ access: string }>(`${baseURL}auth/refresh/`, {
          refresh: refreshToken,
        })
        const newAccessToken = response.data.access
        localStorage.setItem(ACCESS_TOKEN_KEY, newAccessToken)
        apiClient.defaults.headers.common.Authorization = `Bearer ${newAccessToken}`
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`

        processQueue(null, newAccessToken)
        return apiClient(originalRequest)
      } catch (refreshError) {
        processQueue(refreshError, null)
        handleSessionExpired()
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }

    return Promise.reject(error)
  },
)

