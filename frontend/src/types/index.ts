export interface HealthCheckResponse {
  status: string
}

export interface NavItem {
  label: string
  path: string
}

export type BadgeVariant = "navy" | "emerald" | "gold" | "neutral"

export interface User {
  id: number
  email: string
  full_name: string
  role: string
  tenant: string | null
  tenant_code: string | null
  mfa_enabled: boolean
}

export interface LoginResponse {
  mfa_setup_required?: boolean
  mfa_required?: boolean
  pending_token: string
}

export interface MfaSetupResponse {
  secret: string
  qr_code_base64: string
}

export interface MfaVerifyResponse {
  access: string
  refresh: string
}
