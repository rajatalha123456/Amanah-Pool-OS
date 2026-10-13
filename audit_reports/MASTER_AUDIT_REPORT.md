# Amanah Pool OS - Master Audit Report

Audit date: 2026-10-13. Source of truth: `docs/NovuLabs_Islamic_Pool_Management_Platform_BRD.docx` (the file named in the brief,
"...BRD(2).docx", does not exist; this is the only BRD in the repository). Scope: source code as committed on branch `master`
(HEAD `017bf28`) plus this audit's tests. No application source file was modified. All data used was synthetic.

## 1. Architecture map
```
Browser (React 19 + Vite + TS, role-based nav, i18n en/ur)
   |  HTTPS, Bearer JWT (20 min, refresh rotation), X-Tenant-Code
   v
Django 6 / DRF  (backend/config, 12 apps)
   |-- accounts      users, roles, MFA (TOTP), approval matrix, investor/admin scope allow-lists
   |-- tenants       tenants, legal entities, demo enquiries (public form)
   |-- products      products, contract templates, Shariah decisions + quorum, jurisdiction rule packs
   |-- pools         pools + lifecycle, assets, daily balances, daily/period close, liquidity, concentration
   |-- participants  participants, accounts, consents, tax support
   |-- allocation    engine, PSR, weightages, reserves, runs (4-stage ceremony), statements, payout clearing (simulated)
   |-- investments   capital accounts, NAV, subscriptions, redemptions, distributions, negligence cases
   |-- circles       members, contributions, draw, payouts, closure, reminders, votes
   |-- accounting    journals, chart/account mapping, reconciliation, events, GL CSV
   |-- governance    exceptions, purification, related parties, audit plans, retention, support requests, config changes
   |-- ai_agents     recording, contract analyzer, audit sampler, hardship, collusion
   |-- core          audit log (hash chain), evidence bundle, dashboards, health, simulators (refused in production)
   |-- notifications in-app + e-mail
   v
PostgreSQL (70 models, 63 tenant-scoped)         Shariah Policy Copilot (FastAPI + Chroma + BM25 + LLM)  [separate service, not running]
No Redis, no Celery, no Docker, no CI. Scheduled jobs = management commands run by cron.
```
Component status: backend business logic **functional**; frontend **functional** (13/13 roles load every screen); copilot **unverified at runtime**;
bank / KYC / e-sign / GL integrations **placeholder-only** (simulators refused in production); infrastructure (HA, backups, CI) **absent or unexecuted**.

## 2. Executive summary
**Working** (verified by executed tests): the allocation engine reproduces the BRD example and 25 further independently computed scenarios;
signed runs, journals and posted events are immutable and nothing could be physically deleted through any of 17 delete-enabled endpoints by any of 10 roles;
maker-checker and four-person release hold for bank pools; tenant isolation held with two tenants (0 leaks); investors and the platform super admin are confined to allow-lists;
the correction path (reversal and linked rerun) works; the audit log is hash-chained; the 444-test backend suite and 13-user browser role sweep pass.

**Broken or unsafe** (verified): a single pool manager can overwrite a reserve balance (871,335.74 to 1.00) with HTTP 200 and no log; rule-pack tax and cap values can be changed in place by risk or super admin;
participant account opening dates can be rewritten; balances that were never validated receive profit; negative weightages are accepted; the platform super admin can read financial amounts through the audit log; one smoke test fails.

**Missing**: every external integration (core banking, GL posting status, KYC/AML, payment rails, e-signature, BI), Shariah review for investment-pool distributions, suspense accounting,
value quarantine for exceptions, a Wakalah circle model, Arabic UI, SSO, secrets vault, HA/DR evidence, CI/CD, pagination.

## 3. BRD compliance (186 requirement rows, see `BRD_TRACEABILITY_MATRIX.md`)
| Status | Count |
|---|---|
| PASS | 78 |
| PARTIAL | 70 |
| FAIL | 9 |
| MISSING | 9 |
| BLOCKED | 8 |
| NOT TESTED | 10 |
| NOT APPLICABLE | 2 |

Screens (58, `SCREEN_AUDIT.md`): 21 working and browser-verified, 26 render without errors, 2 partial, 8 with a verified defect, 1 blocked (copilot service not running), 0 missing.
Business rules: BR-001, 002, 004, 005, 006, 008, 010 PASS; BR-003 FAIL; BR-007 NOT TESTED; BR-009 PARTIAL.

## 4. Metrics (transparent denominators; no averaged overall score)
| Metric | Numerator / denominator | Value |
|---|---|---|
| Full BRD implementation coverage (PASS / applicable rows) | 78 / 184 | 42% |
| Implemented in full or in part (PASS + PARTIAL) / applicable | 148 / 184 | 80% |
| Verified pass rate (PASS / rows with an executed test: PASS + PARTIAL + FAIL) | 78 / 157 | 50% |
| Rows not verifiable here (BLOCKED + NOT TESTED) | 18 | 10% of applicable |
| Backend tests | 444 / 444 pass | - |
| Audit tests (42 executions, 5 files) | 35 pass, 7 fail (4 financial, 2 integrity, 1 patch probe that records five persisted changes) | each failure is a defect or finding, see section 5 |
| Browser tests | 42 / 43 pass (29/30 smoke, 13/13 sweep) | - |
| API verification | 300 routes listed; 1,287 role GETs, 3 read-only-role POST sets, 160 PATCH and 170 DELETE attempts executed; request-schema fuzzing not done | partial |
| Backend / frontend line coverage | not measured | `coverage.py` not installed (needs approval) |
| Financial engine | 17 reference scenarios (31 executions): 27 pass, 4 fail (2 defects) | see FINANCIAL_ENGINE_AUDIT.md |
| Shariah controls | 11 of 13 negative questions answered "No/blocked"; 2 gaps (exceptions do not stop release; reserves and rule packs change without effective dating) | see SHARIAH_COMPLIANCE_AUDIT.md |

The percentages are ratios of the counted rows, not a judgement of effort or quality. Rows differ in weight.
Distinguish: **full BRD** 42% PASS; **current delivery phase** (Foundation MVP + Governance + Investment + Circles are all built to some degree; phase 5 scale/integrations not started);
**pilot readiness** and **commercial production readiness** are in section 7.

## 5. Findings

IDs: F-nn from this audit; FIN-nn, ACC-nn, AI-nn are the module reports' sub-findings. Effort is in developer-days, one engineer, and assumes the existing test suite and conventions.

### P0 - Critical
| ID | Finding | BRD | Evidence | Fix | Effort |
|---|---|---|---|---|---|
| **F-01** | Any pool manager can create or change a reserve policy (rate, cap, **current balance**) immediately, alone, with no approval and no audit-log entry. The balance feeds the PER/IRR cap in the next profit run. Verified: balance 871,335.74 -> 1.00, HTTP 200. | 5 (Reserves: approval, release, disclosure), 11 (overrides need reason, maker, checker), BR-003 | `allocation/views.py:1019-1032`; `evidence/reserve_policy_change.txt`, `patch_probe_changes.txt` | Make `current_balance` read-only (changed only by released runs and approved reserve movements). Route rate/cap changes through `ConfigChangeRequest` with a reason, a different approver, notice, and audit log | 3-4 |

### P1 - High
| ID | Finding | BRD | Evidence | Fix | Effort |
|---|---|---|---|---|---|
| F-02 (FIN-01) | Balances with status `pending` (unvalidated) are allocated profit, and run creation does not require a signed daily close | 6.2, 6.3 | `allocation/engine.py:60-67`; AT financial test_14 | Only `validated` rows; require a signed close for each day of the period | 2 |
| F-03 | Platform super admin reads tenant financial figures through the audit log | 3 | `accounts/investor_scope.py` ADMIN_ALLOWED; `evidence/superadmin_audit_log_exposure.txt` | Redact `changes` for this role | 1-2 |
| F-04 | Jurisdiction rule pack (WHT rates, Mudarib cap, PER/IRR ceilings, notice period) is edited in place by super admin or risk, with no approval, versioning, effective date or audit log; signed runs depend on it | 3, 8 change governance, 11, BR-003 | `products/views.py` (JurisdictionRulePackViewSet); `patch_probe_changes.txt` | Version rule packs, maker-checker, effective dating, snapshot into the run hash | 5-7 |
| F-05 | Participant account opening and closing dates can be rewritten by pool manager or finance maker; the engine zeroes balances outside those dates | 11 | `participants/views.py`; patch probe | Lock dates once balances exist; change only via approved request | 1-2 |
| F-06 | Investment-pool distributions are signed by one finance checker: no Shariah review, no authorized signatory | 6.3 | `investments/distribution_views.py:195-262` | Reuse the 4-stage ceremony | 3-4 |
| F-07 | Risk dashboard presents hard-coded percentages as "SBP statutory" limits with a "90 days remediation filing" claim; not configurable or sourced | 5, 13, 20 | `pools/concentration_engine.py:21-27`; `RiskLimitDashboard.tsx:401` | Move limits to the rule pack; label as configured; remove unsourced regulatory claims. **Needs regulatory confirmation** | 2-3 |
| F-08 | Distribution release has no row lock: two concurrent approvals could both pass the status check (not reproduced) | 7, 10 | `investments/distribution_views.py:195-262` vs `allocation/views.py:643-645` | `select_for_update` inside the transaction; add a concurrency test | 1 |
| F-09 | The bank-pool Shariah review stage is an environment flag; flipping it changes the required flow for runs in progress | 6.3, 8 | `config/settings/base.py:204`; `allocation/models.py:230-245` | Store the requirement on the run at creation; remove or restrict the flag | 1 |
| F-11 | Open high/critical Shariah exceptions block daily and period close but not allocation release | 8 (exceptions) | no `ExceptionCase` check in `allocation/views.py`; period close gate `period_close_engine.py:132-139` | Add an exceptions gate at check/release | 1 |
| R-136..R-139 | No live integration to core banking, KYC/AML, payment rails, GL posting status | 12 | simulators only | Needs bank specifications (outside code) | 20+ per integration |
| R-154, R-155, R-159 | No HA, no pagination, backups never run | 14 | `PRODUCTION_READINESS_AUDIT.md` | Pagination 3-4 days; DR needs infrastructure | - |
| R-173, 183, 184 | Pilot, Shariah UAT and two-period parallel run not done | 17, 18 | - | People | - |

### P2 - Medium
F-10 allocation page shows the wrong pool to read-only roles (breaks one browser test; `AllocationSimulator.tsx:52-65`, 1 day) · FIN-02 negative weightage accepted (0.5 day) ·
FIN-04 reserve release in loss periods not modelled (policy decision) · FIN-05 run hash does not cover balance rows or the rule pack (2 days with F-04) ·
F-12 Django admin exposes approved-PSR change forms to a superuser (disable or make read-only, 0.5 day) · general API throttle missing (0.5 day) ·
distribution create and balance import ignore pool freeze (0.5 day) · GL export has no log, status, duplicate guard or trial balance (3 days) · no suspense accounting (3-4 days) ·
purification, accrual journals untested · AI-01 analyzer trusts the model's own confidence · AI-02 fixed role header · AI-03 anomaly detector and reconciliation copilot not recorded (BR-009) ·
no AI red-team, drift or hallucination tests · BR-007 has no negative test · 15 financial relations cascade on delete · asset transfer lacks valuation and approval · no value quarantine for exceptions ·
contract-template mandatory parameters not enforced · Wakalah circle model, guarantees, payment mandates missing · no Arabic UI, SSO or vault · unlabeled form controls ·
seed data certificates claim "Certified conforming to AAOIFI FAS-30 and SBP IBD Circular 03/2012" (`participants/seed_ledger.py:231,242`).

### P3 - Low
"LIVE CONTROLS" badge pulses regardless of state · realistic personal names on demo users · `JournalBatch.pool` cascade · LegalEntity not tenant-scoped (view filters it) ·
no "return" state in Shariah approval · 68 lint warnings (mostly set-state-in-effect).

## 6. Missing BRD features (not implemented)
Integrations: core banking/LOS/LMS, GL posting status and trial balance, KYC/KYB/AML, payment rails, market data, e-signature, BI/CDC, regulator export.
Controls: Shariah stage for investment distributions, suspense account, exception value quarantine, adjustment period for back-dated entries, accrual/posting-calendar policy, rule hierarchy model.
Product: Wakalah circle model, circle guarantees and payment mandates, super admin feature flags and key management, Arabic UI, SSO, secrets vault, WAF/EDR, executive growth/forecast/jurisdiction dashboard.
AI: Contract-analyzer provenance/validation records, drift and bias metrics, Urdu/Arabic disclosure generation, fraud graph.

## 7. Production readiness
**NOT READY** for production, and **not yet a pilot candidate** for real customer money.

Basis: one P0 and eleven P1 findings. The P0 and the eight code-level P1s (F-02 to F-09, F-11) are fixable in roughly 20-30 developer-days
and should be fixed before any pilot. Even then, a pilot needs the human gates (Shariah Board sign-off of configuration, tax/Zakat/retention professional sign-off, UAT, parallel run)
and infrastructure evidence (backup and restore run, HA design, penetration test) that do not exist yet.
After the code fixes and a successful re-audit, the status could move to **PILOT CANDIDATE - subject to specified approvals and gates**, with settlement kept manual and no live integrations.
Nothing in this audit supports a **PRODUCTION CANDIDATE** classification.

## 8. Caveats on this audit
- Static findings are marked "static" in each report and were not reproduced at runtime (F-08, F-09, F-11, AI-01, AI-02, accrual and purification journal gaps).
- The copilot service, backups, load test and penetration test could not be executed. Their rows are BLOCKED, not PASS.
- BRD ambiguities are listed in `FINANCIAL_ENGINE_AUDIT.md` and `SHARIAH_COMPLIANCE_AUDIT.md`; this audit decided none of them.
- The demo database was used for browser tests and latency probes only; the audit tests ran on throw-away test databases. A local demo run may have left an extra draft pool (see F-10).

## 9. Next recommended task
**Close F-01 and F-04 together**: make reserve balances system-controlled and put reserve policy and rule pack changes behind maker-checker with versioning and audit logging.
They are the only verified ways one person can alter signed-run economics without a trace.
Then fix F-02 (validated balances plus signed-close gate), which is a two-day change that removes the largest remaining correctness risk in the engine.

## Report index
`BRD_TRACEABILITY_MATRIX.md` · `SCREEN_AUDIT.md` · `API_AUDIT.md` · `FINANCIAL_ENGINE_AUDIT.md` · `SHARIAH_COMPLIANCE_AUDIT.md` · `ACCOUNTING_AUDIT.md` ·
`SECURITY_AUDIT.md` · `AI_GUARDRAILS_AUDIT.md` · `E2E_WORKFLOW_AUDIT.md` · `DATABASE_AUDIT.md` · `PRODUCTION_READINESS_AUDIT.md` · `TEST_EXECUTION_REPORT.md` · `IMPLEMENTATION_ROADMAP.md`.
Evidence: `evidence/`. Reproducible audit tests: `audit_tests/` (run with `PYTHONPATH=../audit_reports python manage.py test audit_tests` from `backend/`).
