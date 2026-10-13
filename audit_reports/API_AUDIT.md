# API Audit

## Surface discovered
- 300 URL patterns under `/api/v1/` (Django URL resolver dump: `evidence/api_routes.tsv`, script `scripts/list_routes.py`).
- DRF viewsets declare `permission_classes = [IsAuthenticated]` at class level. Role rules live in each `get_permissions()`
  (`HasAnyRole`, `IsFinanceChecker`, ...). On top of that, `accounts/authentication.py` applies two allow-lists before any view runs:
  investors and members (`ALLOWED`) and the platform super admin (`ADMIN_ALLOWED`) in `accounts/investor_scope.py`.
- Tenant resolution comes from the `X-Tenant-Code` header (`core/middleware.py`), checked against the user's tenant.
- No list endpoint is paginated (`REST_FRAMEWORK` has no `DEFAULT_PAGINATION_CLASS`, and no view sets `pagination_class`).
- No idempotency keys exist. Duplicate submissions are prevented per object state (status checks, unique constraints) rather than per request.

## Runtime role matrix (audit test `test_audit_security.test_role_matrix_and_scopes`)
Every parameter-free route was called with GET by 11 roles (1,287 calls). Read-only roles (auditor, investor, super admin) also sent `POST {}`
to every collection route. Full table: `evidence/role_matrix.tsv`.

| Role | GET 200 | GET 403 | Other |
|---|---|---|---|
| platform_super_admin | 14 | 97 | 6x405 |
| investor_member | 16 | 95 | 3x400, 2x405 |
| auditor | 87 | 13 | 10x400 (missing query params), 6x405 |
| risk_compliance | 87 | 11 | 1x503 copilot |
| pool_manager | 81 | 19 | |
| finance_maker / checker | 76 / 76 | 26 / 22 | |
| shariah_board / secretariat | 74 / 70 | 24 / 30 | 1x503 copilot each |
| product_manager / authorized_signatory | 62 / 62 | 43 / 46 | |

- **No 500 error** on any route for any role. The only 5xx is `ai/shariah-copilot/documents/` (503), because the copilot service is down; that is the intended degradation.
- **Investor**: 16 readable routes, all on the allow-list. Probes of other investors' capital accounts (lists and direct ids) leaked nothing (`evidence/investor_idor.txt`).
- **Super admin**: 14 readable routes. Pools, participants, runs, journals and circle members are refused. **Exception: `core/audit-log/` returns the financial content of audit entries** (F-03).
- **Read-only roles, POST that passed the permission check** (`evidence/role_matrix_violations.txt`). All 15 were reviewed:
  - Auditor: sampling, collusion detection, Merkle verify, tamper simulation (read-only, confirmed in `core/merkle_engine.py:169`), evidence bundle, Shariah audit findings, support requests, mark-own-notifications-read. None posts a financial record. Creating Shariah audit findings is an audit activity. Accepted.
  - Super admin: tenants, legal entities, rule packs (by design). However the rule pack itself can be changed in place (F-04).

## In-place change probe (audit test `test_audit_patch_probe`)
Each update endpoint was sent one PATCH on a field with economic or legal effect, against a record that is approved, posted or active. All 10 staff roles tried.
Results: `evidence/patch_probe.tsv`, changes `evidence/patch_probe_changes.txt`.

| Endpoint | Field | Persisted change by | Verdict |
|---|---|---|---|
| `allocation/reserve-policies/{id}/` | `current_balance` 871,335.74 -> 1.00 | pool_manager (HTTP 200) | **FAIL P0** (F-01) |
| `participants/accounts/{id}/` | `opened_date` 2026-01-01 -> 2020-01-01 | pool_manager, finance_maker | **FAIL P1** (F-05) |
| `products/jurisdiction-rule-packs/{id}/` | `version`, `rules_config` (WHT 15/30 -> 0, Mudarib cap) | platform_super_admin, risk_compliance | **FAIL P1** (F-04) |
| `allocation/psr-schedules/{id}/` approved | `mudarib_share` | nobody | PASS |
| `allocation/weightage-bands/{id}/` approved | `weightage` | nobody | PASS |
| `investments/capital-accounts/{id}/` | `units_held` | nobody | PASS |
| `pools/assets/{id}/` | `face_value` | nobody | PASS |
| `pools/asset-assignments/{id}/` | `assigned_date` | nobody | PASS |
| `accounting/income-expense-events/{id}/` posted | `amount` | nobody | PASS |
| `circles/circle-members/{id}/` drawn | `payout_position` | nobody | PASS |
| `products/products/{id}/` approved | `minimum_subscription` | nobody | PASS |
| `products/contract-templates/{id}/` approved | `version` | nobody | PASS |
| `products/shariah-decisions/{id}/` approved | `title` | nobody | PASS |
| `governance/related-party-transactions/{id}/` approved | `amount` | nobody (403/400) | PASS |
| `pools/pools/{id}/` open | `effective_date` | nobody | PASS |

## Authentication (audit test `test_authentication_failures`, `test_mass_assignment_role_escalation`)
- No token -> 401; tampered signature -> 401; unknown tenant code -> 403; a tenant B user presenting tenant A's code -> 403. All PASS.
- `PATCH /auth/me/ {"role": "authorized_signatory", "is_superuser": true}` does not change the role. PASS.
- Access token lifetime is 20 minutes in base and production settings and 24 hours in development (`config/settings/development.py:18`). Refresh tokens rotate and are blacklisted.
- Throttling covers only login/MFA/refresh (`AUTH_THROTTLE_RATE`) and the public form. No general API rate limit exists. P2.

## Business endpoints that need attention (static reading, file:line)
| Area | Observation | Priority |
|---|---|---|
| Investment distribution approve, `investments/distribution_views.py:195-262` | Status is checked outside the transaction and there is no `select_for_update`, so two concurrent approvals can both pass and post twice. The bank-pool approve locks the row (`allocation/views.py:643-645`). | P1 (F-08, plausible, not reproduced) |
| Investment distribution create, `distribution_views.py:155-178` | No `assert_not_frozen`: a frozen pool can still prepare and sign distributions. Allocation, payouts, contributions, subscriptions and redemptions are guarded. | P2 |
| Balance import | No freeze check (`grep assert_not_frozen`). | P2 |
| Reserve policy viewset, `allocation/views.py:1019-1032` | Pool manager alone may create or update; no audit log entry; the balance field is writable. | P0 |
| Draw endpoint, `circles/views.py:681-720` | Single-step commit+execute; the operator supplies the client seed. Re-draws are refused. | P2 |
| GL export, `accounting/views.py:290-315` | CSV only; no export record, status, or duplicate-export guard; no trial balance. | P2 |
| Contract analyzer, `ai_agents/services/contract_analyzer.py:30-44` | Untrusted contract text is concatenated into the LLM prompt and sent with the fixed role header `shariah_reviewer`, whatever the caller's role. | P2 |

## BRD section 12 representative API vs actual
| BRD | Actual equivalent | Status |
|---|---|---|
| POST /v1/pools | `POST /api/v1/pools/pools/` | present (E2E wizard) |
| POST /v1/pools/{id}/versions | versions are sealed by the system (`pools/{id}/versions` GET; `config_snapshot.py`) | different by design: no client-created version |
| POST /v1/pools/{id}/assets:assign | `POST /api/v1/pools/asset-assignments/` | present (BT AssetRuleTests) |
| POST /v1/imports/daily-balances | `POST /api/v1/pools/balance-imports/` | present (BT BalanceImportTests) |
| POST /v1/allocation-runs:simulate / :execute | `POST allocation-runs/simulate/`, `POST allocation-runs/` | present |
| POST /v1/allocation-runs/{id}:approve | `check/`, `shariah-sign-off/`, `approve/` | present (4-stage) |
| POST /v1/community-circles/{id}/contributions | `POST /api/v1/circles/contributions/` | present |
| POST /v1/community-circles/{id}/payouts:release | `circles/payouts/` request/approve/settle | present (BT payout workflow) |
| POST /v1/shariah-exceptions | `POST /api/v1/governance/exceptions/` | present |
| GET /v1/statements/{participantId} | `my-statements/` (self) and `statements/{id}` | present |
| GET /v1/audit/evidence-bundles/{period} | `POST core/evidence-bundle/compile/` + download | present (different verb) |

## Not done in this phase (and why)
- Per-endpoint request-schema fuzzing and response-schema validation were not done. There is no OpenAPI schema in the project to validate against.
- Concurrency was assessed by reading the code; no parallel-request test was run.
