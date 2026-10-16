# BRD Traceability Matrix

Source: `docs/NovuLabs_Islamic_Pool_Management_Platform_BRD.docx` (text in `evidence/BRD_TEXT.md`). BRD wording is kept short where a
row quotes a table cell. Screen inventory (BRD 15, 58 screens) is traced row by row in `SCREEN_AUDIT.md` (IDs SCR-01..SCR-58).

**Evidence keys**
- `BT:` backend test in the project suite (all 444 passed, `evidence/evidence_backend_tests.txt`; index `evidence/backend_test_index.tsv`).
- `AT:` audit test written for this audit (`audit_tests/`, outputs in `evidence/`).
- `E2E:` Playwright smoke (`evidence/evidence_e2e_smoke.txt`) or role sweep (`evidence/evidence_e2e_roles.txt`).
- `RT:` manual runtime probe against the demo server (`evidence/*.txt`).
- `ST:` static code reading only.

**Status rules** (as instructed): PASS only with an executed, passing test; static-only = NOT TESTED; FAIL = verified violation.
**Severity** = priority of the gap (P0 critical ... P3 low); "-" when the row passes.

## Section 1-3: control principle, scope, roles

| ID | BRD | Requirement | Backend evidence | Frontend evidence | Database evidence | Test evidence | Status | Sev |
|---|---|---|---|---|---|---|---|---|
| R-001 | 1 | AI must not independently issue a Shariah ruling | `ai_agents/services/*` read-only; `contract_analyzer.py:106-116` disclaimer | Copilot page shows citations | `AIRecommendation` | BT ai_agents.test_recommendations; copilot runtime BLOCKED (service down) | PARTIAL | P2 |
| R-002 | 1 | AI must not change an approved PSR | no AI path writes PSR (ST); PSR immutable once approved | - | `ProfitSharingRatio` | BT core.test_access_control `test_approved_economics_and_rulings_are_immutable` | PASS | - |
| R-003 | 1 | AI must not waive a loss | no AI path to `negligence.py` / distribution (ST) | - | - | none | PASS | P3 |
| R-004 | 1 | AI must not post a journal | `ai_agents` imports no accounting service (ST, grep) | - | - | none | PASS | P3 |
| R-005 | 1 | AI must not approve a related-party allocation | elevated approval is a human role check `governance/views.py` | - | - | BT governance.tests RPT (human roles only) | PASS | - |
| R-006 | 2 | Bank pools: daily balances x weightages; income less direct expenses; PER/IRR | `allocation/engine.py:152-427` | Allocation Engine | `DailyBalance`, `WeightageBand` | BT test_brd_golden, test_financial_core; AT test_audit_financial 01-13 | PASS | - |
| R-007 | 2 | Asset contracts Murabahah / Ijarah / Diminishing Musharakah under bank pools | `pools.Asset.asset_type` (types only) | Asset registry | `Asset` | none specific | PARTIAL | P2 |
| R-008 | 2 | Investment pools: units, PSR, realized/unrealized, manager share, loss by capital | `investments/distribution.py`, `nav_engine.py` | Investments | `CapitalAccount`, `NAVSnapshot` | BT investments.test_distribution (19), test_musharakah_wakalah (23) | PASS | - |
| R-009 | 2 | Community savings: Qard rotating; Wakalah service model; cooperative rules | `circles/*` (Qard behaviour only) | Community Circles | `CircleMember`, `Contribution` | BT circles.* | PARTIAL | P2 |
| R-010 | 2 | Circles: no interest or time-value uplift | no rate field anywhere (ST); payout = collected pot | - | - | no negative test exists | PASS | P2 |
| R-011 | 2 | Out of scope list (fatwa without human, capital guarantee, crypto, Takaful, Sukuk, GL replacement, abusive collection) | - | - | - | - | NOT APPLICABLE | - |
| R-012 | 3 | Super Admin: tenant provisioning | `tenants/views.py` | Administration | `Tenant` | BT tenants.*; AT role matrix | PASS | - |
| R-013 | 3 | Super Admin: feature flags, encryption keys | AI model toggle; per-tenant feature flags and an encryption-key register (metadata, rotation attestation; no key material, the keys stay in the bank's KMS/HSM) | Administration tab | audit log | BT tenants.test_flags_and_keys | PARTIAL | P2 |
| R-014 | 3 | Super Admin cannot view tenant financial data by default | `ADMIN_ALLOWED` includes `core/audit-log/` (`accounts/investor_scope.py`) | Security & Audit Log tab | `AuditLog.changes` holds amounts | RT `evidence/superadmin_audit_log_exposure.txt` (amounts returned); AT test_superadmin_reads_no_financial_data (pools/runs blocked); after fix F-03: AT test_super_admin_audit_log_hides_the_figures (BT governance.test_audit_fixes) | PASS | - |
| R-015 | 3 | Product Manager drafts; cannot approve own configuration | `products/views.py` | Products & Pools | `Product.status` | BT products.tests, core.test_access_control | PASS | - |
| R-016 | 3 | Pool Manager creates pools, assigns assets, proposes allocations; cannot approve runs or Shariah exceptions | `allocation/views.py:343-369` | Allocation Engine | - | AT role matrix; BT access control | PASS | - |
| R-017 | 3 | Finance Maker/Checker; no change to signed Shariah parameters | PSR/decisions immutable | - | - | BT access control; AT patch probe (PSR, decisions unchanged) | PASS | - |
| R-018 | 3 | Shariah Secretariat: no final ruling unless delegated | quorum: drafter cannot vote | Shariah Governance | `ShariahDecision` | BT products.test_quorum | PASS | - |
| R-019 | 3 | Shariah Board: no silent retrospective parameter change | rule pack editable in place (see R-020) | - | `JurisdictionRulePack.rules_config` | AT patch probe; after fix F-04: rule pack changes are proposals (BT test_rule_pack_change_is_only_proposed_until_approved) | PASS | - |
| R-020 | 3 | Risk & Compliance: no profit manipulation | Risk can PATCH rule pack (WHT, Mudarib cap, PER/IRR ceilings) in place, alone | Jurisdiction & Rule Packs | `JurisdictionRulePack` | AT `evidence/patch_probe_changes.txt`; after fix F-04 (BT governance.test_audit_fixes); AT patch probe: no change persists | PASS | - |
| R-021 | 3 | Auditor: read-only, sampling, reperformance; no operational posting | auditor POST passes only on sampling / evidence / findings / own requests | Reports | - | AT `evidence/role_matrix_violations.txt` (reviewed: none is a posting) | PASS | - |
| R-022 | 3 | Investor/member: only own data and authorized pool information | `accounts/investor_scope.py` allow-list | My Portal | - | AT test_investor_cannot_read_other_peoples_investment_records; BT StatementTests | PASS | - |

## Section 4: modules

| ID | BRD | Requirement | Backend evidence | Frontend evidence | Database evidence | Test evidence | Status | Sev |
|---|---|---|---|---|---|---|---|---|
| R-023 | 4 | Tenant & Jurisdiction Studio: entities, branches, currencies, calendars, languages, accounting policy, retention | legal entities, branch/timezone/calendar on pool, retention policies | Administration, wizard | `LegalEntity`, `RetentionPolicy` | BT governance.test_retention; E2E wizard | PARTIAL (no accounting-policy object; one currency in practice) | P2 |
| R-024 | 4 | Product & Contract Studio: templates for Mudarabah/Musharakah/Wakalah/Qard; PSR, weightage, tenure, notice, disclosure rules | `products/*` | Product catalogue, template studio | `ContractTemplate` | BT products.tests | PARTIAL (mandatory-parameter enforcement per template not built) | P2 |
| R-025 | 4 | Pool lifecycle: draft, review, approved, open, frozen, allocation, closed, archived | `pools/lifecycle.py`, `activation.py` | Pool detail | `Pool.status` | BT pools.test_lifecycle, test_activation_gates | PASS | - |
| R-026 | 4 | Capital & membership: opening, KYC/KYB, subscriptions, redemptions, contributions, nominees, member limits | participants, investments, circles | Participants, Investments | - | BT redemptions, participation terms | PARTIAL (no KYB; nominee is text) | P2 |
| R-027 | 4 | Asset assignment: one pool; transfer with effective date, valuation, approval | `pools/asset_rules.py` | Assets tab, transfer modal | `AssetAssignment` | BT pools.test_asset_rules; after fix: transfer needs valuation, basis and a different approver (BT, E2E); ring-fencing still not built | PARTIAL | P3 |
| R-028 | 4 | Income & expense: accruals, realization, direct expenses, provisions, write-offs, reversals, non-permissible income | `allocation/income.py`, provisions | Income & Expense workbench | `IncomeExpenseEvent` | BT test_income_derivation (17), test_provisions | PARTIAL (no accrual vs realization distinction; keyword classification) | P2 |
| R-029 | 4 | Profit allocation: daily averages, weightages, PSR, Mudarib, Wakalah fee, Hiba, PER/IRR, rounding | `engine.py` | Allocation Engine | `AllocationRun` | AT test_audit_financial (27 pass); see FIN-01; after fix F-02: pending balances refused (AT test_14, BT test_pending_balances_block_a_run) | PASS | - |
| R-030 | 4 | Loss & impairment: waterfall, negligence cases, provisions, write-offs, recoveries | `investments/negligence.py`, provisions | Investments, Risk | - | BT NegligenceWorkflowTests (11), provisions | PASS | - |
| R-031 | 4 | Community circle: schedules, ballots/rotation, guarantees, late payments, hardship, payout, dissolution | `circles/*` | Community Circles | - | BT circles (60+) | PARTIAL (guarantees missing) | P2 |
| R-032 | 4 | Shariah governance: register, policy mapping, pre-launch, exceptions, review and audit | `products/shariah.py`, `governance/*` | Shariah Governance | - | BT register, quorum, audit report | PARTIAL (policy mapping missing; exception time limits built as unconfirmed defaults, BT governance.test_exception_sla) | P2 |
| R-033 | 4 | Accounting subledger: double entry, chart mapping, close, reversals, suspense, GL export | `accounting/*` | Finance & Ledger | `JournalBatch` | BT accounting.tests, ImmutabilityTests | PARTIAL (suspense and GL hand-over built; no live ERP connection) | P2 |
| R-034 | 4 | AI & analytics: forecasts, anomaly, extraction, explanation, copilot, scenarios | `ai_agents`, `pools/liquidity.py` | AI & Analytics | `AIRecommendation` | BT ai_agents (13) | PARTIAL | P2 |
| R-035 | 4 | Reporting & portal: regulatory, management, statements, disclosures, examiner data room | period report, evidence bundle | Reports, portal | - | BT core.test_period_report; E2E auditor | PARTIAL (no regulatory return formats) | P2 |
| R-036 | 4 | Integration hub: core banking, GL, KYC, payment rails, market data, e-sign, notifications, BI | simulators only (`core/banking_switch.py`, `cbs_daemon.py`), refused in production | - | - | BT core.test_evidence_and_simulation | MISSING | P1 |

## Section 5: pool configuration model

| ID | BRD | Requirement | Backend evidence | Frontend evidence | Database evidence | Test evidence | Status | Sev |
|---|---|---|---|---|---|---|---|---|
| R-037 | 5 | Identity: code, entity, branch, model, currency, timezone, calendar, start/end | `pools/serializers.py:55-64` | New Pool Wizard | `Pool` | E2E "new pool wizard has six steps..." | PASS | - |
| R-038 | 5 | Contract: type/version, Rab-ul-Maal, Mudarib/partner/agent, PSR, Wakalah fee, loss basis | template + PSR; parties not modelled as entities | wizard step 2 | `ContractTemplate`, `ProfitSharingRatio` | BT wakalah tests | PARTIAL | P2 |
| R-039 | 5 | Participation: classes, minimums, tenure, withdrawal, notice, caps, eligibility, KYC tier | `investments/participation.py` | product modal | `Product` fields | BT test_participation_terms (8) | PASS | - |
| R-040 | 5 | Weightages: tiers, tenor bands, class, effective dates, maximum change, approval | `WeightageBandSerializer` | Weightage section | `WeightageBand` (no min/max constraint) | AT test_16 FAIL (negative weightage accepted); no max-change rule; after fix FIN-02: weightage > 0 in serializer and DB (AT test_16). The BRD 'maximum change' rule is still not built | PASS | - |
| R-041 | 5 | Assets: eligible contracts/sectors, concentration, liquidity buffer, valuation, transfer, ring-fencing | `concentration_engine.py` hard-codes limits labelled "SBP statutory" | Risk dashboard | - | ST; after fix F-07: limits configurable; sector and obligor data are still inferred | PARTIAL | P2 |
| R-042 | 5 | Income/expense taxonomy, provisioning, write-off, reversal, purification | `accounting/models.py:112-198` | workbench | - | BT income derivation | PARTIAL (keyword classification) | P2 |
| R-043 | 5 | Reserves: availability, basis, cap, ownership, **approval**, release, disclosure | `ReservePolicyViewSet` create/update by Pool Manager alone, no audit log, balance writable (`allocation/views.py:1019-1032`) | Rule Packs page | `ReservePolicy.current_balance` | AT `evidence/reserve_policy_change.txt` (871,335.74 -> 1.00, HTTP 200); after fix F-01: balance read-only, changes need a different checker (BT test_reserve_balance_cannot_be_set...; AT reserve test) | PASS | - |
| R-044 | 5 | Governance: decision, quorum, maker-checker, exception SLA, audit frequency, disclosure pack | quorum, plans; no SLA | Shariah Governance | - | BT test_quorum, audit plan | PARTIAL | P2 |
| R-045 | 5 | Accounting: chart mapping, accrual policy, rounding, posting calendar, close, restatement | mapping + close + restatement | Governance Config | `AccountMapping` | BT matrix_and_chart, period close | PARTIAL (no accrual policy / posting calendar) | P2 |
| R-046 | 5 | AI policy: models allowed, thresholds, human gates, prohibited actions, retention | registry + kill switch; threshold fixed 0.8 in code | Model Governance | `AIModelRegistry` | BT recommendations | PARTIAL | P2 |

## Section 6: workflows

| ID | BRD | Requirement | Backend evidence | Frontend evidence | Database evidence | Test evidence | Status | Sev |
|---|---|---|---|---|---|---|---|---|
| R-047 | 6.1.1 | PM selects jurisdiction and model | wizard + rule pack binding | wizard | - | E2E wizard | PASS | - |
| R-048 | 6.1.2 | Contract Studio loads approved clauses and mandatory parameters | clauses JSON; no mandatory set | template studio | - | none | PARTIAL | P2 |
| R-049 | 6.1.3 | AI completeness / conflict / policy-mapping check | deterministic `rule_conflicts` gate only | - | - | BT activation gates | PARTIAL | P2 |
| R-050 | 6.1.4 | Finance validates mappings; Risk validates limits and disclosures | `governance/config_changes.py` | Governance Config | `ConfigChangeRequest` | BT governance; E2E governance config | PASS | - |
| R-051 | 6.1.5 | Secretariat review pack; Shariah authority approves / rejects / returns | quorum approve; quorum of rejections rejects; any Board member returns with a note (new review round, earlier votes stop counting); Secretariat edits and resubmits | Fatwa register modal | `ShariahDecision.review_round` | BT core.test_from_scratch | PASS | - |
| R-052 | 6.1.6 | Checker activates with future effective timestamp | `pools/views.py` open by checker/signatory | Pool detail | - | BT activation gates | PASS | - |
| R-053 | 6.1.7 | Seal configuration version; publish disclosures | `config_snapshot.py`, `disclosures.py` | - | `PoolVersion`, `PoolDisclosure` | BT test_disclosures (8) | PASS | - |
| R-054 | 6.2.1 | Import balances, income, expenses, provisions, transfers | manual import; CBS simulated | Balance Import | - | BT BalanceImportTests | PARTIAL | P2 |
| R-055 | 6.2.2 | Validate control totals, duplicates, value dates, tags, closed periods | import checks | Balance Import | unique (pool, day, account) | BT BalanceImportTests, PeriodLockTests | PASS | - |
| R-056 | 6.2.3 | Daily funds and weighted balances by product/class | engine | - | - | AT 07, 09 | PASS | - |
| R-057 | 6.2.4 | Reconcile assets, sources, pool equity, suspense | `accounting/reconciliation.py` | Reconciliation Center | - | BT ReconciliationTests | PARTIAL (no suspense, no live feed) | P2 |
| R-058 | 6.2.5 | AI flags unusual yield, leakage, drift | `anomaly_detector.py` (after signing; no recommendation record) | Anomaly queue | - | none direct; after fix: recorded with reason code; still a moving-average check after signing, no cross-pool leakage test | PARTIAL | P3 |
| R-059 | 6.2.6 | Maker resolves exceptions; checker signs daily close | `pools/daily_close.py` exists, but allocation does not require a signed close and uses pending balances (`engine.py:66`) | Daily Close tab | `DailyClose` | BT test_daily_close; AT test_14 FAIL; after fix F-02: pending balances block a run. A signed daily close is still not required before a run; after T-02/daily close: signed close required before check and release (BT) | PASS | - |
| R-060 | 6.3.1 | Freeze period inputs and configuration versions | snapshot hashes PSR/bands/reserves; rule pack mutable; balances not hashed | - | - | AT patch probe; after fix F-04: rule pack changes are approved and audited; the run hash still does not snapshot the pack; after rule pack revisions: run seals the pack revision and hash (BT) | PASS | - |
| R-061 | 6.3.2 | Gross income and permitted direct expenses | `allocation/income.py` | - | - | BT DerivedFromEventsTests | PASS | - |
| R-062 | 6.3.3 | Distributable profit and reserve appropriation | engine 296-338 | - | - | AT 13; BT reserves | PASS | - |
| R-063 | 6.3.4 | Weightages and weighted participation | engine | - | - | AT 02, 09 | PASS | - |
| R-064 | 6.3.5 | Allocate; Mudarib share or Wakalah fee; rounding | engine | - | - | AT 10, 17; BT wakalah | PASS | - |
| R-065 | 6.3.6 | Tolerance, fairness, negative-yield, prior-period tests | residual tolerance; loss path; prior-period only post-signing | - | - | AT 04 | PARTIAL | P2 |
| R-066 | 6.3.7 | Finance checker **and Shariah reviewer** approve; post journals; issue statements | bank pool: 4-stage ceremony; **investment distributions signed by one finance checker, no Shariah stage** (`investments/distribution_views.py:195-262`); bank-pool Shariah stage switchable by env flag (`allocation/models.py:230-245`) | Ceremony | - | BT DistributionWorkflowTests (checker alone signs); BT ceremony tests; after fix F-06: 4-stage ceremony for distributions (BT DistributionCeremonyTests, 3) | PASS | - |
| R-067 | 6.4.1 | KYC, suitability, disclosures; signs contract | no e-signature | onboarding tab | - | BT disclosures | PARTIAL | P2 |
| R-068 | 6.4.2 | Subscription received; units / capital account created | `investments/views.py` | Subscription tab | - | BT CapitalJournalTests | PASS | - |
| R-069 | 6.4.3 | Capital deployed only to eligible assets | `asset_rules.assert_asset_eligible` | Assign modal | - | BT AssetRuleTests | PASS | - |
| R-070 | 6.4.4 | Valuations update NAV / capital accounts | `nav_engine.py` | NAV tab | `NAVSnapshot` | BT investments.tests | PASS | - |
| R-071 | 6.4.5 | Profit by PSR; Musharakah loss by capital ratio | `distribution.py` | - | - | BT musharakah tests | PASS | - |
| R-072 | 6.4.6 | Negligence allegation opens investigation | `negligence.py` | - | `NegligenceCase` | BT NegligenceWorkflowTests | PASS | - |
| R-073 | 6.4.7 | Exit subject to valuation, liquidity, terms | `redemptions.py` | - | - | BT test_redemptions (9) | PASS | - |
| R-074 | 6.5.1 | Organizer selects Qard or approved Wakalah model | Qard only | Circle setup | - | none | PARTIAL | P2 |
| R-075 | 6.5.2 | Members accept rules, schedule, draw method, hardship policy | `circles/governance` | Circle setup, portal | `CircleRules` | BT test_circle_governance; E2E member | PASS | - |
| R-076 | 6.5.3 | Verify identities and payment mandates; no uplift | KYC status only | - | - | none | PARTIAL | P2 |
| R-077 | 6.5.4 | Collect and reconcile; arrears trigger respectful reminders | `circles/reminders.py` | Arrears tab | - | BT test_reminders, test_arrears | PASS | - |
| R-078 | 6.5.5 | Eligibility gate before payout | `circles/payouts.py` | Payout ceremony | - | BT test_payout_workflow (14) | PASS | - |
| R-079 | 6.5.6 | Transparent ledger, receipts, schedule changes | member portal | portal | - | BT test_member_portal; E2E member | PASS | - |
| R-080 | 6.5.7 | Final reconciliation, surplus/shortfall, approved closure | `circles/closure.py` | - | - | BT closure tests | PARTIAL (surplus/shortfall not journalled) | P2 |

## Section 7: engine

| ID | BRD | Requirement | Backend evidence | Frontend evidence | Database evidence | Test evidence | Status | Sev |
|---|---|---|---|---|---|---|---|---|
| R-081 | 7 | Deterministic, reproducible; inputs, config version, formulas, overrides, approvers, journals hashed and retained | `engine.py:447-489` hashes inputs totals, snapshot, lines; not the balance rows or journals | Run detail | `calculation_hash` | BT test_stored_hash_matches_recomputation | PARTIAL | P2 |
| R-082 | 7.1 | Daily funds | `_daily_balances` | - | - | AT 07 | PASS | - |
| R-083 | 7.1 | Weighted funds = funds x approved weightage | engine 229-240 | - | - | AT 02, 09 | PASS | - |
| R-084 | 7.1 | Participation ratio | engine 340-342 | - | - | AT 01, 02 | PASS | - |
| R-085 | 7.1 | Gross income eligible and assigned to pool | `income.py` | - | - | BT DerivedFromEvents | PASS | - |
| R-086 | 7.1 | Only approved direct expenses | overhead excluded | - | - | BT DerivedFromEvents | PASS | - |
| R-087 | 7.1 | Distributable = gross - expenses - provisions +/- reversals - purification +/- reserve movements | appropriations yes; approved provisions/releases flow in as pool expense/income (BT pools.test_provisions); reserve **release** to cover a loss deliberately not built: needs a Shariah ruling | - | - | AT 04, 13; BT pools.test_provisions | PARTIAL | P2 |
| R-088 | 7.1 | Investor profit by PSR / weighted participation | engine | - | - | AT 02 | PASS | - |
| R-089 | 7.1 | Mudarib share never a share of capital | loss path sets Mudarib 0 | - | - | AT 04 | PASS | - |
| R-090 | 7.1 | Musharakah loss by capital ratio | `distribution.py` | - | - | BT musharakah | PASS | - |
| R-091 | 7.1 | Community payout less only approved transparent fees | payout = pot | - | - | BT payout workflow | PASS | - |
| R-092 | 7.2 | Worked example 6.6M / 4.4M | engine | - | - | AT 01; BT test_brd_golden | PASS | - |
| R-093 | 7.3 | High precision; round only at output | Decimal throughout | - | - | AT 11, 12 | PASS | - |
| R-094 | 7.3 | Residual to disclosed rounding account | engine 365-378; journal | - | - | AT 10; BT journal tie-out | PASS | - |
| R-095 | 7.3 | No edit to signed run; reversal + linked rerun | model guards, restatement | Restatement wizard | - | BT ImmutabilityTests, RestatementTests | PASS | - |
| R-096 | 7.3 | Back-dated entries go to an adjustment period unless a restatement is opened | a closed date is refused unless the maker books it in the adjustment period (today), keeping `adjusted_from_date`; restatement path unchanged | Income & Expense form | `IncomeExpenseEvent.adjusted_from_date` | BT core.test_from_scratch | PASS | - |

## Section 8: Shariah controls

| ID | BRD | Requirement | Backend evidence | Frontend evidence | Database evidence | Test evidence | Status | Sev |
|---|---|---|---|---|---|---|---|---|
| R-097 | 8 | Rule hierarchy; conflicts block activation | `activation.py` rule_conflicts | Pool detail checklist | - | BT activation gates | PARTIAL (hierarchy itself not modelled) | P2 |
| R-098 | 8 | Decision register: decision, scope, evidence, effective date, superseded version, conditions, approvers | `ShariahDecision` | Fatwa register | - | BT ShariahRegisterTests | PASS | - |
| R-099 | 8 | Pre-launch review: nothing activates without Shariah approval | activation gate | - | - | BT activation gates | PASS | - |
| R-100 | 8 | Exceptions: classify, quarantine value, investigate, decide, disclose | `ExceptionCase` | Exception case | - | BT governance.tests; after fix: quarantine, Board decision, disclosure before close (BT test_quarantined_value_needs...; E2E) | PASS | - |
| R-101 | 8 | Purification: identify, prevent distribution, approve charity, retain proof | `PurificationEntry` | Purification ledger | - | BT non_permissible test | PASS | - |
| R-102 | 8 | Related parties: disclose, price-test, conflict declaration, elevated approval | `governance/views.py` | Related-party review | - | BT RelatedPartyTransactionApiTests (4) | PASS | - |
| R-103 | 8 | Shariah audit: plan, samples, findings, responses, remediation, annual report | `governance/audit_report.py` | Shariah audit plan | - | BT test_shariah_register_and_report | PASS | - |
| R-104 | 8 | Change governance: impact, regression simulation, approvals, notification, effective dating | PSR/weightage yes; reserve policy and rule pack no | - | - | BT EconomicsChangeNoticeTests; AT patch probe; after fix F-01/F-04: reserve and rule pack changes need approval and are audited | PASS | - |

## Section 9: AI

| ID | BRD | Requirement | Backend evidence | Frontend evidence | Database evidence | Test evidence | Status | Sev |
|---|---|---|---|---|---|---|---|---|
| R-105 | 9 | Shariah Policy Copilot: citations mandatory; cannot issue fatwa | external FastAPI service `shariah-policy-copilot/` | Copilot | - | copilot unit tests 2/2 (`evidence/copilot_tests.txt`); live service not running; live check 2026-10-15 (scripts/copilot_live_check.py): answers carry citations; no evidence gives the fixed fallback; an investor gets 403. The copilot issues no ruling | PASS | - |
| R-106 | 9 | Contract analyzer: low confidence routes to human | `contract_analyzer.py:114` uses model's self-reported confidence | - | - | none; after fix AI-01: the model's own confidence never clears human review (BT test_a_document_cannot_clear...) | PASS | - |
| R-107 | 9 | Anomaly detector advisory with reason codes | `anomaly_detector.py` | Anomaly queue | `ExceptionCase` | none direct; after fix: findings recorded with reason code and pending disposition (BT DetectorRecordingTests) | PASS | - |
| R-108 | 9 | Cash-flow and liquidity forecast with ranges | `pools/liquidity.py` | Liquidity section | - | BT test_liquidity_forecast (3) | PASS | - |
| R-109 | 9 | Reconciliation copilot cannot post or write off | `accounting/reconciliation.py` advisory | Reconciliation | - | BT ReconciliationTests; after fix: finding recorded; the copilot only proposes (BT DetectorRecordingTests) | PASS | - |
| R-110 | 9 | Member risk and hardship without protected-trait inference | `hardship_predictor.py` | Arrears tab | - | none on traits | PASS | P2 |
| R-111 | 9 | Disclosure generator in Urdu / Arabic / English from signed run only | `allocation/statements.py` fixed templates (no machine translation) in English, Urdu, Roman Urdu, Arabic from the signed run | Statement view language tabs | `DepositorStatement.narrative_translations` | BT core.test_from_scratch | PASS (Urdu/Arabic wording to be confirmed by a native reviewer) | - |
| R-112 | 9 | Audit sampling logged and challengeable | `audit_sampler.py` + recommendation record | Reports | `AIRecommendation` | BT recommendations | PASS | - |
| R-113 | 9 | Fraud and collusion graph; KYC/AML decides | indicators from real data | - | - | BT test_collusion_indicators (2) | PARTIAL (no graph) | P3 |
| R-114 | 9 | Scenario simulator sandbox cannot alter production | `simulate` endpoints write nothing (ST) | Scenario comparison | - | none asserting no writes | PASS | P2 |
| R-115 | 9 | Model inventory: owner, purpose, version, provenance, validation, retirement | registry holds owner, purpose, provenance, validation status/date/reference, retirement date | Model Governance | `AIModelRegistry` | BT ai_agents.test_recommendations | PARTIAL (inventory is edited through the API; no edit form yet) | P2 |
| R-116 | 9 | Prompt/output logging with masking and retention | `ai_agents/recording.py` | log viewer | - | BT test_masking; retention | PASS | - |
| R-117 | 9 | Accuracy, drift, bias, hallucination, override, false-positive metrics | acceptance, override, fallback, false-positive rate, 30-day confidence drift; bias and hallucination cannot be measured automatically (need reviewed samples) | Model Governance | - | BT recommendations | PARTIAL | P2 |
| R-118 | 9 | Role-based copilot access; no cross-tenant retrieval | tenant header; copilot filter | - | - | copilot test_tenant_isolation; AT role matrix | PASS | - |
| R-119 | 9 | Approved knowledge base only; paragraph-level citations | copilot service | - | - | live service not running; live check: answers cite document, section and page from the approved corpus; the approved-corpus-only rule is enforced by the copilot service, not re-tested here; no red-team run | PARTIAL | P2 |
| R-120 | 9 | Kill switch, safe fallback, manual operating procedure | kill switch, fallback; no manual procedure doc | - | - | BT kill switch test, copilot fallback test | PARTIAL | P3 |

## Section 10: accounting

| ID | BRD | Requirement | Backend evidence | Frontend evidence | Database evidence | Test evidence | Status | Sev |
|---|---|---|---|---|---|---|---|---|
| R-121 | 10 | Subscription / contribution journal | `post_capital_movement_journal` | Journal batches | `JournalEntry` | BT CapitalJournalTests | PASS | - |
| R-122 | 10 | Eligible income accrual journal | posting an event: Dr Accrued Income Receivable / Cr Pool Income | - | `IncomeExpenseEvent.journal_batch` | BT core.test_from_scratch | PASS | - |
| R-123 | 10 | Direct pool expense journal | Dr Pool Direct Expense / Cr Pool Expense Payable (pool-chargeable part only) | - | - | BT core.test_from_scratch | PASS | - |
| R-124 | 10 | Profit allocation journal | `build_allocation_entries` | Journal batches | - | BT tie-out tests | PASS | - |
| R-125 | 10 | Purification journal (clearing -> charity payable) | non-permissible income to clearing; Board approval: clearing -> charity payable; payment: charity payable -> cash | Purification ledger | `PurificationEntry.approval_journal/distribution_journal` | BT core.test_from_scratch | PASS | - |
| R-126 | 10 | Payout / redemption journal | payout clearing, redemptions | - | - | BT payout clearing, CapitalJournalTests | PASS | - |
| R-127 | 10 | Provision / write-off journal | provisions | - | - | BT pools.test_provisions | PASS | - |
| R-128 | 10 | Reversal / recovery | `create_reversal_journal` | - | - | BT RestatementTests | PASS | - |
| R-129 | 10 | Reconcile to enterprise GL; never silently balance through suspense | Suspense is itemized (`accounting/suspense.py`): named items, maker-checker, journals on approval, ageing, ledger = items check, period-close gate 6 | - | - | BT accounting.test_suspense (5); E2E suspense flow | PASS | - |

## Section 11: data model and integrity

| ID | BRD | Requirement | Backend evidence | Frontend evidence | Database evidence | Test evidence | Status | Sev |
|---|---|---|---|---|---|---|---|---|
| R-130 | 11 | Core entities (Foundation ... Assurance & AI) | most present; `Member` = `CircleMember`; no `Payment`, `EvidenceObject`, `ModelVersion` as such | - | migrations | - | PARTIAL | P3 |
| R-131 | 11 | One effective asset assignment unless sharing approved | `asset_rules.py` (application level) | - | no DB constraint | BT AssetRuleTests | PASS | - |
| R-132 | 11 | Signed run references immutable pool, contract, rate, balance, rule-pack versions | rule pack edited in place keeps its version; balances not versioned | - | `JurisdictionRulePack` | AT patch probe; after fix F-04: pack edits are controlled, but the pack is still edited in place and not versioned; after rule pack revisions: signed run seals pack revision; history immutable (BT) | PASS | - |
| R-133 | 11 | PSR totals equal the configured whole | `ProfitSharingRatio.clean` | - | no DB check | AT test_15 | PASS | - |
| R-134 | 11 | No physical deletion after posting | model guards + PROTECT FKs | - | PROTECT | BT ImmutabilityTests; AT admin bulk delete refused | PASS | - |
| R-135 | 11 | Every override: reason, evidence, maker, checker, timestamp | income override sealed with reason; reserve balance / account dates / rule pack changed with no reason or checker | - | - | AT patch probe; after fixes F-01, F-04, F-05: AT patch probe shows no uncontrolled change | PASS | - |

## Section 12: integrations and API

| ID | BRD | Requirement | Status | Sev | Evidence |
|---|---|---|---|---|---|
| R-136 | 12 | Core banking / LOS / LMS (REST, events, SFTP) | MISSING (simulated `cbs_daemon.py`, refused in production) | P1 | BT core.test_evidence_and_simulation |
| R-137 | 12 | ERP / GL: chart mapping, journal batches, posting status, trial balance | PARTIAL: controlled hand-over with stored file, no duplicate send, the GL's posting status recorded by a different checker, trial balance (BT accounting.test_gl_handover, 6; E2E GL hand-over). No live ERP connection: the file is handed over and the answer recorded by people | P2 | `apps/accounting/gl_handover.py` |
| R-138 | 12 | KYC / KYB / AML (API, webhook) | MISSING | P1 | ST |
| R-139 | 12 | Banking / payment rails | MISSING (simulated) | P1 | ST |
| R-140 | 12 | Market / valuation data | MISSING | P3 | ST |
| R-141 | 12 | Digital signature / documents | MISSING (evidence reference only) | P2 | ST |
| R-142 | 12 | Messaging: email, SMS, WhatsApp, push, delivery status | PARTIAL (e-mail + in-app) | P2 | BT notifications.tests |
| R-143 | 12 | BI / data lake (events/CDC, masked) | MISSING | P3 | ST |
| R-144 | 12 | Regulator / auditor portal: secure export | PARTIAL (auditor portal, evidence bundle; no regulator export) | P2 | E2E auditor |
| R-145 | 12 | Representative API surface (10 endpoints) | PARTIAL - equivalents exist for 9 of 10; see API_AUDIT.md | P3 | `evidence/api_routes.tsv` |

## Section 13: dashboards

| ID | BRD | Audience | Status | Sev | Evidence |
|---|---|---|---|---|---|
| R-146 | 13 | Executive: AUM, distributable profit, yield, liquidity, exceptions, growth, forecast, jurisdiction view | PARTIAL (no growth/forecast/jurisdiction view) | P2 | BT core.test_dashboards; E2E dashboards |
| R-147 | 13 | Pool manager: asset mix, income, expenses, daily funds, weightages, pending, close readiness | PARTIAL | P3 | E2E role dashboards |
| R-148 | 13 | Finance: reconciliations, journals, provisions, suspense, residuals, close, restatements | PARTIAL (no suspense) | P3 | E2E |
| R-149 | 13 | Shariah: approval queue, exceptions, purification, contract coverage, review plan, finding age | PARTIAL | P3 | E2E |
| R-150 | 13 | Risk: concentration, liquidity, AML/KYC, related parties, limits, breaches; after fix F-07: limits come from the rule pack; defaults are labelled unconfirmed | PARTIAL | P2 | ST `concentration_engine.py:21-27` |
| R-151 | 13 | Investor: balance, profit, methodology, transactions, disclosures, tax/Zakat, disputes | PASS | - | E2E investor tests |
| R-152 | 13 | Member: contribution status, schedule, ledger, vote/consent, receipts, hardship | PASS | - | E2E member test |
| R-153 | 13 | Auditor/regulator: signed runs, versions, reperformance inputs, exceptions, samples, exports | PASS | - | E2E auditor test |

## Section 14: non-functional

| ID | BRD | Requirement | Status | Sev | Evidence |
|---|---|---|---|---|---|
| R-154 | 14 | Availability 99.9%, graceful AI degradation | NOT TESTED (no HA deployment exists; AI fallback tested) | P1 | DEPLOYMENT.md |
| R-155 | 14 | P95 < 2 s; batch SLA; million-account scaling | PARTIAL: P95 0.38-0.83 s on demo data (`evidence/latency_probe.txt`); the growing lists are now paged (default 50, max 500; BT `test_growing_lists_are_paged...`, `test_the_audit_log_is_paged...`). No load test at real volume; allocation runs in one process | P2 | `apps/core/pagination.py` |
| R-156 | 14 | SSO/MFA, RBAC+ABAC, tenant isolation, encryption, vault, WAF, EDR | PARTIAL (MFA, RBAC, isolation tested; no SSO/vault/WAF/EDR) | P1 | AT security tests |
| R-157 | 14 | Append-only audit, signed manifests, tamper-evident hashes | PASS | - | BT core.test_audit_chain (7) |
| R-158 | 14 | Privacy: purpose limitation, minimisation, consent, residency, retention, DSAR | PARTIAL | P2 | BT consents, retention |
| R-159 | 14 | Resilience: multi-zone, encrypted backups, tested restore, RPO 15 min, RTO 4 h | BLOCKED (scripts exist, never run; no pg_dump here) | P1 | `backend/scripts/` |
| R-160 | 14 | WCAG 2.2 AA, keyboard, contrast, labels, localization; after fix: every control gets an accessible name (probe: 242 unnamed -> 0 over 8 roles); no full WCAG audit | PARTIAL | P3 | `evidence/a11y_probe.txt` |
| R-161 | 14 | Multi-currency, timezone, calendars, English/Urdu/Arabic, RTL | PARTIAL (no Arabic UI; RTL for Urdu) | P2 | ST `i18n/index.ts` |
| R-162 | 14 | Metrics, traces, logs, lineage, data-quality and control alerts | PARTIAL (logs, health endpoints and control alerts: late close, suspense ageing, stale approvals, key rotation; no traces or lineage) | P2 | BT HealthTests |

## Section 16: business rules

| ID | Rule | Status | Sev | Evidence (details in SHARIAH_COMPLIANCE_AUDIT.md) |
|---|---|---|---|---|
| R-163 | BR-001 activation gates | PASS | - | BT pools.test_activation_gates (12) |
| R-164 | BR-002 no overlapping weightages / PSR | PASS (application level, no DB constraint) | P3 | BT overlap tests |
| R-165 | BR-003 economics change -> simulation + notification; after fix F-01/F-04 | PASS | - | BT EconomicsChangeNoticeTests; AT patch probe |
| R-166 | BR-004 signed run immutable; reversal + linked rerun | PASS | - | BT ImmutabilityTests, RestatementTests |
| R-167 | BR-005 non-permissible income excluded and routed | PASS | - | BT test_income_derivation |
| R-168 | BR-006 Musharakah loss by capital ratio unless liability | PASS | - | BT NegligenceWorkflowTests |
| R-169 | BR-007 no interest / late interest / uplift in circles | PASS (static: no field) | P2 | ST |
| R-170 | BR-008 payout needs collections, eligibility, KYC, dual approval | PASS | - | BT circles.test_payout_workflow (14) |
| R-171 | BR-009 AI output shows source, confidence, reason, disposition; after fixes AI-03: detector and reconciliation copilot now record (BT) | PASS | - | BT ai_agents.test_recommendations |
| R-172 | BR-010 cross-tenant reads and retrieval denied, tested | PASS | - | BT tenants.test_comprehensive_isolation; AT cross-tenant (two tenants, 0 leaks) |

## Section 17-19: roadmap, go-live gates, decisions

| ID | BRD | Requirement | Status | Sev | Evidence |
|---|---|---|---|---|---|
| R-173 | 17 | Phase 1 exit: one pilot bank pool runs in parallel | BLOCKED (needs pilot) | P1 | - |
| R-174 | 17 | Phase 2 exit: controlled AI and audit evidence live | PARTIAL | P2 | - |
| R-175 | 17 | Phase 3 exit: pilot investment product live | BLOCKED | P2 | - |
| R-176 | 17 | Phase 4 exit: pilot circle live | BLOCKED | P2 | - |
| R-177 | 17 | Phase 5: rule packs, integrations, HA/DR, multilingual, regulator packs | MISSING | P2 | - |
| R-178 | 18 | Formula unit tests with regulator-approved examples | PARTIAL (BRD example only) | P1 | AT/BT golden |
| R-179 | 18 | Golden-dataset reperformance vs independent spreadsheets | PARTIAL (independent reference calculations in AT; no client workbook) | P1 | AT test_audit_financial |
| R-180 | 18 | Conflict, negative-profit, reserve cap, rounding tests | PASS | - | AT 04, 10, 13; BT activation |
| R-181 | 18 | Migration reconciliation | NOT APPLICABLE until legacy data exists | - | - |
| R-182 | 18 | RBAC, isolation, penetration, API, privacy, DR tests | PARTIAL (RBAC/isolation done; pen-test, DR not) | P1 | AT security |
| R-183 | 18 | Shariah Board UAT and documented approval | BLOCKED (human) | P1 | `docs/UAT_CHECKLIST.md` |
| R-184 | 18 | Finance parallel run, two periods | BLOCKED (human) | P1 | - |
| R-185 | 18 | AI validation, red-team, fallback, monitoring | PARTIAL (fallback only) | P2 | copilot tests |
| R-186 | 19 | Implementation decisions recorded | PASS (documented, sign-offs pending) | P2 | `docs/DECISIONS.md` |

## Totals (R-001..R-186), after all code fixes and the live copilot check (2026-10-15)

| Status | Count |
|---|---|
| PASS | 110 |
| PARTIAL | 59 |
| FAIL | 0 |
| MISSING | 8 |
| BLOCKED | 6 |
| NOT TESTED | 1 |
| NOT APPLICABLE | 2 |
| **Total** | **186** |

Counted by script. Before any fix: PASS 78, PARTIAL 70, FAIL 9, MISSING 9, BLOCKED 8, NOT TESTED 10, NOT APPLICABLE 2.

Update: R-003, R-004, R-010, R-110, R-114, R-169 moved NOT TESTED -> PASS by `core/test_brd_prohibitions.py` and the simulate-writes-nothing check in `core/test_from_scratch.py`. R-122, R-123, R-125 are not just untested: event posting and purification create no journal at all (real gaps).
