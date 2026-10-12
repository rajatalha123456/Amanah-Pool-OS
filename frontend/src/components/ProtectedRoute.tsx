import type { ReactNode } from "react"
import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "../api/auth"

interface ProtectedRouteProps {
  children: ReactNode
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    // A visitor who opens the bare address meets the website first; anything deeper goes straight to sign-in.
    return <Navigate to={location.pathname === "/" ? "/welcome" : "/login"} replace />
  }

  return <>{children}</>
}
