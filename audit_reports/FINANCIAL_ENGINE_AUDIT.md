# Financial Engine Audit

## Where the calculation lives
| Engine | File | Used for |
|---|---|---|
| Bank-pool allocation | `backend/apps/allocation/engine.py` `calculate_allocation` (152-427) | Mudarabah / Wakalah deposit pools |
| Income derivation | `backend/apps/allocation/income.py` `resolve_income` | gross income and direct expenses from posted events |
| Reserves | `engine.py` `_reserve_amount`, `reserve_headroom`; `allocation/reserves.py` | PER / IRR |
| Investment distribution | `backend/apps/investments/distribution.py` `calculate_distribution` | Mudarabah / Musharakah / Wakalah investment pools (time-weighted units) |
| Run seal | `engine.py` `run_hash_payload`, `compute_run_hash` | tamper detection at check and release |

All money arithmetic uses `Decimal`. Rounding is half-up to 2 places at the output stage only. The identity
`distributable = PER + IRR + Mudarib + sum(lines) + residual` is enforced, with a tolerance check (`engine.py:365-378`).

## Formulas as implemented (bank pool)
1. `distributable = gross - direct_expenses` (gross and expenses come from posted events, after purification and overhead exclusions; or a sealed manual override with a reason).
2. Daily balance per account per day: the last known balance is carried forward up to 10 days before the period start. It is zero before `opened_date` and after `closed_date`. Days with balance <= 0 are skipped.
3. `average_funds = sum(balance) / days`; `average_weighted = sum(balance x band weightage of that day) / days`.
4. Wakalah only: `fee = total_avg_funds x fee% x days / 365`; `result = distributable - fee`.
5. Profit: `PER = min(result x PER%, cap headroom)`; `net = result - PER`; `Mudarib = fee + net x mudarib%`; `investor = net x depositor%`; `IRR = min(investor x IRR%, cap headroom)`; `investor -= IRR`; line = `investor x weighted_i / total_weighted`.
6. Loss (`result < 0`): no PER/IRR, Mudarib gets only the Wakalah fee; the loss is spread by **unweighted** average funds.
7. Cap headroom = `cap% x total_avg_funds - current_balance`.

## Independent reference tests (audit test `audit_tests/test_audit_financial.py`)
Expected values are computed in the test with `fractions.Fraction`, not with the engine's helpers. The base class runs once for a Mudarabah contract and once for Wakalah (fee 0), so 31 executions in total. Output: `evidence/audit_financial_tests.txt`.

| # | Scenario | Inputs | Expected (independent) | Actual | Result |
|---|---|---|---|---|---|
| 01 | BRD 7.2 worked example | gross 12,000,000; expenses 1,000,000; A 60M, B 40M, weight 1.0; PSR 100/0; no reserves | A 6,600,000.00; B 4,400,000.00 | same | PASS |
| 02 | PSR 70/30, two classes (1.0, 1.5) | as above, B weight 1.5 | Mudarib 3,300,000.00; A = 7.7M x 60/120; B = 7.7M x 60/120 | same | PASS |
| 03 | Zero income | gross 0 | all lines 0.00, not a loss | same | PASS |
| 04 | Negative result | gross 1,000, expenses 2,000; A 600 (w1), B 400 (w2) | A -600.00, B -400.00 (unweighted); Mudarib 0; no reserves | same | PASS |
| 05 | Zero funds | only balance 0 | refused (ValueError) | refused | PASS |
| 06 | Single participant | 80/20, gross 1,000 | 800.00 / Mudarib 200.00 | same | PASS |
| 07 | Mid-period deposit and withdrawal | 10 days; A 100 all; B opens day 6; C drops to 0 day 6 | 500 / 250 / 250 | same | PASS |
| 09 | Weightage change mid-period | x: w1 days 1-5, w2 days 6-10; y: w1 | x 150/250 of 1,000; y 100/250 | same | PASS |
| 10 | Rounding residual | 3 equal accounts, 100.00 | 33.33 each, residual 0.01 to the rounding account | same | PASS |
| 11 | Very large balances | 123,456,789,012.34 and 987,654,321,098.76; gross 98,765,432,101.23; 65/35 | exact Fraction result rounded | same | PASS |
| 12 | Very small balance | 0.01 vs 999,999.99 | 0.01 (1,000 x 1e-8 rounds to 0.00) | same | PASS |
| 13 | PER cap headroom | PER 10%, cap 1% of 1,000,000 funds, 9,500 held, profit 20,000 | PER 500.00; investor 19,500.00 | same | PASS |
| 14 | **Unvalidated balance** | account B's only balance has status `pending` | B gets nothing | **B received 500.00** | **FAIL** (FIN-01) |
| 15 | PSR must total 100 | 60/30 | refused | refused | PASS |
| 16 | **Negative weightage** | serializer with weightage -1.00 | rejected | **accepted** | **FAIL** (FIN-02) |
| 17 | Wakalah fee | 1% p.a. on 100M for 30 days; gross 500,000 | fee = 100M x 1% x 30/365 = 82,191.78; investor 417,808.22 | same | PASS |

## The 24 scenarios required by the audit brief
| # | Scenario | Evidence | Result |
|---|---|---|---|
| 1 | Zero income | AT 03 | PASS |
| 2 | Negative income | AT 04; BT RestatementTests `test_zero_gross_income_is_honoured...` | PASS |
| 3 | Zero weighted funds | AT 05 | PASS |
| 4 | Single participant | AT 06 | PASS |
| 5 | Multiple participant classes | AT 02; BT test_brd_golden (3 classes) | PASS |
| 6 | Mid-period deposits | AT 07 | PASS |
| 7 | Mid-period withdrawals | AT 07 | PASS |
| 8 | Weightage changes | AT 09 | PASS |
| 9 | Overlapping effective dates | BT overlap tests (serializer level) | PASS (no DB constraint) |
| 10 | Invalid PSR totals | AT 15 | PASS |
| 11 | Reserve cap violations | AT 13; BT test_rule_pack_cap | PASS for the cap. But the reserve balance the cap uses can be overwritten by one person (F-01) |
| 12 | Non-permissible income | BT `test_run_figures_come_from_posted_events_and_exclude_non_permissible_and_overhead` | PASS |
| 13 | Rounding residuals | AT 10 | PASS |
| 14 | Very large balances | AT 11 | PASS |
| 15 | Very small balances | AT 12 | PASS |
| 16 | Backdated transactions | BT PeriodLockTests | PASS (refused; no adjustment period, see R-096) |
| 17 | Duplicate imports | BT `test_duplicate_account_balance_for_a_day_is_skipped`; DB unique (pool, day, account) | PASS for account rows. Class-level rows (account null) have no unique constraint, but class-level imports are rejected (BT `test_unverified_kyc_unknown_and_class_level_records_are_rejected`) |
| 18 | Closed accounting periods | BT `test_balance_import_blocked_in_closed_period` | PASS |
| 19 | Unauthorized overrides | income override needs a reason and is sealed (BT); reserve balance, account dates and rule pack can be changed by one person (AT patch probe) | FAIL |
| 20 | Recalculation of signed runs | BT `test_stored_hash_matches_recomputation`, `test_signed_run_is_immutable_and_tampering_blocks_approval` | PASS |
| 21 | Reversal and linked rerun | BT RestatementTests (5) | PASS |
| 22 | Cross-pool asset or income leakage | engine filters by pool; events consumed once (BT ConsumptionTests); no test with two pools sharing an asset | PARTIAL |
| 23 | Simultaneous approval requests | bank pool: row lock (`allocation/views.py:643-645`); investment distribution: none (`distribution_views.py:195-262`) | FAIL for investment distributions (static, not reproduced) |
| 24 | Concurrent allocation executions | runs are drafts until released; release checks for an existing signed overlap inside the lock | NOT TESTED (no parallel test) |

## Findings
- **FIN-01 (P1): balances that were never validated receive profit.** `engine.py:60-67` reads every balance except `rejected`, including `pending` (flagged) rows. The daily-close gate counts pending rows (`pools/daily_close.py:32`), but run creation does not require a signed daily close for the period. BRD 6.2 says the checker signs the daily close before 6.3. Fix: only `validated` rows feed a run, and run creation requires a signed close for each day of the period.
- **FIN-02 (P2): negative or zero weightage accepted.** `WeightageBandSerializer` and the model have no lower bound. A negative band, once approved by the checker, would give a class a negative share and push profit to others. Fix: weightage > 0 at the serializer and as a DB check constraint, plus the BRD "maximum change" rule.
- **FIN-03 (P1): reserve balance writable.** Covered as F-01. The PER/IRR cap headroom depends on `current_balance`, which a pool manager can set to any value through the API without a journal.
- **FIN-04 (P2): reserve release in a loss period is not modelled.** BRD 7.1 includes "+/- approved reserve movements". The loss path never draws on PER/IRR. Whether and how reserves absorb a loss is a Shariah and policy decision; the engine has no option for it.
- **FIN-05 (P1): run seal does not cover the balance rows or the rule pack content.** The hash covers per-line averages and a snapshot of PSR, bands and reserves (`engine.py:380-414`). It does not cover the underlying `DailyBalance` rows or the jurisdiction rule pack, and the rule pack can be edited in place (F-04). Reperformance from inputs therefore depends on data that can change after signing.

## Ambiguities to confirm with Shariah Board / finance (not decided by this audit)
1. Loss distributed by **unweighted** funds in bank pools (`engine.py:315-326`). BRD 7.1 defines the Musharakah loss basis but not the bank-pool loss basis.
2. The Wakalah fee is still charged in a loss period (`engine.py:303-321`), on an actual/365 basis with no leap-year handling.
3. PER is taken before the PSR split and IRR from the investors' share (`docs/DECISIONS.md` item 3).
4. Missing balances are carried forward up to 10 days (`CARRY_FORWARD_DAYS`).
5. Profit on a day with a negative balance is ignored (`balance <= 0` is skipped), and a negative balance does not create a negative share.
