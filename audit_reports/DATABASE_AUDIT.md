# Database and Data Integrity (BRD section 11)

Inventory produced by `scripts/db_inventory.py` (read-only, `evidence/db_inventory.txt`). Engine: PostgreSQL (`config/settings/base.py`).
`makemigrations --check`: **no pending model changes** (`evidence/makemigrations_check.txt`). Tests ran on a fresh PostgreSQL test database after all migrations applied.

## Inventory
| Item | Value |
|---|---|
| Local models | 70 |
| Tenant-scoped (`TenantScopedModel`, filtered manager) | 63 |
| Tenant FK but not scoped | `ApprovalMatrixRule`, `AuditLog`, `LegalEntity`, `User` (all filtered in their views; `LegalEntity` gap is documented by a project test) |
| Unique / check constraints | 28, of which 1 check constraint (`Contribution.contribution_amount_positive`) |
| Explicit indexes | 2 (plus FK and unique indexes created by Django) |
| Float money fields | none; all amounts `DecimalField` (e.g. 18,2) |

## BRD 11 integrity constraints
| Constraint | Where enforced | Evidence | Result |
|---|---|---|---|
| One effective asset assignment unless sharing approved | application (`pools/asset_rules.py`) | BT AssetRuleTests (4) | PASS (no DB exclusion constraint) |
| Signed runs reference immutable pool, contract, rate, balance, rule-pack versions | `config_snapshot` + `calculation_hash`; rule pack and balances not frozen | AT patch probe | FAIL (F-04, FIN-05) |
| PSR totals equal the configured whole | `ProfitSharingRatio.clean()` on save | AT test_15 | PASS (no DB check constraint; `QuerySet.update` would bypass) |
| Musharakah loss ratios follow capital ratios | `investments/distribution.py` | BT test_musharakah_wakalah | PASS |
| No physical deletion of posted records via normal operations | model `delete()` guards, PROTECT FKs, viewset guards | AT delete probe: 17 delete-enabled endpoints x 10 roles, **nothing deleted** (`evidence/delete_probe.tsv`); AT admin bulk delete refused | PASS |
| Overrides keep reason, evidence, maker, checker, timestamp | income override: reason + seal; reserve / account / rule pack changes: none | AT patch probe | FAIL (F-01, F-04, F-05) |

## Other checks
| Check | Observation | Result |
|---|---|---|
| Foreign-key integrity | 15 financial relations use `on_delete=CASCADE` to `Pool`, `AllocationRun`, `CapitalAccount` or `CircleMember`, e.g. `AllocationRun.pool`, `JournalBatch.pool`, `Contribution.member`, `Payout.member`, `Subscription.capital_account` (`evidence/db_inventory.txt`). API deletes are refused (delete probe) and journals are PROTECT, but a cascade remains one `QuerySet.delete()` or admin action away. | P2: change to PROTECT |
| Effective-dated records | PSR, bands, assignments, decisions; overlap checks in serializers only | P3 (no DB exclusion constraint) |
| Financial precision | Decimal everywhere; engine rounds at output | PASS |
| Transactions | release, payouts, closure, imports wrapped in `transaction.atomic()`; bank-run release locks the row; distribution release does not | P1 (F-08) |
| Historical configuration versions | `PoolVersion` with config hash; rule pack has no versions (edited in place) | FAIL (F-04) |
| Immutable signed records | runs, lines, journals, entries, posted events, determined negligence cases | PASS (BT ImmutabilityTests, EventIntegrityTests) |
| Audit timestamps | `created_at` / `updated_at` on base model; hash-chained `AuditLog` | PASS |
| Soft deletion / reversal policy | reversal journals and restatement; no hard delete via API | PASS |
| Record retention | `RetentionPolicy` (maker-checker), `apply_retention` deletes only read notifications | PASS (legal periods unconfirmed) |
| Duplicate prevention | unique (pool, day, account) balances; unique contribution per member/cycle; unique account numbers per tenant; class-level balance rows have no uniqueness but are rejected at import | PASS |
| Indexing / query performance | only 2 explicit indexes; no pagination on any list endpoint; allocation reads all balance rows of a period (measured ~13,000 rows/s, `docs/DEPLOYMENT.md` 6a) | P1 for scale (R-155) |
| Concurrent updates | row lock on run release; none on distribution release, reserve movements outside release | P1 / P2 |
