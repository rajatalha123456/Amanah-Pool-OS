# Audit progress

Audit 2026-10-13. Source of truth: `docs/NovuLabs_Islamic_Pool_Management_Platform_BRD.docx` (the prompt names `..._BRD(2).docx`; that file does not exist). Text extracted to `evidence/BRD_TEXT.md`.
Rules followed: no application source changed; demo database used only for browser tests and latency probes; audit tests run on Django's throw-away test database.

| Phase | Status | Report |
|---|---|---|
| 1 Discovery | done | MASTER_AUDIT_REPORT.md (architecture map) |
| 2 Traceability | done (186 rows) | BRD_TRACEABILITY_MATRIX.md |
| 3 Screens | done (58 screens; browser sweep 13/13) | SCREEN_AUDIT.md |
| 4 API | done, except request-schema fuzzing | API_AUDIT.md |
| 5 Financial engine | done | FINANCIAL_ENGINE_AUDIT.md |
| 6 Shariah | done | SHARIAH_COMPLIANCE_AUDIT.md |
| 7 Accounting | done (GL export, purification and accrual journals NOT TESTED) | ACCOUNTING_AUDIT.md |
| 8 Security | done; pen-test not performed | SECURITY_AUDIT.md |
| 9 AI | partial: copilot runtime and red-team BLOCKED | AI_GUARDRAILS_AUDIT.md |
| 10 E2E workflows | done through seed + tests; GL handover and e-signature are break points | E2E_WORKFLOW_AUDIT.md |
| 11 Database | done | DATABASE_AUDIT.md |
| 12 Production readiness | done; HA, backup, load evidence unavailable | PRODUCTION_READINESS_AUDIT.md |
| 13 Tests | done; coverage not measured | TEST_EXECUTION_REPORT.md |
| 14 Scoring | done | MASTER_AUDIT_REPORT.md |
| 15 Roadmap | done | IMPLEMENTATION_ROADMAP.md |

## Commands executed
See `TEST_EXECUTION_REPORT.md` (suites) and the scripts in `scripts/` (route list, schema inventory, copilot runner, accessibility probe).

## Blockers and how to unblock
- Coverage: `pip install coverage` (needs approval), then `coverage run manage.py test apps`.
- Copilot runtime and prompt-injection tests: configure an LLM provider in `shariah-policy-copilot/backend/.env`, ingest the approved corpus, `uvicorn app.main:app --port 8001`, run the prompts in `AI_GUARDRAILS_AUDIT.md`.
- Backup/restore: install PostgreSQL client tools, run `backend/scripts/backup_db.py` and `restore_check.py`.
- Concurrency (F-08): write a two-thread approval test once T-07 is scheduled.

## Housekeeping
`audit_reports/` is untracked. The demo database now contains extra rows created by the browser suites (for example a draft pool from the wizard test); re-seed for a clean E2E run.
