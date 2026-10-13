# Accounting, Journals and GL Export (BRD section 10)

## Structure
- `accounting/models.py`: `JournalBatch` (links to `allocation_run` or `investment_run`, `reverses_batch`, pool, date, totals, status `posted` only) and `JournalEntry` (account name, logical key, GL code, debit/credit, amount).
- `accounting/services.py`: builders for allocation, distribution, capital movements, adjustments and reversals. `_post_batch` (128-160) refuses an unbalanced batch and writes batch + entries in one transaction.
- `accounting/chart.py` + `AccountMapping` (maker-checker through `ConfigChangeRequest`): logical account -> enterprise GL code; each entry stores both.
- GL export: `GET /api/v1/accounting/gl-export/?pool=&date_from=&date_to=` (`accounting/views.py:290-315`, `exports.py`), CSV, finance maker/checker only, audit-logged.

## Checks
| Check | Evidence | Result |
|---|---|---|
| Double entry, balanced totals | `_post_batch` refuses imbalance; `JournalBatch.clean` | BT tie-out tests, ImmutabilityTests | PASS |
| Correct account mapping | mapping resolved pool override -> tenant default; GL code stored on entry | BT ChartMappingTests `test_mapped_accounts_carry_gl_code_and_name` | PASS |
| Participant capital accounts | subscription/redemption journals | BT CapitalJournalTests | PASS |
| Income accruals | events posted; no accrued-income-receivable journal distinct from realization | none | NOT TESTED / PARTIAL |
| Direct expenses | events -> run figures | BT income derivation | PASS (journal not separately asserted) |
| Profit allocation entries | `build_allocation_entries` (distributable -> reserves, Mudarib payable, participant payables, rounding) | BT `verify_run_ties_out` tests | PASS |
| Mudarib share payable | same builder | BT tie-out | PASS |
| Purification entries | purification entry + approval; journal to charity payable not asserted by a test | none | NOT TESTED |
| Payout and redemption | payout clearing contra journal; redemption journal | BT payout clearing (12), CapitalJournalTests | PASS |
| Provisions and write-offs | `pools/provisions.py` -> `post_adjustment_journal` | BT pools.test_provisions (7) | PASS |
| Reversals and recoveries | `create_reversal_journal`; restatement reverses original batch and reserves | BT `test_approving_rerun_reverses_original_journal_and_reserves` | PASS |
| Closed-period protection | period lock on imports, events, runs; restatement allowed after lock | BT PeriodLockTests | PASS |
| Suspense handling | none: there is no suspense account and no suspense ageing. Reconciliation differences become exceptions instead | BT ReconciliationTests | PARTIAL (BRD 4 / 13 list suspense explicitly) |
| Journal approval workflow | journals are created only by an approved release (run, distribution, provision, payout); no free-form journal entry endpoint exists | role matrix (no journal POST) | PASS |
| Journals before approvals | `create_journal_from_allocation` is called only inside `approve` after all stages (`allocation/views.py:679`) | static + BT ceremony | PASS for bank pools; investment distributions post on one checker's approval (F-06) |
| Partial commit on failure | approve wraps reserve movements, status, event consumption and journal in one `transaction.atomic()`; errors roll back (`allocation/views.py:641-684`) | static; BT reserve-cap error test | PASS (static + test) |
| Traceability run -> pool -> period -> config | batch -> run (one-to-one, PROTECT) -> `config_snapshot` + hash | DB FKs | PASS, but rule pack content is not snapshotted (F-04 / FIN-05) |
| GL export generation | CSV per pool and date range | not covered by a backend test (no `gl_export` test in the index) | NOT TESTED |
| Export status and reconciliation | none: no export record, no posting status from the GL, no trial balance | static | MISSING (BRD 12 "posting status, trial balance") |
| Duplicate export prevention | none: the same range can be exported repeatedly with no marker | static | MISSING |
| Physical deletion | `JournalBatch.delete` / `JournalEntry.delete` raise; entries PROTECT; Django admin bulk delete of a signed run was refused (protected FK) | AT `evidence/admin_bulk_delete.txt` | PASS |
| Cascade risk | `JournalBatch.pool` is `on_delete=CASCADE` (`accounting/models.py:42`). Deleting a pool would cascade to journals at the queryset level. Pools with accounts are protected by other PROTECT FKs | static | P3 |

## Findings
- **ACC-01 (P2):** No suspense account or suspense ageing, although BRD 4 and 13 require them. Differences are raised as exceptions only.
- **ACC-02 (P2):** GL export has no export log, no status, no duplicate guard and no trial balance, so the enterprise GL cannot confirm what it received.
- **ACC-03 (P2):** Purification and accrual journals have no test.
- **ACC-04 (P1):** The reserve balance can be set through the API without a journal (F-01). The journals then no longer explain the reserve balance the engine uses for caps.
- **ACC-05 (P3):** `JournalBatch.pool` cascades on pool delete. Change it to PROTECT.

Exact account classification and recognition are for the client's accounting policy (BRD 10 note). The auditor did not assess them.
