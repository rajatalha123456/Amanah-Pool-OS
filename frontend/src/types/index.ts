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

export interface ContractTemplateBasic {
  id: string
  name: string
  contract_type: string
  version: string
  status: string
}

export interface Product {
  id: string
  tenant: string
  name: string
  code: string
  operating_model: string
  contract_template: string
  contract_template_detail: ContractTemplateBasic
  status: string
  base_currency: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface ProductBasic {
  id: string
  name: string
  code: string
  status: string
  contract_template: ContractTemplateBasic
}

export interface ContractTemplate {
  id: string
  tenant: string
  name: string
  contract_type: string
  version: string
  clauses: Record<string, unknown>
  shariah_decision: string | null
  shariah_decision_code: string | null
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateProductInput {
  name: string
  code: string
  operating_model: string
  contract_template: string
}

export interface Pool {
  id: string
  tenant: string
  name: string
  code: string
  product: string
  product_detail: ProductBasic
  status: string
  effective_date: string
  closed_date: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}
