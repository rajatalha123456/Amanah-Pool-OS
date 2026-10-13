# End-to-End Workflow Audit

How the workflows were exercised:
1. The seed command (`core/management/commands/seed_project_data.py`) drives the real services through each workflow on synthetic data. The test `core.test_seed` checks the outcome.
2. Backend workflow tests use the API with real JWTs and role users.
3. The audit tests in `audit_tests/` run on a seeded throw-away database.
4. The browser smoke suite runs against the demo server.

No real money, payment provider or external system was involved. Each step lists its evidence; a step with no executed evidence is marked.

## Workflow A - Bank pool
| Step | Evidence | Result |
|---|---|---|
| Create tenant | BT tenants tests; AT creates tenant B | PASS |
| Configure jurisdiction | rule pack bound at activation; BT test_rule_pack_cap | PASS (rule pack mutable in place - F-04) |
| Register Shariah decision | BT ShariahRegisterTests, test_quorum | PASS |
| Approve contract | BT products.tests | PASS |
| Create product | E2E product with asset types and terms | PASS |
| Configure PSR and weightages | BT EconomicsChangeNoticeTests, overlap tests | PASS (negative weightage accepted - FIN-02) |
| Configure accounting mapping | BT config change maker-checker; E2E governance config | PASS |
| Obtain approvals and activate | BT test_activation_gates (12) | PASS |
| Import daily balances | BT BalanceImportTests (4) | PASS |
| Import income and expenses | BT DerivedFromEventsTests | PASS |
| Reconcile | BT ReconciliationTests | PASS (no live feed) |
| Daily close | BT test_daily_close (4); E2E daily close | PASS, **but the next step does not require it** |
| Simulate allocation | BT; AT engine tests | PASS |
| Submit, independent check, Shariah review, release | BT ceremony tests (allocation.tests, access control) | PASS |
| Sign and generate journal batch | BT tie-out tests | PASS |
| Depositor statements | BT StatementTests (5) | PASS |
| Export to GL | `gl-export` CSV exists; no test, no export status | **NOT TESTED** - break point for "GL posting status" (MISSING) |
| Browser: checker finds the pending run | E2E smoke **failed** (wrong default pool, F-10) | FAIL |

## Workflow B - Investment pool
| Step | Evidence | Result |
|---|---|---|
| Investor onboarding | E2E onboarding spec; BT investor profiles | PASS |
| KYC | BT `verify-kyc`, KYC tier tests | PASS (internal record; no KYC provider) |
| Contract signature | evidence reference only, no e-sign | **MISSING** (break point) |
| Disclosure acknowledgement | BT test_disclosures (8) | PASS |
| Subscription and capital account | BT CapitalJournalTests | PASS |
| Asset assignment | BT AssetRuleTests | PASS |
| Valuation / NAV | BT NAV tests | PASS |
| Profit/loss calculation | BT test_distribution (19), test_musharakah_wakalah (23) | PASS |
| Approval | single finance checker; no Shariah stage | **FAIL vs BRD 6.3** (F-06) |
| Statement | BT investor self-service statement test | PASS |
| Redemption | BT test_redemptions (9); E2E request | PASS |

## Workflow C - Community circle
| Step | Evidence | Result |
|---|---|---|
| Create circle, configure model | BT circles; Qard only | PARTIAL (no Wakalah model) |
| Add members | BT member tests | PASS |
| Rules acceptance, contribution schedule | BT test_circle_governance (9) | PASS |
| Record collections | BT contributions (unique per member/cycle, positive amount check constraint) | PASS |
| Reconcile | closure reconciliation | PASS |
| Draw | BT commit-reveal tests; UI console uses single-step draw | PARTIAL |
| Payout eligibility and dual approval | BT test_payout_workflow (14) | PASS |
| Release synthetic payout | BT settle with bank reference; E2E ceremony | PASS |
| Receipts | E2E member receipt | PASS |
| Close circle | BT closure tests | PASS (surplus/shortfall not journalled) |

## Workflow D - Exceptions and corrections
| Step | Evidence | Result |
|---|---|---|
| Detect exception | reconciliation and anomaly create `ExceptionCase` | PASS (BT ReconciliationTests) |
| Quarantine value | not modelled | **MISSING** |
| Investigate, decide treatment | exception case detail, dismiss with reason | PASS (BT governance.tests) |
| Record evidence | notes and evidence fields | PASS |
| Reconcile | period close gate requires no open serious exception | PASS (but allocation release ignores open exceptions - F-11) |
| Signed allocation -> correction request -> approved reversal -> linked rerun -> new approval -> updated statements | BT RestatementTests (5), `test_restatement_rederives_the_period_and_relinks_events` | PASS |

## Summary
- Workflow A: complete up to statements. GL handover has no status (MISSING), and one browser defect blocks a checker on the allocation page.
- Workflow B: works except contract e-signature (MISSING) and the approval chain (no Shariah review).
- Workflow C: works. The Wakalah circle model, payment mandates and guarantees are missing.
- Workflow D: correction loop works. Value quarantine is missing, and exceptions do not stop a release.
