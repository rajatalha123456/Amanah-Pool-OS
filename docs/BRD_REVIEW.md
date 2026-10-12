# BRD requirement-by-requirement review (2026-10-12)

Method: the BRD was re-read section by section and each requirement was checked against the code, the tests and the
running screens. "Done" means implemented and exercised; "Partial" means it exists but is narrower than the BRD; "Missing"
means it is not there. Nothing is marked Done on the strength of a label.

## 1. Summary

| BRD section | Status |
|---|---|
| 1 Non-negotiable AI control | **Done.** AI code writes only its own records (checked by reading every write in `ai_agents`). |
| 2 Operating models | **Done** for bank pools, investment pools, community circles. |
| 3 Roles and segregation of duties | **Done** after the role-matrix review; see section 3 below for the screen-by-role result. |
| 4 Modules (14) | 12 done, **Integration Hub simulated**, Reporting partial (no regulator return formats; the BRD defines none). |
| 5 Pool configuration model | **Partial**: see 2.1. |
| 6 Workflows | **Done** except the integrations they assume (KYC/AML, e-sign, bank rails). |
| 7 Profit, loss, allocation engine | **Done**, one gap: a back-dated entry is refused instead of being routed to an adjustment period. |
| 8 Shariah governance | **Partial**: see 2.2. |
| 9 AI capabilities | **Done** for the ten services; **Partial** for AI governance metrics (accuracy, drift, bias, hallucination are not measured). |
| 10 Accounting and journals | **Done.** |
| 11 Data model | **Partial**: ContributionSchedule, Payment, EvidenceObject and AuditTest are not separate entities. Integrity constraints are enforced, except "every override needs evidence and a checker" which is enforced for most but not all overrides. |
| 12 APIs and integrations | **Simulated / not built**: core banking, ERP/GL, KYC/AML, payment rails, market data, e-sign, messaging (e-mail only), BI. |
| 13 Dashboards by audience | **Partial**: see 2.3. |
| 14 Non-functional | **Partial**: MFA, RBAC, tenant isolation, audit chain, privacy records are done; SSO, vault, WAF, HA/DR, 99.9% target, P95 and million-account scale, WCAG audit, Arabic, multi-currency and observability are not. |
| 15 Screen inventory (58 screens) | **56 done, 2 partial** (new pool wizard has 2 of 6 catalogue steps; asset eligibility has no dedicated screen). |
| 16 Business rules BR-001 to BR-010 | **Done** (BR-010 within this repository; retrieval isolation inside the external copilot service is outside it). |
| 18 Testing and go-live gates | Unit, isolation, RBAC, golden-example and browser tests exist; **not done**: independent golden dataset, migration reconciliation, penetration, DR, Shariah Board UAT, two-period finance parallel run, AI red-team. |

## 2. What is not complete

### 2.1 Pool configuration model (BRD section 5)
- **Identity**: a pool has name, code, product, effective date. It has **no legal entity, branch, timezone or calendar** (the currency lives on the product).
- **Participation**: the product has redemption notice and gate. **Minimum subscription, tenure, caps, member limits and KYC tier are not modelled.**
- **Governance**: exception SLA and audit frequency are not configurable. **Accounting**: accrual policy and posting calendar are not configurable.
- **AI policy**: models can be switched off and are inventoried, but "models allowed per pool" and confidence thresholds are not configuration.

### 2.2 Shariah governance (BRD section 8)
- Decision register: no **scope** field and **no superseded-version link** (supersession is by status only).
- Related parties: disclose and review exist; **price-test, conflict declaration and elevated approval are missing**.
- Shariah audit: plan, samples, findings and management response exist; **no annual report** output.
- Change governance: impact notice exists for PSR / weightage changes; a **regression simulation before approval** is not forced.

### 2.3 Dashboards by audience (BRD section 13)
**Update (member self-service built):** an investor or member can now raise a dispute or a hardship request (staff are notified, and
the member sees only their own requests and the answer), vote on circle proposals with their own login (bound to their membership,
one vote, tallies shown once closed), read the circle's ledger and print a receipt for each contribution, see their transactions and
a tax / Zakat support statement computed from the payout batches. The remaining gaps in this section are the per-audience *staff*
dashboards and a hand-held mobile layout; the text below is kept as the review found it.

There is one Command Center for every staff role. The BRD lists a different dashboard per audience (Executive, Pool manager, Finance, Shariah, Risk, Auditor).
Investor and member dashboards are narrower than listed:
- **Investor**: balance, statements, disclosures, consent and data download are there. **Disputes, transactions list and tax / Zakat support are missing.**
- **Member**: contribution status, payout position, rules acceptance, consent. **Voting, hardship request, receipts and a pool ledger are missing from the member portal** (staff record votes and receipts).

### 2.4 Screens that are only partly built (2 of 58)
New pool wizard (2 of the 6 catalogue steps) and Asset eligibility rules (a field on product creation, no dedicated screen). Member mobile home, contribution receipt, vote / consent and the dispute / request center are now covered inside the member portal; the tenant switcher is an indicator because a user belongs to one tenant.

## 3. Who sees which screens (menu level, from the running system)

"Should" follows BRD section 3 (powers and restrictions) and section 13 (audiences). The BRD does not list screens per role, so this mapping is a judgement; it lives in one file, `frontend/src/layouts/navItems.ts`.

| Role | Sees now | Verdict |
|---|---|---|
| Platform Super Admin | Administration | Correct (cannot view tenant financial data). |
| Product Manager | Command Center, Products & Pools, Shariah Governance, AI & Analytics | Command Center shows funds and profit; arguably **extra** for a role that drafts products. Kept as a landing page. |
| Pool Manager | Command Center, Products & Pools, Participants, Daily Operations, Allocation, Investments, Circles, Shariah Governance, Risk & Compliance, Finance & Ledger, Reports, Governance Config | Wide but each area is something a pool manager prepares or monitors. Finance & Ledger and Governance Config are read-only for this role. |
| Finance Maker | Command Center, Products & Pools, Participants, Daily Operations, Allocation, Investments, Circles, Risk & Compliance, Finance & Ledger, Governance Config | Correct for imports, journals, contributions, provisions. |
| Finance Checker | as Maker plus Reports | Correct (independent approval, close). |
| Shariah Secretariat | Command Center, Products & Pools, Allocation, Circles, Shariah Governance, AI & Analytics | Correct. |
| Shariah Board | Command Center, Products & Pools, Allocation, Investments, Circles, Shariah Governance, AI & Analytics, Reports | **Participants removed** in this review (personal data the Board does not need). |
| Risk & Compliance | Command Center, Products & Pools, Participants, Daily Operations, Allocation, Investments, Circles, Shariah Governance, Risk & Compliance, Finance & Ledger, AI & Analytics, Reports, Governance Config | Correct (limits, KYC, reporting); read-only on money screens. |
| Authorized Signatory | Command Center, Products & Pools, Allocation, Investments, Shariah Governance, Finance & Ledger, **Daily Operations (Period Close tab only)** | **Fixed**: the signatory locks a period but could not reach the screen. Governance Config and Reports removed earlier. |
| Auditor | Command Center, Products & Pools, Participants, Daily Operations, Allocation, Investments, Circles, Shariah Governance, Risk & Compliance, Finance & Ledger, Reports, Governance Config | Read-only everywhere; every write on these screens is refused (verified). |
| Investor / Member | My Portal, Notifications | Correct, but **incomplete** (see 2.3). |

Inside a screen, buttons and tabs are also role-gated (pool lifecycle, products, reconciliation, payout engine, reports, circles, AI panels) and a browser sweep (`npm run e2e:roles`) confirms that no role opens a screen that its API refuses.

## 4. Changes made in this review
- Shariah Board no longer sees or reads the participant registry.
- Authorized Signatory can reach Period Close (that tab only).
- Product creation takes the eligible asset types (asset eligibility rules); assignment already enforced them.

## 5. Recommended next work, in order
1. Member and investor self-service gaps (disputes and requests, voting, hardship request, receipts, tax / Zakat support).
2. Pool configuration fields (legal entity, branch, timezone, calendar, minimums, caps, tenure, KYC tier).
3. Related-party price-test and conflict declaration; decision supersession; Shariah audit annual report.
4. Role-specific home dashboards (BRD section 13).
5. Integrations, HA/DR, SSO and the go-live gates in section 18 (outside the code).


## 6. Update: the remaining code gaps were closed (2026-10-12, later)
- **Pool configuration (section 2.1)**: a pool now carries its legal entity, branch, timezone and working calendar (the calendar limits redemption dealing dates); a product carries minimum subscription, cap per account, minimum holding period, required KYC tier and a participant limit, all enforced (subscription, redemption, account and member creation) and sealed into the configuration snapshot and the investor disclosure. The KYC tier is set when a checker verifies an investor.
- **Shariah governance (section 2.2)**: a ruling has a scope and can supersede an approved ruling (approval marks the old one superseded; contracts follow the chain, nothing is rewritten silently); related-party transactions need a conflict declaration, an independent benchmark price test, a Risk recommendation and an elevated approval from the Board or the Authorized Signatory (a failed price test needs a written justification); a sealed annual Shariah audit report is built from the plans and findings.
- **Dashboards (section 2.3)**: each audience (pool manager, finance, Shariah, risk, auditor, signatory, product) has its own dashboard on the home screen, every figure counted from recorded data, `-` where there is no source.
- **Screens (section 2.4)**: the New Pool wizard has the catalogue's six steps; asset eligibility is chosen from the valid asset types (the earlier free-text box would have accepted invalid values) together with the participation terms.
- Still outside the code: real bank / KYC / e-sign integrations, SSO, vault, HA/DR, load and penetration tests, accessibility audit, Arabic and multi-currency, Shariah Board UAT and the finance parallel run.
