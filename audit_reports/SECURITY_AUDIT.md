# Security, Tenant Isolation and Role Permissions

Scope: safe tests only, on Django's throw-away test database (audit tests) and read-only GETs against the local demo server.
No destructive testing, no external systems.

## Tenant isolation (BR-010) - two tenants
Audit test `test_audit_security.test_cross_tenant_reads_and_writes_are_denied`: tenant **AUD-A** is fully seeded; tenant **AUD-B** is created with its own
users and pool. Output: `evidence/cross_tenant.txt`.
| Attack | Result |
|---|---|
| Tenant B user sends `X-Tenant-Code: AUD-A` | 403 |
| Tenant B user lists every collection route of its own tenant and searches the responses for tenant A ids (4 pools, 13 participants, 12 accounts, 4 runs, 3 journal batches) | 0 ids found |
| Tenant B user GETs and PATCHes tenant A pools, participants, runs and journal batches by id | no 200/202 |
| Project suite: `tenants.test_comprehensive_isolation` (10 tests over every tenant-scoped model) | pass |
| Copilot service: `test_candidate_documents_are_scoped_to_tenant` | pass |
**Result: PASS.** Known design gap: `LegalEntity` is not a `TenantScopedModel`. Its view filters by tenant (`tenants/views.py:93-99`) and pools refuse a foreign entity (`pools/serializers.py:55-58`). P3.

## Authentication and session
| Check | Result |
|---|---|
| Missing token | 401 |
| Tampered JWT signature | 401 |
| Unknown tenant | 403 |
| Access token lifetime | 20 min (base/production); 24 h in development settings |
| Refresh rotation + blacklist | configured (`SIMPLE_JWT`) |
| MFA | TOTP; enforced by default only in production settings (`MFA_ENFORCED`) |
| Login throttling | `AUTH_THROTTLE_RATE` (default 10/min); no general API throttle (P2) |
| SSO | none (BRD 14 asks for it) - P2 |
| Role change by mass assignment (`PATCH /auth/me/` role, is_superuser) | refused (unchanged) |

## Role permissions
- Full runtime matrix of 11 roles x all collection routes: `evidence/role_matrix.tsv` (see API_AUDIT.md).
- Investor deny-by-default and super-admin allow-list both hold for business data, with one exception:
- **F-03 (P1): Super admin reads tenant financial data through the audit log.** `ADMIN_ALLOWED` includes `core/audit-log/` and its export.
  Audit entries carry amounts, member references and run figures. Verified on the demo server: `evidence/superadmin_audit_log_exposure.txt`.
  BRD 3: "Cannot view tenant financial data by default". Fix: give the super admin a redacted view (actor, action, model, time) or tenant consent before access.
- **Single-person changes to economics** (object-level authorization gap, verified): reserve policy balance and rate by a pool manager (F-01, P0); participant account dates by a pool manager or finance maker (F-05, P1); rule pack tax and cap values by risk or super admin (F-04, P1). See `evidence/patch_probe_changes.txt`. None of these writes an audit-log entry: `ReservePolicyViewSet`, `ParticipantAccountViewSet` and `JurisdictionRulePackViewSet` contain no `perform_update` and no `log_action` (static check).
- Django admin is mounted at `/admin/` (`config/urls.py:9`) with default ModelAdmins for runs, lines, PSR, bands and journals. A Django superuser can open the approved-PSR change form (`evidence/admin_psr_edit.txt`). The seeded admin is not `is_staff`, so the exposure needs a superuser created on the server. A bulk delete of a signed run was refused by protected FKs. P2: disable `/admin/` in production, or make these admins read-only.

## Other checks
| Area | Observation | Result |
|---|---|---|
| IDOR (investor) | other investors' capital accounts via lists and direct ids | none (`evidence/investor_idor.txt`) |
| SQL injection | ORM only; the one raw cursor is the fixed `SELECT 1` readiness check (`core/views.py:32`) | static PASS |
| File uploads | copilot documents go to the external service; no Django file field accepts uploads in business models (static) | NOT TESTED |
| CORS | `CORS_ALLOWED_ORIGINS` required in production (`docs/DEPLOYMENT.md`) | configuration inspected |
| CSRF | API uses Bearer tokens (CSRF n/a); Django admin uses sessions + CSRF | inspected |
| Secrets | `SECRET_KEY` and DB settings from environment (`python-decouple`); `backend/.env` not committed (gitignore) | inspected; no vault (BRD 14) |
| Audit log tampering | hash chain + Merkle verify; `simulate-tamper` is read-only | BT test_audit_chain (7) |
| Dependencies | `pip-audit` / `npm audit` clean on 2026-10-12 (`docs/DEPLOYMENT.md` 6a) | not re-run in this audit |
| Contract analyzer | sends a fixed `X-User-Role: shariah_reviewer` header to the copilot whatever the caller's role (`ai_agents/services/contract_analyzer.py:35-41`) | P2 |
| Public endpoints | `/api/v1/public/` (demo requests) throttled `5/hour` | BT test_demo_requests |

## Not performed
Penetration test, DAST scan, TLS/WAF/EDR review, password-policy review, load-based DoS. These need an external party and a deployed environment.
