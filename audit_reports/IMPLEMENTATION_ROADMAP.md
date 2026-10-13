# Implementation Recovery Roadmap

Estimates are developer-days for one engineer who knows the codebase, shown as ranges. Assumptions: the existing 444-test backend suite and
Playwright suites are kept green; each task ships with its tests; no external vendor integration is included unless stated; review and
deployment time are excluded. Task IDs map to findings in `MASTER_AUDIT_REPORT.md`.

## 0. Immediate critical fixes (do first; about 14-22 days)
| Task | Req / finding | Affected files | Backend | Frontend | Database | Tests required | Depends on | Days | Acceptance criteria |
|---|---|---|---|---|---|---|---|---|---|
| T-01 | F-01, BR-003, BRD 5 reserves | `allocation/views.py` (ReservePolicyViewSet), `allocation/reserves.py`, `governance/config_changes.py` | `current_balance` read-only; changes only through released runs and an approved reserve-movement action; rate/cap changes become `ConfigChangeRequest` (reason, different approver, notice, audit log) | `JurisdictionRulePacks.tsx` reserve form -> proposal flow; pending queue in Governance Config | none (reuse change request) | patch probe returns 4xx or 202 for every role; balance unchanged; audit entry written; approver != proposer | none | 3-4 | `evidence/reserve_policy_change.txt` shows unchanged balance |
| T-02 | F-04, FIN-05, R-132 | `products/views.py`, `products/models.py`, `allocation/config snapshot`, `pools/config_snapshot.py` | rule pack versions (immutable once active), maker-checker, effective date, notice; snapshot rule pack values into run hash | Rule Pack screen: draft/propose/approve states | `JurisdictionRulePack` version fields + migration | patch probe refused for all roles; run hash changes if pack content changes; old run still verifies | T-01 pattern | 5-7 | signed run reperforms with the pack version it used |
| T-03 | F-02 / FIN-01 | `allocation/engine.py:60-67`, `allocation/views.py` create, `pools/daily_close.py` | engine reads `validated` only; run creation requires a signed daily close for each day (or an explicit sealed exception) | message on Allocation page | none | audit test_14 passes; BT for missing close | none | 2 | pending balance receives nothing |
| T-04 | F-05 | `participants/views.py`, `participants/models.py` | opening/closing date locked once balances or runs exist; change by approved request | account form read-only fields | none | patch probe refused | none | 1-2 | `opened_date` unchanged after PATCH |
| T-05 | F-03 | `core/views.py`, `core/audit_serializer`, `accounts/investor_scope.py` | super-admin audit-log view redacts `changes` (amounts, references) | Security & Audit Log tab shows redacted fields | none | admin read returns no amounts | none | 1-2 | `evidence/superadmin_audit_log_exposure.txt` repeats with redaction |
| T-06 | F-06 | `investments/distribution_views.py`, `investments/models.py` | same ceremony as bank pools: check, Shariah review, release by signatory | Distribution tab ceremony | `InvestmentDistributionRun` status values and reviewer fields | BT ceremony for distributions; one person cannot do two stages | none | 3-4 | no single user can release |
| T-07 | F-08 | `investments/distribution_views.py:195-262` | `select_for_update` and re-check inside the transaction | none | none | concurrent-approve test | none | 1 | second approval refused |
| T-08 | F-09, F-11 | `allocation/models.py:230-245`, `allocation/views.py` approve/check | store `shariah_review_required` on the run at creation; add open-serious-exception gate | ceremony shows the gate | field on `AllocationRun` + migration | BT for flipped flag and open exception | none | 2 | flag flip cannot change a run in progress |
| T-09 | F-07 | `pools/concentration_engine.py`, `RiskLimitDashboard.tsx`, rule pack schema | limits read from the rule pack; remove "statutory" and "90 days" claims until confirmed | label "configured limits" | rule pack JSON keys | BT with custom limits | T-02 | 2-3 | no hard-coded percentage remains; **regulatory confirmation obtained** |

## 1. Foundation MVP completion (about 20-25 days)
| Task | Req / finding | Work | Tests | Days |
|---|---|---|---|---|
| T-10 | FIN-02 | weightage > 0 and max-change rule; DB check constraint | audit test_16 passes | 1 |
| T-11 | F-10 | allocation page: pool selector for every role; stop auto-picking by name; E2E independent of seed state | smoke test passes on a clean seed | 1 |
| T-12 | R-155 | pagination on all list endpoints (`PageNumberPagination`), frontend tables | latency probe on 10,000-row data | 3-4 |
| T-13 | R-137 | GL export log: status, hash, duplicate guard, trial balance report | export test | 3 |
| T-14 | ACC-01 | suspense account and ageing; reconciliation differences post to suspense with approval | tie-out tests | 3-4 |
| T-15 | freeze gaps | `assert_not_frozen` on distribution create and balance import | BT | 0.5 |
| T-16 | F-12 | disable `/admin/` in production; read-only admins | settings test | 0.5 |
| T-17 | API | general throttle; idempotency key on money-moving POSTs | BT | 2 |
| T-18 | DB | change 15 financial CASCADE FKs to PROTECT; DB check constraints for PSR total, weightage | migration + tests | 2 |
| T-19 | R-096 | adjustment period for back-dated entries | BT | 3 |
| T-20 | CI | pipeline: backend tests, `tsc`, lint, migrations check, `pip-audit`, `npm audit`, e2e on a clean seed; coverage report | pipeline green | 2-3 |
| T-21 | R-159 | run backup and restore scripts in the target environment; WAL archiving for RPO | restore evidence | 2-3 (infra) |

## 2. Governance and AI (about 12-15 days)
| Task | Req | Work | Days |
|---|---|---|---|
| T-22 | AI-03 | anomaly detector and reconciliation copilot write `AIRecommendation` | 2 |
| T-23 | AI-01, AI-02 | analyzer: always human review for Shariah extraction; pass caller role; sanitize contract text | 1-2 |
| T-24 | AI-04 | red-team and hallucination suite against the running copilot; drift/bias metrics | 4-5 |
| T-25 | R-100 | exception value quarantine and disclosure step; SLA | 3 |
| T-26 | R-049 | AI configuration check on the pool wizard | 2 |
| T-27 | BR-007 | test that no circle endpoint accepts rate, late charge or time uplift | 0.5 |

## 3. Investment pools (about 8-10 days)
| Task | Req | Work | Days |
|---|---|---|---|
| T-28 | R-067 | e-signature integration (vendor needed) | 5-8 |
| T-29 | R-027 | asset transfer valuation and approval; ring-fencing | 3 |
| T-30 | R-122, 125 | tests for accrual and purification journals | 1-2 |

## 4. Community circles (about 8-10 days)
| Task | Req | Work | Days |
|---|---|---|---|
| T-31 | SCR-C4 | draw console uses the two-step commit then reveal; publish the commitment first; remove invented default reason | 1-2 |
| T-32 | R-074 | Wakalah circle model | 3-4 |
| T-33 | R-076 | payment mandates and guarantees | 4-6 |
| T-34 | R-080 | journal surplus/shortfall settlement | 2 |

## 5. Multi-jurisdiction and production scale (weeks, depends on the bank)
| Task | Req | Work | Estimate |
|---|---|---|---|
| T-35 | R-136..139 | core banking, KYC/AML, payment rails: adapters against the bank's specifications | 20+ days each |
| T-36 | R-154, 155 | HA deployment, worker queue, partitioned allocation runs, load test at real volume | 15-25 days |
| T-37 | R-156 | SSO, secrets vault, WAF/EDR | 8-12 days (infra) |
| T-38 | R-160, 161 | WCAG 2.2 AA pass, Arabic UI, RTL review | 8-10 days |
| T-39 | R-162 | metrics, traces, alerts, job lineage | 5-8 days |
| T-40 | R-183, 184 | Shariah UAT and two-period parallel run (people, not code) | calendar time |

## Order and gates
1. T-01..T-09, then re-run the audit tests (`audit_tests/`), which should all pass.
2. Human gates in parallel: tax, Zakat, retention sign-off; Shariah Board configuration approval; regulatory confirmation for T-09.
3. T-10..T-21, external penetration test, backup/restore evidence.
4. Pilot (manual settlement, no live integrations), Shariah UAT, parallel run.
5. Integrations and scale (section 5) after the pilot confirms the model.

Estimated total for sections 0-4: about 62-82 developer-days. Section 5 depends on external specifications and infrastructure.
