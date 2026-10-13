# Shariah Governance Audit (BRD sections 6, 8, 16)

This audit checks whether the system enforces the controls the BRD describes. It issues no Shariah opinion. Items needing a
qualified Shariah Board, legal, accounting or regulatory decision are flagged as such.

## Lifecycle trace
| Step | Where enforced | Evidence | Result |
|---|---|---|---|
| Fatwa register | `products/models.py` `ShariahDecision` (scope, supersedes, effective/expiry), `products/shariah.py` | BT ShariahRegisterTests (4), test_quorum (4) | PASS |
| Contract template | approved template required at activation | BT activation gates | PASS |
| Product catalogue | maker-checker; PM cannot approve own | BT products.tests | PASS |
| Pool creation | wizard; draft state | E2E wizard | PASS |
| Review and approval | Shariah Board approve; quorum for rulings | BT test_quorum | PASS (no "return" state, R-051) |
| Activation | `pools/activation.py` 8 gates incl. decision in force, rule conflicts | BT test_activation_gates (12) | PASS |
| Financial processing | events, imports, period lock | BT income derivation, PeriodLockTests | PASS, except FIN-01 (pending balances used) |
| Allocation | 4-stage ceremony for bank pools | BT ceremony tests | PARTIAL: investment pools have no Shariah stage (F-06) |
| Journal | posted only at release, balanced, immutable | BT ImmutabilityTests | PASS |
| Statement | per-account statements at release | BT StatementTests | PASS |
| Audit evidence | hash-chained audit log, evidence bundle | BT test_audit_chain (7), E2E auditor | PASS |

## Required negative tests
| Question from the brief | Answer | Evidence |
|---|---|---|
| Can a product or pool activate without Shariah approval? | No | BT `pools.test_activation_gates` |
| Can an unapproved contract be used? | No (activation gate) | BT activation gates |
| Can an expired or superseded rule be activated? | No: a superseded ruling with no approved successor backs nothing | BT `test_a_superseded_ruling_with_no_approved_successor_backs_nothing` |
| Can a Product Manager approve their own configuration? | No | BT products.tests; AT role matrix |
| Can a Pool Manager approve their own allocation? | No: check needs a finance checker who is not the maker; release needs an authorized signatory who is neither maker nor checker | `allocation/views.py:343-369, 618-624`; BT access control |
| Can an unauthorized user change an approved PSR? | No | AT patch probe (all 10 roles refused) |
| Can a signed allocation be edited? | No | BT `test_signed_run_cannot_be_edited_or_deleted`; AT admin bulk delete refused |
| Can non-permissible income be distributed? | No: excluded and routed to purification | BT `test_non_permissible_income_is_routed_to_purification_when_posted` |
| Can a Shariah exception be silently bypassed? | **Partly yes.** An open high/critical exception blocks the daily close (`pools/daily_close.py:35`) and the period close (`pools/period_close_engine.py:132-139`), but **not the release of an allocation run or an investment distribution**, and a run does not require a signed daily close. Journals can therefore post while a pool has an open serious exception. | static (grep: no `ExceptionCase` check in `allocation/views.py` or `investments/distribution_views.py`); not reproduced at runtime |
| Do purification transactions lack approval or evidence? | Approval exists (`purification-entries/{id}/approve/`, "mark distributed" with proof) | BT governance.tests; route list |
| Can related-party allocations bypass enhanced review? | No: conflict declaration, price test, and a different elevated approver are required | BT RelatedPartyTransactionApiTests (4) |
| Are rule conflicts blocked? | Yes at activation (`rule_conflicts`); there is no full rule hierarchy model | BT activation gates |
| Can retrospective parameter changes bypass effective dating? | **Yes for reserves and rule packs**: a reserve policy (rate, cap, balance) and a jurisdiction rule pack (WHT, Mudarib cap, PER/IRR ceilings) are changed in place, immediately, by one person, with no effective date or notice. PSR and weightage changes do follow effective dating and notice. | AT patch probe; BT EconomicsChangeNoticeTests |

## Business rules BR-001 .. BR-010
| Rule | Enforcement location | Positive test | Negative test | Actual | Result | Missing safeguards |
|---|---|---|---|---|---|---|
| BR-001 | `pools/activation.py` (`activation_readiness`, 8 gates), `pools/views.py` open | pool with all gates opens | missing contract / decision / mapping / matrix refused | as expected | PASS | rule pack content itself is not versioned |
| BR-002 | `allocation/validators.check_no_overlap` used in serializers | non-overlapping bands accepted | overlapping refused | as expected | PASS | no DB exclusion constraint; Django admin bypasses serializers |
| BR-003 | `allocation/economics_change.py`, notices | PSR/weightage change with notice approved and announced | change inside notice refused | as expected for PSR and weightages | **FAIL** | reserve policies and rule packs have no simulation, approval or notice (AT patch probe) |
| BR-004 | model guards (`allocation/models.py:188-219, 274-281`), restatement flow | rerun reverses original | edit/delete refused; tamper blocks approval | as expected | PASS | |
| BR-005 | `allocation/income.py`, purification entries | permissible income distributed | non-permissible excluded | as expected | PASS | classification is keyword-based (`accounting/models.py:112-198`) - Shariah Secretariat should review the keyword list |
| BR-006 | `investments/distribution.py`, `negligence.py` | loss by capital ratio | liability determination shifts loss to manager once | as expected | PASS | |
| BR-007 | no rate fields in circles (static) | payout equals collected pot | none exists | not tested | NOT TESTED | add a test that no circle endpoint accepts a rate, fee-by-time or late charge |
| BR-008 | `circles/payouts.py` pre-flight + request/approve/settle | complete payout | missing collections / KYC / same approver refused | as expected | PASS | |
| BR-009 | `ai_agents/recording.py`, `AIRecommendation` | outputs recorded with source/confidence/reason, disposition once | disposition without reason refused | as expected for 5 services | PARTIAL | allocation anomaly detector and reconciliation copilot write no recommendation record |
| BR-010 | tenant middleware + `TenantScopedModel` + copilot tenant filter | own-tenant reads | tenant B denied tenant A rows, ids, PATCH | 0 leaks across 5 record types, all routes | PASS | `LegalEntity` has no manager-level filter (view filters it; documented test) |

## Findings for the Shariah Board and the product owner
1. **F-06 (P1):** Investment-pool (Mudarabah/Musharakah) profit distributions are signed by one finance checker. No Shariah review stage and no authorized signatory, unlike bank pools (`investments/distribution_views.py:195-262`). BRD 6.3 requires "Finance checker and Shariah reviewer approve".
2. **F-09 (P1):** The bank-pool Shariah review stage can be switched off for every pool by an environment variable (`ALLOCATION_SHARIAH_REVIEW_REQUIRED_FOR_BANK_POOL`, `config/settings/base.py:204`). The check is evaluated live (`allocation/models.py:230-245`), so runs already checked could be released without review after a flip.
3. **F-11 (P1):** Open serious Shariah exceptions do not block allocation release (above).
4. **F-07 (P1):** The concentration engine and Risk dashboard present fixed percentages as "SBP statutory" limits and state that "a formal remediation filing is required within 90 days" (`pools/concentration_engine.py:1-27`, `frontend/src/pages/RiskLimitDashboard.tsx:401`). These rules are not sourced, not configurable, and measured against portfolio exposure. Regulatory limits are usually set against capital or equity. **Needs regulatory/legal confirmation; the values must come from the rule pack.**
5. Similar unsourced regulatory labelling: payout gates described as "required by SBP" (`allocation/payout_clearing_engine.py:233`); seeded period-close certificates read "Certified conforming to AAOIFI FAS-30 and SBP IBD Circular 03/2012" (`participants/seed_ledger.py:231,242`). The second is demo data, but it reads as a real certification. P2.
6. **Decisions still open** (documented in `docs/DECISIONS.md`, awaiting sign-off): WHT rates, Zakat at source, PER/IRR basis and ceilings, retention periods, the bank-pool loss basis (unweighted funds), and the Wakalah fee in loss periods.
