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

export interface AIModelRegistry {
  id: number
  model_name: string
  version: string
  status: "active" | "disabled"
  disabled_reason: string | null
  disabled_by: number | null
  disabled_at: string | null
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
  operating_model: string
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

export interface CreateContractTemplateInput {
  name: string
  contract_type: string
  version: string
  clauses: Record<string, string>
  shariah_decision?: string | null
}

export interface ContractClauseSchemaField {
  key: string
  label: string
  description: string
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

export interface RelatedPartyTransaction {
  id: string
  tenant: string
  pool: string
  related_party_name: string
  relationship_type: string
  transaction_type: string
  amount: string
  transaction_date: string
  disclosure_status: string
  reviewed_by: number | null
  review_notes: string | null
  created_at: string
  updated_at: string
}

export interface CreateRelatedPartyTransactionInput {
  pool: string
  related_party_name: string
  relationship_type: string
  transaction_type: string
  amount: string
  transaction_date: string
}

export interface RelatedPartyReviewInput {
  decision: "approved" | "flagged"
  notes?: string
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
  shariah_review_required: boolean
  shariah_signed_off_by: number | null
  shariah_signed_off_at: string | null
  shariah_review_note: string | null
  lines: AllocationLine[]
  journal_batch: JournalBatch | null
  created_at: string
  updated_at: string
}

export interface CapitalAccount {
  id: string
  pool: string
  investor_name: string
  investor_reference: string
  units_held: string
  status: string
  created_at: string
  updated_at: string
}

export interface InvestorProfile {
  id: string
  capital_account: string
  kyc_status: "pending" | "verified" | "rejected"
  id_document_type: string
  id_document_number: string
  date_of_birth: string
  address: string
  risk_tolerance: "conservative" | "moderate" | "aggressive"
  suitability_assessment_notes: string | null
  verified_by: number | null
  verified_at: string | null
  created_at: string
  updated_at: string
}

export interface InvestorProfileInput {
  capital_account: string
  id_document_type: string
  id_document_number: string
  date_of_birth: string
  address: string
  risk_tolerance: InvestorProfile["risk_tolerance"]
  suitability_assessment_notes?: string
}

export interface VerifyKYCInput {
  kyc_status: "verified" | "rejected"
  notes?: string
}

export interface CreateCapitalAccountInput {
  pool: string
  investor_name: string
  investor_reference: string
}

export interface Subscription {
  id: string
  capital_account: string
  amount: string
  nav_per_unit: string
  units_allotted: string
  transaction_date: string
  status: string
  created_at: string
  updated_at: string
}

export interface Redemption {
  id: string
  capital_account: string
  units_redeemed: string
  nav_per_unit: string
  amount: string
  transaction_date: string
  status: string
  created_at: string
  updated_at: string
}

export interface NAVSnapshot {
  id: string
  pool: string
  valuation_date: string
  total_pool_value: string
  total_units_outstanding: string
  nav_per_unit: string
  status: string
  created_by: number | null
  published_by: number | null
  published_at: string | null
  created_at: string
  updated_at: string
}

export interface CreateNAVSnapshotInput {
  pool: string
  valuation_date: string
  total_pool_value: string
}

export interface SubscribeInput {
  amount: string
  transaction_date: string
}

export interface RedeemInput {
  units_redeemed: string
  transaction_date: string
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

// --- Governance: Exception Queue + Purification Ledger (apps.governance) ---

export interface ExceptionCase {
  id: string
  source_module: string
  source_object_id: string | null
  pool: string | null
  severity: string
  title: string
  description: string
  status: string
  detected_by: string
  assigned_to: number | null
  investigation_notes: string | null
  treatment_plan: string | null
  resolution_notes: string | null
  resolved_by: number | null
  resolved_at: string | null
  created_at: string
  updated_at: string
}

export interface UpdateExceptionAssigneeInput {
  assigned_to: number
}

export interface PurificationEntry {
  id: string
  pool: string
  source_description: string
  amount: string
  identified_date: string
  status: string
  shariah_decision: string | null
  charity_recipient: string | null
  distributed_date: string | null
  approved_by: number | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface CreatePurificationEntryInput {
  pool: string
  source_description: string
  amount: string
  identified_date: string
}

// --- Shariah Governance: Dashboard + Fatwa Register (apps.governance / apps.products) ---

export interface ShariahDecision {
  id: string
  tenant: string
  decision_code: string
  title: string
  description: string
  status: string
  effective_date: string
  approved_by: number | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateShariahDecisionInput {
  decision_code: string
  title: string
  description: string
  effective_date: string
}

export interface ShariahDashboardItem {
  id: string
  [key: string]: unknown
}

export interface ShariahDashboard {
  pending_shariah_decisions: ShariahDashboardItem[]
  pending_contract_templates: ShariahDashboardItem[]
  pending_weightage_bands: ShariahDashboardItem[]
  pending_psr_schedules: ShariahDashboardItem[]
  open_exception_cases: ShariahDashboardItem[]
  pending_purification_entries: ShariahDashboardItem[]
  pending_pool_approvals: ShariahDashboardItem[]
  summary_counts: {
    total_pending_items: number
    critical_exceptions: number
  }
}

export const USER_ROLES = [
  "platform_super_admin",
  "product_manager",
  "pool_manager",
  "finance_maker",
  "finance_checker",
  "shariah_secretariat",
  "shariah_board",
  "risk_compliance",
  "auditor",
  "investor_member",
] as const

export interface UserAdmin {
  id: number
  email: string
  full_name: string
  role: string
  tenant_code: string | null
  mfa_enabled: boolean
  is_active: boolean
}

export interface CreateUserInput {
  email: string
  full_name: string
  role: string
  tenant: string
}

export interface UserCreateResponse extends UserAdmin {
  generated_password: string
}

export interface UpdateUserInput {
  full_name?: string
  role?: string
  tenant?: string
  is_active?: boolean
}
