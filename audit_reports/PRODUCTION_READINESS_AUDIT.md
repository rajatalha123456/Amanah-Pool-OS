# Production Readiness (BRD sections 14 and 18)

Legend: **Inspected** = configuration/code read; **Tested** = behaviour executed; **Measured** = numbers taken; **Unavailable** = no operational evidence exists.

| Area | Evidence type | Finding | Status |
|---|---|---|---|
| Interactive latency (P95 < 2 s) | Measured | 20 calls each to 10 list endpoints on the local dev server with demo data: P95 0.39 s to 0.83 s (`evidence/latency_probe.txt`). Dev server, tiny data set: **not representative of production** | PARTIAL |
| Scale ("million-account horizontal scaling") | Inspected + measured | no pagination on any list endpoint; allocation ~13,000 balance rows/s per process (`docs/DEPLOYMENT.md` 6a); no partitioning or worker queue | NOT READY |
| N+1 queries | Inspected | the engine was fixed earlier (values_list, one account dict); views not profiled | NOT TESTED |
| Background jobs / retries | Inspected | no Celery/Redis; scheduled jobs are management commands run by cron (`send_contribution_reminders`, `apply_retention`); no retry framework | PARTIAL |
| Idempotency | Inspected | state checks and unique constraints; no idempotency keys | PARTIAL |
| Concurrency safety | Inspected | run release locked; distribution release not (F-08) | PARTIAL |
| Exception recovery | Tested | approve rolls back on journal or reserve error (atomic) | PASS |
| Logging and monitoring | Inspected | file logs (`backend/logs/`), `/health/` and `/health/ready/` (BT HealthTests); no metrics, tracing or alerting | PARTIAL |
| Backups / restore | Inspected | `backend/scripts/backup_db.py`, `restore_check.py` exist; never executed (no `pg_dump` on this machine); RPO 15 min needs WAL archiving | Unavailable |
| Availability 99.9% / multi-zone | Unavailable | no deployment manifests, Docker, IaC or HA design in the repo | Unavailable |
| Deployment configuration | Inspected | `config/settings/production.py` (HTTPS, HSTS, MFA on, simulated rails off), `docs/DEPLOYMENT.md`; no Dockerfile, no CI/CD pipeline (`.github` absent) | PARTIAL |
| Secret management | Inspected | environment variables via python-decouple; no vault | PARTIAL |
| Data retention | Tested | retention policies and dry-run command (BT test_retention) | PASS (periods need legal sign-off) |
| Localization | Inspected | English + Urdu with RTL; no Arabic; amounts mostly PKR | PARTIAL |
| Accessibility | Tested (probe) | unlabeled controls on 3 of 8 screens probed (`evidence/a11y_probe.txt`); no WCAG audit | PARTIAL |
| CI/CD testing | Inspected | none; tests run manually | MISSING |
| Static checks | Tested | `tsc` clean (`evidence/tsc.txt`); oxlint 68 warnings, 0 errors (`evidence/lint.txt`); `makemigrations --check` clean | PASS |
| Dependency vulnerabilities | from 2026-10-12 | pip-audit / npm audit clean then; not re-run | NOT TESTED in this audit |

## Section 18 go-live gates
| Gate | Status |
|---|---|
| Formula tests with regulator-approved worked examples | PARTIAL: the BRD example passes; no regulator dataset |
| Golden-dataset reperformance vs independent spreadsheets | PARTIAL: independent Fraction-based references in this audit; client workbook needed |
| Conflict, negative-profit, reserve-cap, rounding tests | PASS |
| Migration reconciliation | NOT APPLICABLE until legacy data |
| RBAC, isolation, penetration, API, privacy, DR | PARTIAL: RBAC and isolation done; pen-test and DR not |
| Shariah Board UAT | BLOCKED (people) |
| Finance parallel run, two periods | BLOCKED (people) |
| AI validation, red-team, fallback, monitoring | PARTIAL: fallback only |

## Readiness statement
Availability, million-account scaling, RPO and RTO **cannot be claimed**: there is no measured evidence. The P0 and P1 findings in
`MASTER_AUDIT_REPORT.md` must be fixed before even a pilot handles real customer money.
