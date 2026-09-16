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

export interface CreatePoolInput {
  name: string
  code: string
  product: string
  effective_date: string
}

export interface PoolVersionSnapshot {
  product: {
    id: string
    name: string
    code: string
    operating_model: string
    status: string
  }
  contract_template: {
    id: string
    name: string
    contract_type: string
    version: string
    clauses: Record<string, unknown>
    status: string
  }
}

export interface PoolVersion {
  id: string
  pool: string
  version_number: number
  snapshot: PoolVersionSnapshot
  created_by: number | null
  is_current: boolean
  created_at: string
}

export interface WeightageBand {
  id: string
  tenant: string
  pool: string
  participant_class: string
  weightage: string
  effective_from: string
  effective_to: string | null
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateWeightageBandInput {
  pool: string
  participant_class: string
  weightage: string
  effective_from: string
  effective_to?: string | null
}

export interface PSR {
  id: string
  tenant: string
  pool: string
  depositor_share: string
  mudarib_share: string
  effective_from: string
  effective_to: string | null
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreatePSRInput {
  pool: string
  depositor_share: string
  mudarib_share: string
  effective_from: string
  effective_to?: string | null
}

export interface Asset {
  id: string
  tenant: string
  reference_code: string
  asset_type: string
  description: string
  face_value: string
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateAssetInput {
  reference_code: string
  asset_type: string
  description: string
  face_value: string
}

export interface AssetAssignment {
  id: string
  tenant: string
  asset: string
  pool: string
  assigned_date: string
  unassigned_date: string | null
  assigned_by: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AssignAssetInput {
  asset: string
  pool: string
  assigned_date: string
}

export interface DailyBalance {
  id: string
  tenant: string
  pool: string
  participant_class: string
  value_date: string
  balance_amount: string
  source: string
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface BalanceImportBatch {
  id: string
  tenant: string
  pool: string
  value_date: string
  total_records: number
  matched_records: number
  exception_count: number
  control_total_expected: string | null
  control_total_actual: string | null
  status: string
  imported_by: number | null
  created_at: string
  updated_at: string
}

export interface BalanceImportRecordInput {
  participant_class: string
  balance_amount: string
}

export interface BalanceImportInput {
  pool: string
  value_date: string
  control_total_expected?: string | null
  records: BalanceImportRecordInput[]
}

export interface BalanceImportResult {
  id: string
  total_records: number
  matched_records: number
  exception_count: number
  control_total_expected: string | null
  control_total_actual: string | null
  status: string
  errors: string[]
}
