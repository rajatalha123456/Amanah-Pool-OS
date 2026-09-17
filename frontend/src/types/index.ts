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
  access: string
  refresh: string
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

export interface AllocationLine {
  id?: string
  participant_class: string
  daily_funds: string
  weightage: string
  weighted_funds: string
  allocated_amount: string
}

export interface AllocationRunInput {
  pool: string
  value_date: string
  gross_income: string
  direct_expenses?: string
}

export interface SimulateAllocationResult {
  distributable: string
  total_weighted_funds: string
  depositor_pool_share: string
  mudarib_share: string
  lines: AllocationLine[]
}

export interface JournalEntry {
  id: string
  account_name: string
  entry_type: string
  amount: string
}

export interface JournalBatch {
  id: string
  tenant: string
  allocation_run: string
  pool: string
  batch_date: string
  total_debit: string
  total_credit: string
  status: string
  posted_by: number | null
  entries: JournalEntry[]
  created_at: string
  updated_at: string
}

export interface DepositorStatement {
  id: string
  allocation_run: string
  participant_class: string
  period_start: string
  period_end: string
  opening_balance: string
  net_deposits: string
  profit_allocated: string
  closing_balance: string
  narrative: string
  generated_at: string
}

export interface AllocationRun {
  id: string
  tenant: string
  pool: string
  value_date: string
  gross_income: string
  direct_expenses: string
  distributable_amount: string
  total_weighted_funds: string
  depositor_pool_share: string
  mudarib_share: string
  status: string
  calculation_hash: string | null
  created_by: number | null
  checked_by: number | null
  checked_at: string | null
  rejection_reason: string | null
  lines: AllocationLine[]
  journal_batch: JournalBatch | null
  created_at: string
  updated_at: string
}

// --- Shariah Policy Copilot (proxied through apps.ai_agents to the separate FastAPI service) ---

export interface ShariahDocument {
  id: string
  document_name: string
  document_type: string
  version: string
  approval_status: string
  status_emoji: string
  approval_date: string | null
  product_category: string | null
  jurisdiction: string | null
  is_current_version: number
}

export interface ShariahDocumentUploadInput {
  file: File
  document_name: string
  document_type: string
  approval_status: string
  product_category?: string
  jurisdiction?: string
  approved_by?: string
}

export interface EvidencePackCitation {
  document_id: string
  document_name: string
  version: string
  section_label: string | null
  page_number: number | null
  approval_date: string | null
}

export interface EvidencePackExcerpt {
  document_id: string
  document_name: string
  excerpt: string
  citation: EvidencePackCitation
}

export interface EvidencePackComparisonRow {
  topic: string
  source_a: string
  source_a_citation: EvidencePackCitation
  source_b: string
  source_b_citation: EvidencePackCitation
  note: string | null
}

export interface EvidencePack {
  id: string
  question: string
  research_summary: string
  relevant_rulings: string[]
  relevant_standards: string[]
  key_evidence_excerpts: EvidencePackExcerpt[]
  comparison_table: EvidencePackComparisonRow[]
  open_issues: string[]
  citations: EvidencePackCitation[]
  conflict_flagged: boolean
  disclaimer: string
  review_status: string
  is_fallback: boolean
}

export interface ShariahReviewResult {
  id: string
  review_status: string
  reviewer_id: string
  reviewed_at: string
}

export interface ShariahQueryFilters {
  approved_only?: boolean
  current_version_only?: boolean
  product_category?: string
  document_type?: string
}
