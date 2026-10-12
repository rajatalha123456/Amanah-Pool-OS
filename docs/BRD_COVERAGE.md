# BRD Coverage Report - Amanah Pool OS

Measured against the BRD (`NovuLabs_Islamic_Pool_Management_Platform_BRD`) and the UI Catalogue (42 screens).
Method: each requirement was checked against the code (models, views, engines) and the test suite; the 210+ backend tests pass.
Legend: **Done** = implemented and exercised by tests - **Partial** = exists but incomplete or not enforced - **Missing** - **Simulated** = works against a simulation, no real integration.

> Corrections to earlier statements in this project: (1) "one asset, one pool" **is** enforced (serializer-level) - I wrongly said it was not; it is still not a DB constraint and has no effective-dated transfer. (2) The UI Catalogue is mostly a *template* - about 34 of its 42 pages reuse four placeholder templates (table, dashboard cards, wizard, approval stages), so it fixes layout and navigation, not field-level behaviour.

## 0. Current status after the full audit (2026-10-11) - read this first

A full audit (`docs/AUDIT_REPORT.md`) found problems that the earlier progress figures did not account for. The most important ones:

- **Role checks inside a tenant are broken.** Many endpoints let any logged-in user update or delete records, which was confirmed with an investor login. Approved PSR, weightage and Shariah records can be edited in place. Investors can read other people's data.
- **Several controls can be bypassed:**
  - The period-close lock can be reversed.
  - One Board user can approve a fatwa through the quorum endpoint.
  - Duplicate or negative circle contributions inflate payouts.
  - Circle votes are not bound to the member.
  - The MFA secret can be re-read.
- **Fabricated content is presented as fact:**
  - The fraud/collusion engine accuses real members using invented data.
  - The CBS simulator writes fake balances into real tables.
  - Dashboards show hard-coded funds and yields.
  - The copilot drawer is canned text, and "verify" buttons do not verify.

Several rows below marked **Done** depend on controls that these findings undermine:
- BR-001/BR-002/BR-003: approved economics can be edited in place.
- BR-004: the period lock can be reversed.
- BR-008: payouts can be inflated.
- BR-010 holds between tenants only.

| | Before audit (my earlier estimate) | After audit | After P0 fixes (current) |
|---|---|---|---|
| Functional coverage of the BRD | ~91% | ~75-78% | **~82%** |
| Production readiness | ~71% | ~45-50% | **~58-60%** |

All P0 audit items are fixed (see the fix tracker in `docs/AUDIT_REPORT.md` section 7). The P1 fake and hard-coded displays still need work.

### Update 2026-10-12 (latest)

All P0 items and the P1 fake / hard-coded displays found in the audit are now fixed; 375 backend tests and 29 Playwright runs pass. Estimate now: functional coverage **~87%**, production readiness **~66-68%**. What still keeps readiness down: no real bank / SBP / FBR integrations (simulated), no external security review or load test, MFA and secrets handling still to be verified in a real deployment.

Four policy questions were settled using the BRD wording; where the BRD is silent the choice below is a documented default that the owner can change by editing the jurisdiction rule pack (no code change):
- **Provisions** - BRD 7.1: distributable profit = gross income - direct expenses - provisions/write-offs +/- reversals - purification - reserve movements. This is how the engine already works (approved provision entries feed the next allocation run).
- **PER/IRR** - BRD 4.x lists "availability, basis, cap" as rule-pack items. Basis chosen: appropriation rate is a % of profit (PER) / of the investors' share (IRR); the cap limits the *reserve balance* as a % of pool funds. A reserve policy whose cap exceeds the pack's `per_ceiling_pct` / `irr_ceiling_pct` is refused.
- **Withholding tax** - the BRD names no rates. Rates are now read from the rule pack (`wht_filer_pct`, `wht_non_filer_pct`); a payout batch is refused if the pack has none. The seed pack uses 15% / 30% as a demonstration value - **confirm with a tax adviser before real use**.
- **Zakat** - the BRD only requires "tax/Zakat support" in the statement. Zakat is therefore **not** deducted at source by default; a pack can enable it with `zakat_deduction_pct`, and the basis (per payout) should be reviewed by the Shariah board first.

New in this round: circle members can sign in (member portal: own membership, contributions, payouts; accept rules with their own e-signature reference), pool manager links a login to a member. 

### Update 2026-10-12 (BRD gap round)

Two BRD gaps found by re-reading the BRD against the code were closed. (Several rows in the tables below are older than this note and under-state what exists, e.g. BR-003 economics-change notice/impact and the circle rules acceptance are built; treat section 0 and these update notes as current.)
- **Pool lifecycle - frozen and archived states** (BRD: draft, review, approved, open, frozen, allocation, closed, archived): `pools/lifecycle.py`. A pool can be frozen with a recorded reason (pool manager / risk & compliance), which blocks new subscriptions, redemptions, contributions, payouts and allocation runs (HTTP 409). The freeze must be lifted by a *different* person (authorized signatory / finance checker). Only a closed pool can be archived. Audit-logged; PoolDetail has the buttons.
- **Privacy - consent and data-subject access** (BRD entity `Consent`, NFR privacy): `participants.Consent` per participant and purpose, one live consent per purpose, history kept on withdrawal, evidence required for remote methods. Members see and withdraw their own consents and download everything held about them (`my-data`); staff record consents. Not built: retention schedules / automatic deletion, and using consent to gate marketing messages (there are none).

Verification: 386 backend tests, `tsc` clean, 31 Playwright runs.

### Update 2026-10-12 (remaining items round)

- **Contribution reminders** (BRD 6.5): published circle rules now carry a first due date; `send_contribution_reminders` (daily) sends one gentle reminder before a due date and one when overdue (e-mail and/or in-app), tells Risk & Compliance / the pool manager about overdue members, never flags arrears or adds a charge automatically, and never repeats a reminder.
- **Data retention** (BRD privacy / tenant studio): `RetentionPolicy` is proposed by Risk & Compliance and approved by a different authorized person; `apply_retention` is a dry run unless `--apply`, deletes only read notifications past their period, and only reports support requests / AI records for manual review. Ledgers, statements, contracts, the audit log and Shariah records are outside it.
- **`docs/DEPLOYMENT.md`** lists environment variables, first-time setup, scheduled jobs and the blockers that sit outside the code.
- Still not built: circle guarantees, a UI for the retention register, real bank / KYC / e-sign integrations.

Verification: 396 backend tests, `tsc` clean, 31 Playwright runs.

## 1. Score

| Area | Done | Partial | Missing | Weight |
|---|---|---|---|---|
| Business rules BR-001..BR-010 | 7 | 2 | 1 | 10 items |
| Workflow rows 6.1-6.5 (38 rows) | 14 | 17 | 7 | |
| Modules (14) | 0 | 13 | 0 (1 simulated: Integration Hub) | |
| UI Catalogue screens (42) | all 42 pages exist; behaviour re-verified only where changed in this project | | | |
| BRD screen inventory (58) | present at page level except the gaps below | 5 | 3 | not checked one by one |
| Non-functional (9 rows) | 1 | 4 | 4 | |
| Go-live gates (8) | 0 | 4 | 4 | |

Reading of the table above (a judgement, not a measurement): **roughly two thirds of the functional BRD is built and roughly 45% is production-ready.** The gap to production is mostly (a) Musharakah/Wakalah, (b) real integrations, (c) go-live gates that need people, not code.

## 2. Business rules

| Rule | Status | Evidence / gap |
|---|---|---|
| BR-001 pool activation needs contract version, rule pack, accounting mapping, approval matrix | **Done** (updated) | `pools/activation.py` checks 8 gates at `open` (approved product + contract, Shariah decision in force, rule pack bound/default, approved PSR and weightages covering the effective date, complete accounting mapping for the pool model, approval-matrix rule for the release approval) and lists every gap; `GET /pools/{id}/activation-readiness/` and a PoolDetail checklist expose it. New models `ApprovalMatrixRule` and `AccountMapping` back two of the gates. |
| BR-002 effective-dated weightages / PSR cannot overlap | **Done** | `allocation/validators.check_no_overlap`, used by the serializers. Not a DB constraint. |
| BR-003 economics change needs simulation + notification | **Done** | A PSR / weightage approval inside a live pool computes the impact and opens a customer-notice period; the notice is announced through the notification service (`allocation/economics_change.py`). |
| BR-004 signed run immutable; reversal + linked rerun | **Done** | Model-level guards, hash re-verification on approve, restatement flow (bank pool and Mudarabah). |
| BR-005 non-permissible income excluded from distributable profit, routed to purification | **Done** (updated) | A run's income/expenses are derived from the pool's posted events (`allocation/income.py`); non-permissible income and bank-absorbed overhead are excluded, a `PurificationEntry` is raised when the event is posted, consumed events cannot feed another run, and a stale run cannot be signed. A hand-typed figure is a sealed override that needs a reason. Remaining weakness: event classification is keyword-based. |
| BR-006 Musharakah loss by capital ratio unless liability determination | **Done** | Mudarabah loss falls on investors; Musharakah loss follows capital ratios unless a negligence case determination applies (`investments/distribution.py`, negligence cases). |
| BR-007 no interest / late-interest / time uplift in circles | **Done** | No such field or calculation anywhere; payout = collected pot exactly. |
| BR-008 payout needs collections, eligibility, KYC, dual approval | **Done** | `circles/payouts.py` pre-flight + request/approve/settle with independent checker. |
| BR-009 AI output shows source, confidence, reason, human disposition | **Done** | Every AI output is stored as an `AIRecommendation` with source, confidence, reason and a human disposition; metrics and a kill switch via the model registry. |
| BR-010 cross-tenant reads and retrieval denied, security tested | **Done** | Tenant-bound JWT, isolation test suite over every tenant-scoped model, copilot calls carry the caller's tenant. Retrieval isolation inside the external copilot service is outside this repo's tests. |

## 3. Workflows

### 6.1 Product and pool launch
| Step | Status | Note |
|---|---|---|
| Select jurisdiction and operating model | Done | The rule pack is bound to the pool at activation (pool override, else tenant default) and its caps are enforced (Mudarib share, PER/IRR ceiling, WHT rates). |
| Contract Studio loads approved clauses / mandatory parameters | Partial | Templates and clauses exist; mandatory-parameter enforcement does not. |
| AI completeness/conflict/policy-mapping checks | Partial | Contract analyzer (keyword fallback, flagged for human review); catalogue's "AI configuration check" panel not built. |
| Finance validates mappings; Risk validates limits | Done (updated) | Finance owns `AccountMapping`, Risk & Compliance owns the `ApprovalMatrixRule` limits (Governance Config page, audited); both are activation gates. Maker-checker on the config itself is not built. |
| Shariah authority approves/rejects/returns | Done | Pool approve by Shariah Board; no "return" state. |
| Checker activates with future effective timestamp | Done | Activation readiness checks the effective date; economics changes carry their own effective-from and notice days. |
| Seal configuration version, publish disclosures | Done | Versions are sealed from the real governing configuration with a config hash; disclosures are published with a sealed terms hash and gate subscriptions. |

### 6.2 Daily bank-pool processing
| Step | Status | Note |
|---|---|---|
| Import balances | Done | Account-level, control totals, duplicates, KYC, open-account checks. |
| Import income / expenses / provisions / transfers | Partial | Income, expense, provision, write-off and recovery entries exist (maker-checker); asset transfers are modelled by assignment only. |
| Validate value dates, missing tags, closed periods | Done | Period lock enforced on imports, events, runs. |
| Daily funds and weighted balances | Done | Period-average, day-wise weightage. |
| Reconcile assets, sources, pool equity, suspense | Partial | Reconciliation batches and an advisory copilot; no real CBS/GL feed (simulated). |
| AI flags unusual yield / leakage / drift | Partial | Rule-based 5-run moving average. |
| Maker resolves, checker signs daily close | Partial | Period-close checklist with role sign-offs; no daily-close object. |

### 6.3 Period profit distribution
| Step | Status | Note |
|---|---|---|
| Freeze inputs and configuration versions | Done | `config_snapshot` sealed in the calculation hash. |
| Gross pool income and permitted direct expenses | Done (updated) | Derived from posted ledger events (BR-005). |
| Distributable profit, reserve appropriations | Done | PER/IRR with caps and balance movements. |
| Customer weightages, weighted participation | Done | |
| Profit, Mudarib share / **Wakalah fee**, rounding | Done | Mudarib PSR, Wakalah fee on average funds, and rounding residual are implemented and tested. |
| Tolerance, fairness, negative-yield, prior-period tests | Partial | Negative yield handled as loss; prior-period comparison only as an advisory anomaly after signing. |
| Finance checker + Shariah reviewer approve | Done (updated) | Implemented as the UI Catalogue's 4-stage ceremony: Finance Maker prepares -> Finance Checker independent check -> Shariah review (Secretariat or Board; a review, not a ruling, per BRD Section 3) -> final release by the new **Authorized Signatory** role. Maker, checker and signatory must be different users; every stage is logged and shown with its owner and timestamp. |
| Post journals, issue statements | Done | Balanced, tied-out journals; per-participant statements. |

### 6.4 Investment cycle
| Step | Status | Note |
|---|---|---|
| KYC, suitability, disclosures, contract signature | Partial | KYC, suitability notes and disclosure acknowledgement (with evidence) are built; contract e-signature is not integrated. |
| Subscription received, capital account created | Done | Units at published NAV, unit-movement ledger, balanced journal. |
| Deploy only to eligible assets/projects | Done | Eligibility rules are enforced on assignment (`pools/asset_rules.py`). |
| Valuations update NAV | Done | NAV snapshot maker/publisher. |
| Profit by PSR | Done (Mudarabah) | Time-weighted units. |
| Musharakah loss by capital ratio | Done | Distribution engine allocates by capital ratio. |
| Negligence allegation opens investigation case | Done | Negligence cases with determination; they affect loss allocation. |
| Exit/redemption subject to valuation, liquidity, terms | Done | Request -> independent checker approval, notice days and a 30-day gate (`investments/redemptions.py`). |

### 6.5 Community circle
| Step | Status | Note |
|---|---|---|
| Organizer selects Qard or Wakalah model | Partial | Qard only in behaviour. |
| Members accept rules, schedule, order, hardship policy | Done | Sealed circle rules with per-member acceptance; members can accept with their own login. |
| Verify identities and mandates | Partial | Member KYC status; no payment mandates. |
| No interest-based uplift | Done | |
| Contributions collected, reconciled; arrears -> reminders | Partial | Recorded with a payment reference, unique per member and cycle; arrears flagged and notified; no automatic reminder scheduler. |
| Eligibility gate before payout | Done | |
| Transparent ledger, receipts, schedule changes | Done | Receipts, mobile home, proposals/votes. |
| Final reconciliation, surplus/shortfall, closure | Done | Closure maker/checker with reconciliation (`circles/closure.py`). |

## 4. Modules (Section 4)

| Module | Status | Gap |
|---|---|---|
| Tenant & Jurisdiction Studio | Partial | Tenants, legal entities and rule packs exist and are enforced; calendars and retention schedules are not modelled. |
| Product & Contract Studio | Partial | See 6.1. |
| Pool Lifecycle | Done | Draft -> pending -> approved -> open -> (frozen) -> closed -> archived with versions; freeze needs a reason and a different person to lift. |
| Capital & Membership | Partial | Participants, accounts, KYC; nominee is a text field; limits/caps absent. |
| Asset Assignment | Partial | One-pool rule (serializer); no effective-dated transfer with valuation and approval; no ring-fencing. |
| Income & Expense | Done | Events, classification, provisions/write-offs/recoveries; runs derive their income from posted events. |
| Profit Allocation | Done | Including the Wakalah fee, reserves and loss waterfall. |
| Loss & Impairment | Done | Impairment, provisions, write-offs, recoveries and negligence cases are built. |
| Community Circle | Partial | Guarantees are not modelled; late-payment handling is arrears + hardship; closure and verifiable draw exist. |
| Shariah Governance | Partial | Decision register, quorum votes, exceptions, purification, audit plan exist; policy mapping, exception SLA missing. |
| Accounting Subledger | Partial | Double-entry, reversals, period close, CSV export with GL codes; accounts now resolve through `AccountMapping` (pool override -> tenant default) and each entry stores its logical key and GL code; no suspense handling. |
| AI & Analytics | Done | Copilot (external service), contract analyzer, anomaly, sampling, collusion indicators from real data, recommendation records with metrics and a kill switch. |
| Reporting & Portal | Partial | Statements, auditor portal, evidence bundle, sealed period report with CSV and in-app notifications; formal regulatory return formats are not defined by the BRD. |
| Integration Hub | **Simulated** | CBS, Raast/1LINK are simulations; no KYC/AML, GL, payment, e-sign or messaging integration. |

## 5. UI Catalogue (42 screens)

All 42 have a page. Notes only where behaviour differs from the catalogue:

| # | Screen | Gap vs catalogue |
|---|---|---|
| 03 | New Pool Wizard | Catalogue: 6 steps (Model, Contract, Economics, Assets, Governance, Review) + AI configuration check. Built: 2 steps. |
| 14 | Approval Ceremony | Built: 4 stages with owners/timestamps and control gates (reconciled, Shariah parameters sealed, final authority). Per-stage evidence counts ("12 items", "7 sources") are not built. 16/27/31/35 use the same template in the catalogue; their behaviour is covered by period close, the payout workflow, exception cases and related-party review respectively. |
| 12/13 | Simulator / Run | Catalogue's "Signed input manifest" (balances version, rules version, contract, hash) - hash and config snapshot exist in the data; verified against the catalogue's numbers by `test_brd_golden.py`. |
| 26 | Draw Room | Evidence list (rules accepted 24/24, observer signatures, video record) missing; only the seed/audit record exists. |
| 21 | Musharakah Venture View | UI exists; no backend logic behind capital ratios or results. |
| 38 | Copilot | Citations and approved-source list: present. Quality depends on the external service. |
| 39 | Model Governance | Kill switch only; no validation, drift or override metrics. |
| 25 | Contribution Calendar | Page exists; no automated due-date schedule behind it. |
| 02,04,07,09-11,15,17-20,22-24,28-30,32-34,36,37,40-42 | Template pages | Layout only in the catalogue; pages exist and work with real data where I changed them (allocation, circles, investments, participants, evidence). Dashboards (01, 04, 08, 34, 37) were not re-audited for data sources. |

BRD screen inventory (58): missing outright are **Notifications**, **Approval matrix**, **Asset eligibility rules**; partially covered are Reserve policy setup, Investor portfolio, Musharakah capital accounts, Limits & breaches workflow, Related-party elevated approval.

## 6. Non-functional (Section 14)

| Row | Status |
|---|---|
| Availability 99.9%, graceful AI degradation | Partial - AI fallback and kill switch exist; no HA setup. |
| Performance P95 < 2s, million accounts | Missing - allocation loads all balances in memory; no load test. |
| Security: SSO/MFA, RBAC, tenant isolation, encryption, vault, WAF | Partial - MFA, RBAC, tenant binding done; no SSO, secrets vault, WAF. |
| Auditability: append-only events, signed manifests, tamper-evident hashes | **Done** - hash-chained audit log, sealed runs, evidence bundle. |
| Privacy: consent, minimisation, residency, retention, data-subject workflows | Missing - no consent model, no retention policy. |
| Resilience: multi-zone, backups, RPO/RTO | Missing - untested. |
| Accessibility WCAG 2.2 AA | Missing - not audited. |
| Localization: multi-currency, English/Urdu/Arabic, RTL | Partial - English/Urdu; no Arabic; PKR only. |
| Observability | Partial - app logs only; no metrics/tracing. |

## 7. Go-live gates (Section 18)

| Gate | Status |
|---|---|
| Formula unit tests with regulator-approved examples | Partial - BRD 7.2 and UI catalogue worked examples now pass (`test_brd_golden.py`); no regulator-approved dataset yet. |
| Golden-dataset reperformance vs independent spreadsheets | Missing - needs your finance team's workbook. |
| Contract/rule conflict, negative-profit, reserve cap, rounding tests | Partial - negative-profit, reserve cap, rounding covered; conflict tests missing. |
| Migration reconciliation | Missing - no legacy data yet. |
| RBAC, tenant isolation, penetration, API, privacy, DR tests | Partial - RBAC and isolation tests; no penetration/DR tests. |
| Shariah Board UAT | Missing - human process. |
| Finance parallel run (2 periods) | Missing - human process. |
| AI validation, red-team, fallback, monitoring | Partial - fallback exists; no red-team or monitoring dashboards. |

## 8. Recommended build order

1. ~~Wire income/expense events into allocation runs (BR-005).~~ Done.
2. ~~Shariah / Authorized-Signatory approval chain (4-stage ceremony).~~ Done.
3. ~~BR-001 activation gates + approval matrix + accounting-mapping model.~~ Done.
4. **Notifications** (needed by BR-003, arrears reminders, approval nudges).
5. **Wakalah fee + Musharakah (loss by capital ratio, negligence case)**.
6. **Asset eligibility rules and effective-dated transfer** (closes the 6.4 deployment gap).
7. **Provisions / write-offs / recoveries, impairment journal.**
8. **Circle rules acceptance + draw evidence + closure.**
9. **Model governance metrics + uniform AI recommendation record (BR-009).**
10. **Non-functional and go-live gates** (performance test, backups, penetration test, golden dataset, UAT, parallel run).

## 9. Decisions needed from you

1. (Resolved) Shariah sign-off and Authorized Signatory: implemented as in catalogue screen 14, with the Board also allowed to perform the Shariah review.
2. Impairment accounting treatment (needs your accountant / Shariah advisor).
3. Business rule: how far back to carry a missing daily balance forward (currently 10 days).
4. Redemption: required notice period and liquidity buffer per product.

## Update: Wakalah, Musharakah, notifications, assets, provisions

- **Done:** BR-003 economics-change notice and notifications; Wakalah fee in bank and investment pools; Musharakah capital-ratio loss with managing-partner capital and negligence cases (BR-006, Shariah Board determines); asset eligibility per product, maturity and period-lock checks, effective-dated transfer; maker-checker provisions, releases, write-offs and recoveries with journals and income/expense events (screen: Risk & Compliance > Provisions & Write-offs).
- **Design choices to confirm with the accountant / Shariah advisor:** write-off consumes the asset's provision before hitting expense; Musharakah managing partner's PSR mudarib share is treated as their all-in profit share; provisions are entered by the maker (no automatic ageing rule yet); the approval-matrix amount limit does not yet apply to provision entries.

## Update: community circle governance

- **Done:** published, hash-sealed circle rules (contribution, cycle, order and hardship policy) with per-member acceptance evidence (in person / OTP / e-sign); acceptance by every active member gates the draw and payout pre-flight. The draw is now a real commit-reveal: the secret seed's hash is published first, members supply a seed, the order is a deterministic HMAC-SHA256 shuffle that anyone can recompute (`/circles/draws/{id}/verify/`); re-draws are refused. Final reconciliation (collected vs disbursed per member, blockers, surplus/shortfall needing a resolution note) and four-eyes closure.
- **Removed fakes:** draw-room "provably fair seal" (a hash of a predictable string) and the invented 10,000 default contribution.
- **Still open:** payment mandates, guarantees, automatic arrears detection from cycle deadlines, surplus/shortfall settlement postings (recorded and explained, not journalled).

## Update: redemption workflow (BRD 6.4 exit terms)

- **Done:** redemption is request -> independent finance-checker approval (previously one person redeemed instantly). Units are reserved by pending requests; the investor can request only on their own account; KYC required. Product terms: `redemption_notice_days` (dealing date must respect it) and `redemption_gate_pct` (redemptions in any 30-day window capped at that share of the latest published pool value). Pricing happens at approval from the latest published NAV on or before the dealing date; the dealing date must have arrived; units, movement and journal post only on approval. Rejection needs a reason.
- **Removed fakes:** hard-coded "Daily T+1" and "PKR 10,000 minimum" text in the investment pool terms panel.
- **Open:** product terms are set via API only (no UI), the gate uses pool value rather than a measured cash position, and the terms are not yet part of the sealed pool-version snapshot.

## Update: AI governance (BR-009)

- **Done:** every output of the copilot, contract analyzer, audit sampler, hardship predictor and collusion detector is stored as an `AIRecommendation`: model and version, who asked, the prompt (full-input hash plus truncated text), output, sources, confidence, reason, fallback flag, latency. The output is immutable; a person records accepted / rejected / overridden once, with a reason for anything but acceptance. Per-model metrics (volume, acceptance and override rates, fallback rate, confidence, latency) and a log with prompt/output viewer sit in the Model Governance tab. The rule-based features now respect the kill switch (an explicit disabled registry row blocks them).
- **Open:** the allocation anomaly detector and reconciliation copilot do not yet write recommendation records; no red-team or drift monitoring; metrics are computed from recorded decisions only.

## Update: maker-checker on governance configuration

- **Done:** changes to the approval matrix (proposed by Risk & Compliance) and the account mapping (proposed by Finance) are now proposals (`ConfigChangeRequest`, HTTP 202) with a mandatory reason; a different finance checker approves or rejects under `/governance/config-changes/`. Approval re-validates against current data and refuses a stale proposal (item changed since); one pending change per item; every step is audited and notifies the checkers. The matrix still cannot be deleted.
- **Open:** no automatic expiry of pending proposals; the approver set is finance checker / platform admin for both kinds (a separate approver for matrix limits, e.g. the Board, may be preferred by policy).

## Update: investor disclosures and acknowledgement (BRD 6.4)

- **Done:** a pool publishes a sealed, versioned `PoolDisclosure` built from the terms that actually govern it (contract, profit sharing incl. agent fee, exit notice and gate, reserves, Shariah decision, rule pack) plus mandatory risk warnings and fee statement. An investor acknowledges in the portal (risk box must be ticked) or staff record an in-person / OTP / e-sign acknowledgement with evidence. A subscription is refused unless the account acknowledged the latest disclosure and the pool's terms still match it - changing the PSR or exit terms forces a new disclosure. The onboarding tab shows the disclosure and each investor's status.
- **Open:** acknowledgement is a recorded evidence reference, not a vendor e-signature integration; suitability scoring against product risk is still free-text notes; disclosures are not yet part of the sealed pool-version snapshot or regulator-facing publication.
