import type { ReactNode } from "react"
import { useAuth } from "../api/auth"

/** True when the signed-in user's role is one of `roles` (the API enforces the same rules). */
export function useHasRole(...roles: string[]) {
  const { user } = useAuth()
  return !!user && roles.includes(user.role)
}

/** Shows its children only to the listed roles; others see `fallback` (nothing by default). */
export function RoleGate({ roles, children, fallback = null }: { roles: string[]; children: ReactNode; fallback?: ReactNode }) {
  const { user } = useAuth()
  return <>{user && roles.includes(user.role) ? children : fallback}</>
}
