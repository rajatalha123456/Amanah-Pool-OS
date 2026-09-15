import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react"
import { ACCESS_TOKEN_KEY, REFRESH_TOKEN_KEY, TENANT_CODE_KEY } from "./axios"
import { fetchCurrentUser } from "./authApi"
import type { User } from "../types"

interface AuthContextValue {
  accessToken: string | null
  user: User | null
  isAuthenticated: boolean
  setTokens: (access: string, refresh: string) => void
  loadCurrentUser: () => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [accessToken, setAccessToken] = useState<string | null>(() =>
    localStorage.getItem(ACCESS_TOKEN_KEY),
  )
  const [user, setUser] = useState<User | null>(null)

  const setTokens = useCallback((access: string, refresh: string) => {
    localStorage.setItem(ACCESS_TOKEN_KEY, access)
    localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
    setAccessToken(access)
  }, [])

  const loadCurrentUser = useCallback(async () => {
    const currentUser = await fetchCurrentUser()
    setUser(currentUser)
    if (currentUser.tenant_code) {
      localStorage.setItem(TENANT_CODE_KEY, currentUser.tenant_code)
    }
    return currentUser
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(ACCESS_TOKEN_KEY)
    localStorage.removeItem(REFRESH_TOKEN_KEY)
    localStorage.removeItem(TENANT_CODE_KEY)
    setAccessToken(null)
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({
      accessToken,
      user,
      isAuthenticated: Boolean(accessToken),
      setTokens,
      loadCurrentUser,
      logout,
    }),
    [accessToken, user, setTokens, loadCurrentUser, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return context
}
