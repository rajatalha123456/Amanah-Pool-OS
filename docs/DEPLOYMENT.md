# Deployment Guide - Amanah Pool OS

This is the checklist to take the system from a developer machine to a controlled environment. It lists what the
code already enforces and what **you** must provide. Items marked **BLOCKER** must be done before real money or real
customer data is handled.

## 1. Components

| Part | Technology | Notes |
|---|---|---|
| API | Django 6 / DRF, `config.settings.production` | Run behind a production WSGI/ASGI server. `gunicorn` (Linux) or `waitress` (Windows) is **not** in `requirements.txt`; add the one you use. |
| Database | PostgreSQL | The only supported engine (tests run on it). |
| Web app | React + Vite, `npm run build` -> `frontend/dist` | Serve as static files behind HTTPS. |
| Shariah Policy Copilot | separate service (`shariah-policy-copilot/`) | Optional. If it is down the copilot says so; no answer is invented. |

## 2. Environment variables (backend)

| Variable | Production value |
|---|---|
| `DJANGO_SETTINGS_MODULE` | `config.settings.production` |
| `SECRET_KEY` | long random value, from a vault; never committed |
| `ALLOWED_HOSTS` | the real host names (required) |
| `CORS_ALLOWED_ORIGINS` | the web app's origin(s) (required) |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT` | production database |
| `MFA_ENFORCED` | `True` (the production default) |
| `ALLOW_SIMULATED_INTEGRATIONS` | `False` (the production default). When `True`, fake Raast/1LINK/CBS results become possible - never enable with real data |
| `PAYOUT_SETTLEMENT_ACCOUNT_BALANCE` | the real settlement-account balance until a live balance feed exists; the liquidity gate **fails** if it is not set |
| `AUTH_THROTTLE_RATE` | e.g. `10/min` (login / MFA / refresh throttle) |
| `EMAIL_BACKEND`, `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_USE_TLS`, `DEFAULT_FROM_EMAIL` | the real mail server; the default backend only prints to the console |
| `SHARIAH_COPILOT_BASE_URL`, `SHARIAH_COPILOT_INTERNAL_KEY` | the copilot service and its shared key |

Frontend build: `VITE_API_BASE_URL` = the public API URL ending in `/api/v1/`.

## 3. First-time setup

1. `pip install -r requirements.txt` (plus your WSGI server).
2. `python manage.py migrate`
3. `python manage.py check --deploy` - must report no issues.
4. Create the first tenant and platform super-admin by your own procedure. **Do not run `seed_project_data` in
   production**: it creates demo users with a published password. The seed command refuses to run outside DEBUG
   unless `--allow-non-debug` is passed; never pass it.
5. Create real users per role, enrol MFA for each, and set the approval matrix, account mapping and jurisdiction rule
   pack (Governance Config). The rule pack must define `wht_filer_pct` and `wht_non_filer_pct`; payout batches are
   refused without them. Zakat is not deducted at source unless the pack sets `zakat_deduction_pct`.
6. `npm ci && npm run build`, publish `frontend/dist`.

## 4. Scheduled jobs

Run daily from cron / Task Scheduler:

```
python manage.py send_contribution_reminders      # gentle reminders to circle members (needs "first due date" on the rules)
python manage.py apply_retention                  # dry run: shows what the approved retention policies would remove
python manage.py apply_retention --apply          # only after the dry run was reviewed; deletes read notifications only
```

## 5. What the code already enforces

- Tenant isolation on every tenant-scoped model (a test fails if a new model is not covered).
- Role checks on every write endpoint; investors/members can call only an explicit allow-list.
- Maker-checker everywhere money or configuration changes; approved records are immutable; no hard deletes.
- Login throttling, refresh-token rotation and blacklist, MFA required in production, HTTPS redirect and HSTS.
- Simulated bank rails refused in production (HTTP 409).

## 6. BLOCKERS before real operation (outside the code)

1. **Real payment rail.** Payouts and profit distributions are recorded by staff with the bank's own reference; there is
   no live Raast / 1LINK / core-banking connection. Decide whether staff keep settling in the bank portal or an
   integration is built.
2. **Tax and Zakat sign-off.** The seed pack shows 15% / 30% withholding only as a demonstration value. A tax adviser
   must confirm the rates and the Shariah board must decide on Zakat deduction.
3. **Security review and penetration test** by an external party; fix findings before go-live.
4. **Backups and recovery.** Daily database backups, a restore test, and agreed RPO/RTO. Nothing in this repo does this.
5. **Secrets vault, WAF, SSO** if your policy requires them (not built in).
6. **Load test.** The allocation engine reads all balances of a period into memory; test with your real account
   volumes before trusting it for very large pools.
7. **Shariah Board UAT and a two-period finance parallel run** against your existing spreadsheets.
8. **Monitoring.** Application logs go to `backend/logs/`; add metrics, alerting and log shipping.

## 6a. Capacity, backups and monitoring (measured / provided)

- **Allocation capacity** (`python manage.py benchmark_allocation --accounts N --days D`, run in a throw-away tenant that is removed afterwards).
  Profiling found that the engine built three model objects per balance row; that was fixed and results are unchanged (golden tests pass).
  Measured on a developer laptop, one process: 500 accounts x 30 days (15,000 rows) 5.7 s before, **1.5 s** after (peak memory 57 MB to 9 MB);
  5,000 accounts x 30 days (150,000 rows) **11 s** (about 13,000 rows/s). The cost is linear, so a million accounts over 30 days is
  roughly 30 to 40 minutes in one process; run it in partitions across workers, and repeat the benchmark with your real volumes and
  database server before relying on it.
- **Backups**: `backend/scripts/backup_db.py` (pg_dump, compressed, with a checksum) and `backend/scripts/restore_check.py` (verifies the checksum, restores
  into a scratch database, compares row counts, drops it). They need the PostgreSQL client tools on the server and were not run on the
  development machine, which has none: run them once in your environment and keep the restore check on a schedule. The RPO target of 15 minutes
  needs continuous WAL archiving on the database service (see `docs/DECISIONS.md`).
- **Monitoring**: `GET /api/v1/health/` (process is up) and `GET /api/v1/health/ready/` (database answers; 503 otherwise) for a load balancer or monitor.
  Application logs are in `backend/logs/`; ship them to your log platform and alert on 5xx rates and failed sign-ins.
- **Dependency audit** (2026-10-12): `pip-audit` and `npm audit` report no known vulnerabilities after upgrading PyJWT to 2.15.0, requests to 2.33.0 and
  the transitive `source-map-js`. Repeat before every release.

## 7. Verification before each release

```
python manage.py makemigrations --check --dry-run
python manage.py test apps --noinput
cd ../frontend && npx tsc -b --noEmit && npm run build
AUTH_THROTTLE_RATE=1000/min python manage.py runserver   # for the browser tests only
npm run e2e                                              # needs the dev server, a seeded dev database
```

## 6b. Upgrading an existing database (2026-10-13 audit fixes)
- Run `python manage.py migrate` (adds the Shariah-review flag on allocation runs, the Shariah and release fields on distribution runs, a positive-weightage constraint and two change-request kinds).
- **Approval matrix**: the rule `distribution_approve` must name the **authorized signatory** (Governance Config, proposed by Risk & Compliance, approved by a different finance checker), because investment distributions are now released by the signatory after an independent check and a Shariah review.
- **Rule packs and reserve policies** can no longer be edited directly; changes are proposals approved under `/governance/config-changes/`. Reserve balances are system-controlled: a migrated pool with an opening reserve balance needs an approved opening journal first (not built).
- **Concentration limits**: set `concentration_limits_pct` (and optionally `concentration_cure_days`) in the rule pack; otherwise the Risk screen shows placeholder defaults and says so.
- **Django admin** is off unless `ENABLE_DJANGO_ADMIN=True` (or DEBUG).
