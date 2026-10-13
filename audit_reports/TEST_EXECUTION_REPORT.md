# Test Execution Report (2026-10-13)

## Tests discovered
| Suite | Location | Count |
|---|---|---|
| Backend (Django test runner) | `backend/apps/*/test*.py` | 444 |
| Browser smoke | `frontend/e2e/smoke.spec.ts` | 30 |
| Browser role sweep | `frontend/e2e/role-sweep.spec.ts` (`npm run e2e:roles`) | 13 |
| Screenshot helper | `frontend/e2e/shots.spec.ts` | not a test of behaviour; not run |
| Copilot service | `shariah-policy-copilot/backend/tests` | 2 |
| Audit tests (new, this audit) | `audit_reports/audit_tests/` | 5 files, 42 executions |

## Executed
| Suite | Command | Passed | Failed | Skipped | Output |
|---|---|---|---|---|---|
| Backend | `cd backend && python manage.py test apps --noinput -v 2` | 444 | 0 | 0 | `evidence/evidence_backend_tests.txt` (156 s) |
| Smoke E2E | `cd frontend && npx playwright test e2e/smoke.spec.ts` (backend with `AUTH_THROTTLE_RATE=1000/min`, `npm run dev`) | 29 | **1** | 0 | `evidence/evidence_e2e_smoke.txt` |
| Role sweep | `npm run e2e:roles` | 13 | 0 | 0 | `evidence/evidence_e2e_roles.txt` (7.5 min) |
| Copilot | `venv/Scripts/python.exe ../../audit_reports/scripts/run_copilot_tests.py` (pytest not installed) | 2 | 0 | 0 | `evidence/copilot_tests.txt` |
| TypeScript | `npx tsc -b --noEmit` | clean | - | - | `evidence/tsc.txt` |
| Lint | `npx oxlint src` | 0 errors | 68 warnings | - | `evidence/lint.txt` |
| Migrations | `python manage.py makemigrations --check --dry-run` | no changes | - | - | `evidence/makemigrations_check.txt` |
| Audit: financial | `PYTHONPATH=../audit_reports python manage.py test audit_tests.test_audit_financial` | 27 | **4** | 0 | `evidence/audit_financial_tests.txt` |
| Audit: security | `... audit_tests.test_audit_security` | 6 | 0 (after the review allow-list, see below) | 0 | `evidence/audit_security_tests.txt` |
| Audit: integrity | `... audit_tests.test_audit_integrity` | 1 | **2** | 0 | `evidence/audit_integrity_tests.txt` |
| Audit: patch probe | `... audit_tests.test_audit_patch_probe` | 0 | **1** | 0 | `evidence/audit_patch_probe_run.txt` |
| Audit: delete probe | `... audit_tests.test_audit_delete_probe` | 1 | 0 | 0 | `evidence/audit_delete_probe_run.txt` |
| Accessibility probe | temporary copy of `scripts/a11y_probe.spec.ts` in `frontend/e2e`, removed after the run | 1 | 0 | 0 | `evidence/a11y_probe.txt` |

## Failures and what they mean
| Test | Failure trace (short) | Meaning |
|---|---|---|
| smoke `allocation ceremony: a pending run waits for the independent checker` | `expect(locator('tbody tr').first()).toBeVisible()` failed; screenshot shows "No allocation runs for this pool yet" | Product defect F-10: read-only roles cannot pick the pool. A pool created by an earlier E2E run was auto-selected. Also shows the E2E suite depends on database state |
| audit financial `test_14` (x2) | `'AUD-2' unexpectedly found in {'AUD-1': 500.00, 'AUD-2': 500.00}` | Defect FIN-01: pending balances are allocated |
| audit financial `test_16` (x2) | `True is not false : a negative weightage was accepted` | Defect FIN-02 |
| audit security `test_role_matrix_and_scopes` (first run) | 15 read-only-role POSTs passed the permission check | Reviewed one by one (API_AUDIT.md): all are permitted analysis, evidence or administration actions. **Not a defect.** The 15 pairs were then added to the test's `REVIEWED` list and the test re-run: 6/6 pass. The first failing run is not hidden: it is what produced `evidence/role_matrix_violations.txt` |
| audit integrity `test_reserve_policy_change_needs_an_independent_approval` | balance 871,335.74 -> 1.00, HTTP 200 | Defect F-01 (P0) |
| audit integrity `test_approved_psr_cannot_be_edited_through_django_admin` | change form rendered with input | Finding F-12 (P2; needs a Django superuser) |
| audit patch probe | 5 persisted changes (reserve balance, account opening date x2 roles, rule pack version and config x2 roles) | Defects F-01, F-04, F-05 |

## Coverage
**Not measured.** `coverage.py` is not installed in the backend environment, and installing a dependency needs approval under the audit rules. Run to measure:
`pip install coverage && coverage run manage.py test apps && coverage report`. The frontend has no unit-test framework, only Playwright.

## Not executed (blocked)
- Copilot runtime / prompt-injection tests: the service is not running (needs an LLM key or model and an ingested corpus).
- Backup and restore scripts: no PostgreSQL client tools on this machine.
- Load test at production volume: needs an isolated environment and authorization.
- Penetration test: external party.
