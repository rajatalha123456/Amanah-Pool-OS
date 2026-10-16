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
  preferred_language: string
}

export interface AIModelRegistry {
  id: number
  model_name: string
  version: string
  status: "active" | "disabled"
  disabled_reason: string | null
  disabled_by: number | null
  disabled_at: string | null
  owner: string
  purpose: string
  provenance: string
  validation_status: "not_validated" | "validated" | "expired"
  validated_on: string | null
  validation_reference: string
  retirement_date: string | null
}

export interface LoginResponse {
  access?: string
  refresh?: string
  mfa_required?: boolean
  mfa_setup_required?: boolean
  pending_token?: string
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
  eligible_asset_types?: string[]
  redemption_notice_days?: number
  redemption_gate_pct?: string
  minimum_subscription?: string | null
  subscription_cap?: string | null
  minimum_tenure_days?: number
  required_kyc_tier?: string
  max_participants?: number | null
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
  mandatory?: boolean
}

export interface CreateProductInput {
  name: string
  code: string
  operating_model: string
  contract_template: string
  eligible_asset_types?: string[]
  minimum_subscription?: string | null
  subscription_cap?: string | null
  minimum_tenure_days?: number
  required_kyc_tier?: string
  max_participants?: number | null
  redemption_notice_days?: number
}

export interface ActivationCheck {
  key: string
  label: string
  passed: boolean
  detail: string
}

export interface ActivationReadiness {
  pool: string
  ready: boolean
  checks: ActivationCheck[]
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
  legal_entity?: string | null
  legal_entity_name?: string | null
  branch?: string
  timezone?: string
  calendar?: string
  freeze_reason?: string
  frozen_at?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreatePoolInput {
  name: string
  code: string
  product: string
  effective_date: string
  legal_entity?: string | null
  branch?: string
  timezone?: string
  calendar?: string
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

export interface VersionDiffItem {
  category: string
  key: string
  label: string
  v1_value: unknown
  v2_value: unknown
  unit?: string | null
  is_changed: boolean
  format: "text" | "percentage" | "currency" | "number" | "bps" | "boolean"
  delta?: number | null
  change_direction?: "increased" | "decreased" | "modified" | "unchanged"
}

export interface TierDiffItem {
  code: string
  name: string
  v1_weight: number | null
  v2_weight: number | null
  v1_tenor_days: number | null
  v2_tenor_days: number | null
  is_changed: boolean
  delta: number | null
  change_type: "added" | "removed" | "modified" | "unchanged"
}

export interface PoolVersionDiffResponse {
  pool: {
    id: string
    name: string
    code: string
    status: string
  }
  v1: {
    id: string
    version_number: number
    is_current: boolean
    created_at: string | null
    created_by: string
    snapshot_hash: string
    shariah_resolution: string
  }
  v2: {
    id: string
    version_number: number
    is_current: boolean
    created_at: string | null
    created_by: string
    snapshot_hash: string
    shariah_resolution: string
  }
  summary: {
    total_changes: number
    field_changes_count: number
    tier_changes_count: number
    risk_impact: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    shariah_quorum_attested: boolean
    requires_regulatory_filing: boolean
  }
  diff_matrix: VersionDiffItem[]
  tiers_diff: TierDiffItem[]
}

export interface CreatePoolVersionInput {
  // A version seals the pool's current approved configuration; only these are supplied.
  change_rationale?: string
  effective_value_date?: string
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
  wakalah_fee_pct?: string
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
  wakalah_fee_pct?: string
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
  maturity_date?: string | null
  status: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface AssetProvisionEntry {
  id: string
  asset: string
  asset_reference: string
  pool: string
  pool_code: string
  entry_type: "provision" | "release" | "write_off" | "recovery"
  amount: string
  provision_utilised: string
  effective_date: string
  reason: string
  status: "pending" | "approved" | "rejected"
  rejection_reason: string
  created_by_name: string | null
  approved_by_name: string | null
  created_at: string
}

export interface CircleRulesData {
  id: string
  version: number
  contribution_amount: string
  cycle_days: number
  order_policy: string
  hardship_policy: string
  content_hash: string
}

export interface CircleRulesSummary {
  rules: CircleRulesData | null
  accepted: number
  total: number
  missing: string[]
}

export interface CircleDrawRecord {
  id: string
  sequence: number
  commitment: string
  server_seed: string | null
  client_seed: string
  status: "committed" | "executed"
  participants: string[]
  assignments: Array<{ member_reference: string; member_id: string; position: number }>
}

export interface CircleClosurePreview {
  members: Array<{ member_reference: string; member_name: string; contributed: string; received: string; net: string }>
  total_collected: string
  total_disbursed: string
  difference: string
  blockers: string[]
}

export interface AIRecommendation {
  id: string
  feature: string
  model_name: string
  model_version: string
  requested_by_name: string | null
  prompt_hash: string
  prompt_text: string
  output: unknown
  sources: unknown[]
  confidence: string | null
  reason: string
  requires_human_review: boolean
  is_fallback: boolean
  latency_ms: number
  disposition: "pending" | "accepted" | "rejected" | "overridden"
  disposed_by_name: string | null
  disposition_note: string
  created_at: string
}

export interface AIMetricsRow {
  model_name: string
  total: number
  pending: number
  decided: number
  acceptance_rate: number | null
  override_rate: number | null
  fallback_rate: number | null
  false_positive_rate: number | null
  confidence_drift: number | null
  avg_confidence: number | null
  avg_latency_ms: number
}

export interface PoolDisclosureRecord {
  id: string
  pool: string
  version: number
  summary: string
  terms: {
    contract: { type: string; name: string; version: string }
    profit_sharing: { investor_share_pct: number; manager_share_pct: number; wakalah_fee_pct: number } | null
    redemption: { notice_days: number; gate_pct_per_30_days: string }
  }
  terms_hash: string
  risk_warnings: string
  fee_statement: string
  status: "pending_review" | "published"
  approved_at?: string | null
  created_at: string
}

export interface AssetPosition {
  face_value: string
  provision_balance: string
  written_off: string
  recovered: string
  exposure: string
  recoverable_balance: string
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
  conflict_declaration: string
  benchmark_amount: string | null
  benchmark_source: string
  price_tolerance_pct: string
  price_test: "passed" | "failed" | "not_tested"
  approved_by: number | null
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
  conflict_declaration?: string
  benchmark_amount?: string | null
  benchmark_source?: string
}

export interface RelatedPartyReviewInput {
  decision: "recommended" | "flagged"
  notes?: string
}

export interface CreateAssetInput {
  reference_code: string
  asset_type: string
  description: string
  face_value: string
  maturity_date?: string
}

export interface AssetAssignment {
  id: string
  tenant: string
  asset: string
  pool: string
  assigned_date: string
  unassigned_date: string | null
  transfer_reason?: string
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
  account_number?: string
  participant_class?: string
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
  account?: string | null
  account_number?: string | null
  participant_name?: string | null
  daily_funds: string
  weightage: string
  weighted_funds: string
  allocated_amount: string
}

export interface AllocationRunInput {
  pool: string
  period_start?: string
  value_date: string
  // Omit gross_income/direct_expenses to derive them from the pool's posted ledger events.
  // A hand-typed gross_income is a manual override and needs an override_reason.
  gross_income?: string
  direct_expenses?: string
  override_reason?: string
}

export interface IncomeSource {
  mode: "derived_from_events" | "manual_override"
  event_count?: number
  event_ids?: string[]
  reason?: string
  excluded_non_permissible_income?: string
  excluded_bank_absorbed_overhead?: string
  derived_gross_income?: string
}

export interface SimulateAllocationResult {
  gross_income?: string
  direct_expenses?: string
  income_source?: IncomeSource
  warnings?: string[]
  distributable: string
  total_weighted_funds: string
  depositor_pool_share: string
  mudarib_share: string
  per_amount?: string
  irr_amount?: string
  rounding_residual?: string
  is_loss?: boolean
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
  allocation_run: string | null
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

export type CostClassification =
  | "direct_permissible"
  | "indirect_overhead"
  | "permissible_income"
  | "non_permissible_income"

export interface IncomeExpenseEvent {
  adjusted_from_date?: string | null
  settled_on?: string | null
  settlement_reference?: string
  id: string
  tenant: string
  pool: string
  pool_name?: string
  pool_code?: string
  event_type: "income" | "expense"
  cost_classification: CostClassification
  category: string
  amount: string
  pool_chargeable_amount: string
  bank_absorbed_amount: string
  is_direct_expense: boolean
  is_overhead_leakage: boolean
  quarantined_to_charity: boolean
  event_date: string
  description: string
  shariah_note?: string | null
  status: "pending" | "posted"
  created_by: number | null
  created_by_name?: string
  posted_by: number | null
  posted_by_name?: string
  posted_at: string | null
  created_at: string
  updated_at: string
}

export interface PoolIncomeExpenseSummary {
  pool_id: string | null
  total_income_gross: number
  non_permissible_income: number
  net_permissible_income: number
  total_expenses_claimed: number
  approved_direct_expenses: number
  bank_absorbed_overheads: number
  net_distributable_profit: number
  overhead_leakage_detected: boolean
  overhead_leakage_count: number
  quarantined_items_count: number
  pending_items_count: number
  total_records_count: number
}

export interface CreateIncomeExpenseEventInput {
  pool: string
  event_type: "income" | "expense"
  cost_classification?: CostClassification
  category: string
  amount: string | number
  event_date: string
  description: string
  shariah_note?: string
  book_in_adjustment_period?: boolean
}

export interface DepositorStatement {
  id: string
  allocation_run: string
  participant_class: string
  account?: string | null
  account_number?: string | null
  participant_name?: string | null
  period_start: string
  period_end: string
  opening_balance: string
  net_deposits: string
  profit_allocated: string
  closing_balance: string
  narrative: string
  narrative_translations?: Partial<Record<"ur" | "ur_roman" | "ar", string>>
  generated_at: string
}

export interface Participant {
  id: string
  reference: string
  full_name: string
  participant_class: string
  kyc_status: "pending" | "verified" | "rejected"
  cnic_ntn: string
  iban: string
  bank_name: string
  tax_status: string
  zakat_exempt: boolean
  default_channel: string
  nominee_name: string
  user: number | null
}

export interface ParticipantAccount {
  id: string
  participant: string
  participant_name: string
  participant_reference: string
  participant_class: string
  pool: string
  account_number: string
  opened_date: string
  closed_date: string | null
  status: string
}

export interface ApprovalStage {
  key: "prepared" | "independent_check" | "shariah_review" | "final_release"
  label: string
  owner: string
  state: "completed" | "in_review" | "draft" | "waiting" | "rejected"
  by: string | null
  at: string | null
}

export interface AllocationRun {
  id: string
  tenant: string
  pool: string
  period_start: string | null
  value_date: string
  gross_income: string
  direct_expenses: string
  distributable_amount: string
  total_weighted_funds: string
  depositor_pool_share: string
  mudarib_share: string
  per_amount: string
  irr_amount: string
  rounding_residual: string
  is_loss: boolean
  config_snapshot: Record<string, unknown>
  status: string
  calculation_hash: string | null
  created_by: number | null
  checked_by: number | null
  checked_at: string | null
  rejection_reason: string | null
  shariah_review_required: boolean
  released_by?: number | null
  released_at?: string | null
  stages?: ApprovalStage[]
  control_gates?: Array<{ key: string; label: string; passed: boolean }>
  run_tests?: Array<{ key: string; label: string; status: "pass" | "fail" | "warning" | "info"; detail: string }>
  shariah_signed_off_by: number | null
  shariah_signed_off_at: string | null
  shariah_review_note: string | null
  is_restatement?: boolean
  restatement_reason?: string | null
  replaces_run?: string | null
  lines: AllocationLine[]
  journal_batch: JournalBatch | null
  created_at: string
  updated_at: string
}

export interface DistributionInput {
  pool: string
  period_start: string
  period_end: string
  gross_income: string
  direct_expenses: string
}

export interface DistributionSimulationLine {
  capital_account_id: string
  investor_reference: string
  investor_name: string
  average_units: string
  share_ratio: string
  allocated_amount: string
}

export interface DistributionSimulation {
  distributable: string
  investor_share: string
  manager_share: string
  rounding_residual: string
  total_average_units: string
  is_loss: boolean
  lines: DistributionSimulationLine[]
}

export interface DistributionLine {
  id: string
  capital_account: string
  investor_reference: string
  investor_name: string
  average_units: string
  share_ratio: string
  allocated_amount: string
}

export interface DistributionRun {
  id: string
  pool: string
  period_start: string
  period_end: string
  gross_income: string
  direct_expenses: string
  distributable_amount: string
  investor_share: string
  manager_share: string
  rounding_residual: string
  total_average_units: string
  is_loss: boolean
  status: "simulated" | "pending_approval" | "checked" | "shariah_review" | "signed" | "rejected" | "reversed"
  calculation_hash: string
  replaces_run: string | null
  is_restatement: boolean
  restatement_reason: string | null
  rejection_reason: string | null
  lines: DistributionLine[]
  journal_batch_id: string | null
}

export interface CapitalStatement {
  capital_account: string
  investor_reference: string
  investor_name: string
  pool: string
  period_start: string
  period_end: string
  opening_units: string
  subscribed_units: string
  redeemed_units: string
  closing_units: string
  average_units: string
  nav_per_unit: string | null
  nav_date: string | null
  market_value: string | null
  total_profit_distributed: string
  profit_distributions: Array<{ run_id: string; period_start: string; period_end: string; average_units: string; amount: string }>
  movements: Array<{ date: string; type: string; units: string }>
}

export interface CapitalAccount {
  id: string
  pool: string
  is_managing_partner?: boolean
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
  is_managing_partner?: boolean
}

export interface NegligenceCase {
  id: string
  pool: string
  pool_code: string
  title: string
  allegation: string
  period_start: string
  period_end: string
  status: "open" | "liable" | "cleared"
  raised_by_name: string | null
  notes: Array<{ at: string; by: string; note: string }>
  determination_note: string
  liability_amount: string | null
  determined_by_name: string | null
  determined_at: string | null
  applied_run: string | null
  created_at: string
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
  status: "pending" | "processed" | "rejected" | string
  rejection_reason?: string
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

export interface ImpairmentEvent {
  id: string
  pool: string
  valuation_date: string
  loss_amount: string
  loss_percentage: string
  reason: string
  status: string
  approved_by: number | null
  created_at: string
  updated_at: string
}

export interface CreateNAVSnapshotInput {
  pool: string
  valuation_date: string
  total_pool_value: string
  launch_nav_per_unit?: string
}

export interface CircleMember {
  kyc_status?: string
  iban?: string
  bank_name?: string
  mandate_reference?: string
  mandate_bank?: string
  mandate_verified_at?: string | null
  guarantor_name?: string
  guarantor_reference?: string
  id: string
  pool: string
  member_name: string
  member_reference: string
  payout_position: number | null
  status: "active" | "paid_out" | "withdrawn"
  joined_date: string
  created_at: string
  updated_at: string
}

export interface CreateCircleMemberInput {
  pool: string
  member_name: string
  member_reference: string
  joined_date: string
  email?: string
  iban?: string
  bank_name?: string
  mandate_reference?: string
  mandate_bank?: string
  guarantor_name?: string
  guarantor_reference?: string
}

export interface RunDrawResponse {
  seed: string
  assignments: { member_id: string; position: number }[]
}

export interface Contribution {
  id: string
  member: string
  member_reference: string
  member_name: string
  pool: string
  pool_name: string
  pool_code: string
  amount: string
  contribution_date: string
  cycle_number: number
  status: "pending" | "received"
  created_at: string
  updated_at: string
}

export interface RecordContributionInput {
  amount: string
  contribution_date: string
  cycle_number: number
  payment_reference: string
}

export interface Payout {
  id: string
  member: string
  member_reference?: string
  member_name?: string
  pool: string
  pool_name?: string
  pool_code?: string
  cycle_number: number
  amount: string
  payout_date: string
  status: "pending" | "approved" | "disbursed" | "rejected"
  requested_by?: number | null
  rejection_reason?: string | null
  disbursed_by: number | null
  disbursed_by_username?: string
  draw_seed: string | null
  settlement_rail?: string
  settlement_utr?: string
  recipient_iban?: string
  recipient_bank?: string
  secondary_approved_by?: number | null
  secondary_approved_by_username?: string
  secondary_approved_at?: string | null
  shariah_compliance_status?: string
  shariah_certificate_number?: string
  biometric_auth_ref?: string
  ceremony_hash?: string
  created_at: string
  updated_at: string
}


export interface PayoutCheck {
  key: string
  label: string
  passed: boolean
  detail: string
}

export interface PayoutCeremonyReadiness {
  pool: {
    id: string
    name: string
    code: string
    status: string
    total_members: number
  }
  cycle_number: number
  next_recipient: {
    member_id: string
    member_name: string
    member_reference: string
    payout_position: number
    kyc_status: string
    iban: string
    bank_name: string
  } | null
  pot_summary: {
    total_collected_pot: number
    is_pot_fully_funded: boolean
    total_active_members: number
    received_count: number
    pending_count: number
    pending_members: Array<{ id: string; name: string; reference: string }>
  }
  checks: PayoutCheck[]
  can_request: boolean
  shariah_decision: { decision_code: string; title: string } | null
  open_payout: Payout | null
  settlement_rails_options: Array<{ key: string; title: string }>
  historical_payouts: Payout[]
}

export interface RequestPayoutInput {
  member_id: string
  settlement_rail?: string
  payout_date?: string
}

export interface SettlePayoutInput {
  settlement_utr?: string
  biometric_auth_ref?: string
}

export interface PayoutReceiptData {
  payout_id: string
  circle_name: string
  circle_code: string
  recipient_name: string
  recipient_reference: string
  cycle_number: number
  amount: number
  payout_date: string
  status: string
  settlement_rail: string
  settlement_utr: string | null
  recipient_iban: string
  recipient_bank: string
  requested_by: string | null
  secondary_approved_by: string | null
  secondary_approved_at: string | null
  settled_by: string | null
  shariah_certificate_number: string | null
  biometric_auth_ref: string | null
  ceremony_hash: string | null
}

export interface ArrearsRecord {
  id: string
  member: string
  cycle_number: number
  expected_amount: string
  status: "overdue" | "hardship_granted" | "resolved"
  hardship_reason: string | null
  reviewed_by: number | null
  reviewed_at: string | null
  created_at: string
  updated_at: string
}

export interface FlagArrearsInput {
  cycle_number: number
  expected_amount: string
}

export interface CircleVote {
  id: string
  proposal: string
  member: string
  member_reference: string
  member_name: string
  decision: "approve" | "reject" | "abstain"
  voted_at: string
  created_at: string
  updated_at: string
}

export interface CircleProposal {
  id: string
  pool: string
  title: string
  description: string
  proposal_type: "amount_change" | "member_addition" | "rule_change" | "other"
  status: "open" | "approved" | "rejected" | "closed"
  created_by: number | null
  voting_deadline: string
  closed_at: string | null
  votes: CircleVote[]
  created_at: string
  updated_at: string
}

export interface CreateCircleProposalInput {
  pool: string
  title: string
  description: string
  proposal_type: "amount_change" | "member_addition" | "rule_change" | "other"
  voting_deadline: string
}

export interface RecordVoteInput {
  member_id: string
  decision: "approve" | "reject" | "abstain"
  method: "in_person" | "otp" | "e_sign"
  evidence_reference?: string
}

export interface CloseProposalResponse extends CircleProposal {
  vote_counts: {
    approve: number
    reject: number
    abstain: number
  }
}

export interface GrantHardshipInput {
  hardship_reason: string
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
  sla_days?: number
  sla_due_on?: string
  sla_breached?: boolean
  sla_basis?: string
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
  quarantine_status: "none" | "held" | "decided"
  quarantined_amount: string | null
  quarantine_reason: string
  quarantined_at: string | null
  quarantine_treatment: string
  treatment_note: string
  disclosure_note: string
  created_at: string
  updated_at: string
}

export interface UpdateExceptionAssigneeInput {
  assigned_to: number
}

export interface SupportRequest {
  id: string
  pool: string | null
  request_type: string
  subject: string
  description: string
  raised_by_name: string
  status: string
  priority: string
  assigned_to: number | null
  resolution_notes: string | null
  resolved_by: number | null
  resolved_at: string | null
  created_at: string
  updated_at: string
}

export interface CreateSupportRequestInput {
  pool?: string
  request_type: string
  subject: string
  description: string
  raised_by_name: string
  priority?: string
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

export type ShariahDecisionType =
  | "product_approval"
  | "policy_ruling"
  | "annual_review"
  | "purification_directive"
  | "exemption"

export interface ShariahQuorumVote {
  id: string
  decision: string
  scholar_name: string
  scholar_title: string
  decision_vote: "approve" | "reject" | "abstain"
  fiqh_concurrence_notes: string
  digital_signature_hash: string
  voted_at: string
  signatory_user_name?: string | null
}

export interface ShariahQuorumSummary {
  required_votes: number
  board_size?: number
  approvals: number
  rejections: number
  is_quorum_met: boolean
  status_label: string
}

export interface ShariahDecision {
  review_round?: number
  return_note?: string
  scope?: string
  supersedes?: string | null
  id: string
  tenant: string
  decision_code: string
  title: string
  decision_type: ShariahDecisionType
  meeting_reference?: string | null
  scholars_signatories?: string | null
  fiqh_reference?: string | null
  description: string
  mandatory_caveats?: string | null
  fatwa_arabic_text?: string | null
  status: "draft" | "returned" | "rejected" | "approved" | "superseded"
  effective_date: string
  expiry_date?: string | null
  document_url?: string | null
  created_by?: number | null
  created_by_name?: string | null
  approved_by?: number | null
  approved_by_name?: string | null
  approved_at?: string | null
  is_active: boolean
  created_at: string
  updated_at: string
  quorum_votes?: ShariahQuorumVote[]
  quorum_summary?: ShariahQuorumSummary
}

export interface CreateShariahDecisionInput {
  scope?: string
  supersedes?: string | null
  decision_code: string
  title: string
  decision_type?: ShariahDecisionType
  meeting_reference?: string | null
  scholars_signatories?: string | null
  fiqh_reference?: string | null
  description: string
  mandatory_caveats?: string | null
  fatwa_arabic_text?: string | null
  effective_date: string
  expiry_date?: string | null
  document_url?: string | null
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
  "authorized_signatory",
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

export interface AuditLogEntry {
  id: string
  tenant: string | null
  actor: number | null
  actor_email: string | null
  action: string
  model_name: string
  object_id: string
  changes: Record<string, unknown> | null
  reason: string | null
  ip_address: string | null
  created_at: string
}

export interface AuditLogFilters {
  model_name?: string
  date_from?: string
  date_to?: string
  tenant?: string
}

export interface LiquidityForecast {
  pool: string
  as_of_date: string
  horizon_days: number
  insufficient_data: boolean
  current_balance: string | null
  trend_per_day: string | null
  known_outflows: string | null
  projected_balance: string | null
}

export interface ReservePolicy {
  id: string
  tenant: string
  pool: string
  pool_name?: string
  pool_code?: string
  reserve_type: 'per' | 'irr'
  /** % of profit (PER) or of the investors' share (IRR) appropriated each run */
  rate_percentage: string
  /** maximum reserve balance as a % of pool funds */
  cap_percentage: string
  /** system-controlled: moves only with signed runs */
  current_balance: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface RestatementInput {
  restatement_reason: string
  notes?: string
  gross_income?: string | number
  direct_expenses?: string | number
}

export type ReconciliationStatus = 'pending' | 'matched' | 'variance_flagged' | 'cleared' | 'discrepancy' | 'resolved'

export interface ReconciliationItem {
  id: string
  tenant?: string
  batch?: string
  account_reference?: string
  source_reference?: string
  cbs_amount?: string
  cbs_balance?: string
  gl_amount?: string
  gl_balance?: string
  variance: string
  status: string
  resolution_notes?: string | null
  variance_reason?: string | null
  resolved_at?: string | null
  created_at?: string
}

export interface ReconciliationBatch {
  id: string
  tenant?: string
  pool: string
  pool_name?: string
  pool_code?: string
  reconciliation_date?: string
  batch_date?: string
  source_system?: string
  total_records?: number
  matched_records?: number
  matched_items_count?: number
  exception_count?: number
  unmatched_items_count?: number
  variance_amount?: string
  total_variance?: string
  total_cbs_balance?: string
  total_gl_balance?: string
  control_total_status?: string
  status: ReconciliationStatus
  notes?: string | null
  performed_by?: number | null
  reconciled_by?: number | null
  reconciled_by_name?: string | null
  reconciled_at?: string | null
  items?: ReconciliationItem[]
  created_at?: string
  updated_at?: string
}

export type PeriodCloseStatus = 'open' | 'in_review' | 'pending_review' | 'certified' | 'locked'

export interface PeriodCloseChecklist {
  id: string
  tenant: string
  pool: string
  pool_name?: string
  pool_code?: string
  period_start: string
  period_end: string
  status: PeriodCloseStatus
  checklist_data?: Record<string, boolean>
  checklist_items?: Record<string, boolean>
  decision_note?: string | null
  certified_by: number | null
  certified_by_name?: string | null
  certified_at: string | null
  locked_by?: number | null
  locked_by_name?: string | null
  locked_at?: string | null
  lock_hash?: string
  notes?: string
  created_at: string
  updated_at: string
}

export type AuditPlanStatus = 'draft' | 'approved' | 'in_progress' | 'completed'
export type AuditSeverity = 'low' | 'medium' | 'high' | 'critical'
export type FindingStatus = 'open' | 'under_review' | 'remediated' | 'closed'

export interface ShariahAuditFinding {
  id: string
  tenant: string
  audit_plan: string
  finding_ref: string
  title: string
  description: string
  severity: AuditSeverity
  shariah_standard_ref: string
  remediation_plan: string
  status: FindingStatus
  identified_date: string
  remediation_deadline: string | null
  created_at: string
  updated_at: string
}

export interface ShariahAuditPlan {
  id: string
  tenant: string
  year: number
  title: string
  universe_scope: string
  target_samples: number
  tested_samples: number
  findings_count: number
  status: AuditPlanStatus
  approved_by: number | null
  approved_by_name?: string | null
  findings?: ShariahAuditFinding[]
  created_at: string
  updated_at: string
}

export interface JurisdictionRulePack {
  id: string
  tenant: string
  code: string
  name: string
  version: string
  effective_date: string
  is_active: boolean
  is_default: boolean
  description: string
  rules_config: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface AuditLogEntry {
  id: string
  tenant: string | null
  actor: number | null
  actor_email: string | null
  action: string
  model_name: string
  object_id: string
  changes: Record<string, unknown> | null
  reason: string | null
  ip_address: string | null
  created_at: string
}

export interface LegalEntityRecord {
  id: string
  tenant: string
  name: string
  registration_number: string | null
  jurisdiction: string
  base_currency: string
  timezone: string
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface TenantRecord {
  id: string
  name: string
  code: string
  domain: string | null
  data_residency: string
  is_suspended: boolean
  is_active: boolean
  user_count: number
  pool_count: number
  legal_entities: LegalEntityRecord[]
  created_at: string
  updated_at: string
}

export interface CreateTenantInput {
  name: string
  code: string
  domain?: string
  data_residency: string
}

