# AI services: kill switch, fallback and manual operating procedure

BRD Section 9 asks for a kill switch, a safe fallback and a manual operating procedure for each AI service. AI in Amanah
Pool OS only recommends: it never issues a ruling, changes a PSR, waives a loss, posts a journal or approves a
related-party allocation. Switching any service off therefore stops advice, never a business process.

**Kill switch:** Administration (platform administrator) → AI Model Registry → Disable, with a reason; the same tab edits the inventory (owner, purpose, provenance, validation, retirement, threshold). The change is in the
audit log. A disabled service answers "This AI feature is currently disabled" (HTTP 503); nothing is invented.

**Confidence threshold:** per model in the registry (`confidence_threshold`, default 0.800). Outputs below it are counted as
low-confidence in the metrics. Every output still waits for a person's disposition (accept, reject, override with a reason).

| Service | Registry name | Fallback when off or failing | Manual procedure |
|---|---|---|---|
| Shariah Policy Copilot | `shariah_copilot` | 503 / fixed "no approved internal ruling" answer when there is no evidence | The Shariah Secretariat searches the Fatwa Register and the approved documents directly and drafts the comparison; the Board decides as usual |
| Contract Analyzer | `contract_analyzer` | keyword screen, flagged as fallback; always needs human review | The Product Manager and the Secretariat read the contract against the clause checklist of the template |
| Allocation Anomaly Detector | `allocation_anomaly_detector` | no anomaly recommendations are produced | The finance checker compares the run with the previous period using the run's pre-approval tests (prior-period yield, fairness) before checking it |
| Reconciliation Copilot | `reconciliation_copilot` | no proposed matches | The finance maker matches bank, GL and system records by hand in the Reconciliation Center; unexplained amounts go to suspense as named items |
| Liquidity Forecast | deterministic, no model | not applicable | The pool manager reviews the scheduled maturities and payouts list |
| Member Risk & Hardship | rule-based | not applicable | Staff review arrears records and hardship requests directly |
| Disclosure Generator | fixed templates, no model | not applicable | Statements keep the English narrative; Urdu and Arabic texts come from the same templates |
| Audit Sampling | rule-based | not applicable | The auditor selects samples manually and records the selection rationale |
| Fraud & Collusion indicators | rule-based | not applicable | The KYC/AML team reviews duplicate identities and payout patterns from the participant and payout lists |

**Before re-enabling a service:** record why it was disabled and what was fixed (Model Governance reason field), check the
validation status and date in the model inventory, and run `audit_reports/scripts/copilot_red_team.py` for the copilot.
