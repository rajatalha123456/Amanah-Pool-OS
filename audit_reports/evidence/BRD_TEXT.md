NOVU LABS
AMANAH POOL OS
AI-Based Islamic Pool Management Platform
Business Requirements Document • Functional Architecture • Shariah Controls • Accounting & Profit Allocation Engine • UI Catalogue
| PRODUCT VISION  One configurable platform for Islamic-bank pools, Mudarabah and Musharakah investment pools, and community savings circles - with explainable AI, maker-checker controls, immutable audit evidence, and jurisdiction-specific rule packs. |
| Prepared for | Product owner | Document status |
| Imperium Group Holdings / Novu Labs | Founder & Group Executive Chairman | Developer-ready v1.0 |
# 1. Executive Summary
Amanah Pool OS is a cloud-ready, multi-tenant platform that creates, governs, operates, closes and audits Shariah-compliant financial pools. It separates product configuration from transaction processing: the same core ledger and workflow layer can run a bank deposit pool, a restricted Mudarabah mandate, a Musharakah venture, or a non-profit community savings circle without mixing their contracts or economics.
| NON-NEGOTIABLE CONTROL  AI may recommend, detect, reconcile and explain. It must not independently issue a Shariah ruling, change an approved profit-sharing ratio, waive a loss, post a financial journal, or approve a related-party allocation. |
| Outcome | Platform capability | Evidence produced |
| Shariah integrity | Contract-aware rules, prohibited-income controls, approval gates | Fatwa/version link, exception log, purification trail |
| Fair allocation | Daily funds, weightages, PSR, direct expenses, reserves and loss waterfall | Reproducible calculation sheet and signed run |
| Operational scale | Straight-through imports, reconciliations, member collections and payouts | Batch controls, reconciliations, bank proofs |
| Regulatory readiness | Jurisdiction packs, disclosures, audit workpapers and retention | Examiner portal and immutable evidence bundle |
| Customer trust | Statements, explainable returns, voting and transparent schedules | Customer-facing calculation narrative |
# 2. Scope and Supported Operating Models
| Model | Primary contracts | Core computation | Typical users |
| Islamic bank pools | Mudarabah / Wakalah; asset contracts such as Murabahah, Ijarah, Diminishing Musharakah | Daily product balances × approved weightages; gross income less direct pool expenses; PER/IRR where permitted | Islamic banks, windows, treasury, finance, Shariah |
| Investment pools | Restricted/unrestricted Mudarabah; Musharakah | Capital units, PSR, realized/unrealized results, manager share, loss by capital unless misconduct is established | Asset managers, investors, trustees, fund administrators |
| Community savings | Qard-based rotating savings, Wakalah service model, cooperative rules | Contribution calendar, draw/rotation, arrears, payout eligibility; no interest or time-value uplift | Associations, employers, cooperatives, families |
## Out of scope for the first production release
Issuing a legal or Shariah opinion without qualified human approval.
Guaranteeing capital or profit in a risk-sharing contract except where legally and contractually valid.
Crypto custody, Takaful underwriting, Sukuk issuance and full core-banking general ledger replacement.
Automated debt collection tactics that conflict with applicable law, dignity or approved Shariah policy.
# 3. Personas, Roles and Segregation of Duties
| Role | Primary powers | Restricted actions |
| Platform Super Admin | Tenant provisioning, feature flags, encryption keys | Cannot view tenant financial data by default |
| Product Manager | Draft products, rules, disclosures | Cannot approve own configuration |
| Pool Manager | Create pools, assign assets, propose allocations | Cannot approve calculation run or Shariah exception |
| Finance Maker / Checker | Imports, journals / independent approval | No change to signed Shariah parameters |
| Shariah Secretariat | Research, document control, exception triage | No final ruling unless delegated |
| Shariah Board / Advisor | Approve contracts, rules, exceptions, purification | No silent retrospective parameter change |
| Risk & Compliance | Limits, KYC/AML alerts, regulatory reporting | No profit manipulation |
| Internal / External Auditor | Read-only evidence, sampling, reperformance | No operational posting |
| Investor / Depositor / Member | Statements, votes, consent, disputes | Only own data and authorized pool information |
# 4. Modular Architecture
| Module | What it delivers |
| Tenant & Jurisdiction Studio | Entities, branches, currencies, calendars, languages, accounting policy and retention. |
| Product & Contract Studio | Mudarabah, Musharakah, Wakalah and Qard templates; PSR, weightage, tenure, notice and disclosure rules. |
| Pool Lifecycle | Draft, Shariah review, approved, open, frozen, allocation, closed and archived states. |
| Capital & Membership | Account opening, KYC/KYB, subscriptions, redemptions, contributions, nominees and member limits. |
| Asset Assignment | Tag financing assets and investments to one pool; transfer with effective date, valuation and approval. |
| Income & Expense | Accruals, realization, direct expenses, provisions, write-offs, reversals and non-permissible income. |
| Profit Allocation | Daily average balances, weightages, PSR, Mudarib share, Wakalah fee, Hiba controls, PER/IRR and rounding. |
| Loss & Impairment | Capital loss waterfall, negligence/misconduct cases, provisions, write-offs and recoveries. |
| Community Circle | Schedules, ballots/rotation, guarantees, late payments, hardship, payout and dissolution. |
| Shariah Governance | Fatwa register, policy mapping, pre-launch approval, exception management, review and audit. |
| Accounting Subledger | Double-entry postings, chart mapping, period close, reversals, suspense and GL export. |
| AI & Analytics | Forecasts, anomaly detection, document extraction, explanations, copilot and scenario simulation. |
| Reporting & Portal | Regulatory, management, investor/member statements, disclosures and examiner data room. |
| Integration Hub | Core banking, GL, CRM/KYC, payment rails, market data, document signing, notifications and BI. |
# 5. Pool Configuration Model
| Configuration domain | Required controls |
| Identity | Pool code, legal entity, branch, model, base currency, timezone, calendar, start/end. |
| Contract | Contract type/version, Rab-ul-Maal, Mudarib/partner/agent, PSR, Wakalah fee, loss basis. |
| Participation | Products/classes, minimums, tenure, withdrawal, notice, caps, eligibility and KYC tier. |
| Weightages | Balance tiers, tenor bands, customer class, effective dates, maximum change and approval. |
| Assets | Eligible contracts/sectors, concentration, liquidity buffer, valuation, transfer and ring-fencing. |
| Income/expense | Permitted revenue, direct expense taxonomy, provisioning, write-off, reversal and purification. |
| Reserves | PER/IRR availability, basis, cap, ownership, approval, release and disclosure. |
| Governance | Shariah decision, quorum, maker-checker, exception SLA, audit frequency and disclosure pack. |
| Accounting | Chart mapping, accrual policy, rounding, posting calendar, close and restatement. |
| AI policy | Models allowed, confidence thresholds, human decision gates, prohibited actions and retention. |
# 6. End-to-End Workflows
## 6.1 Product and pool launch
Product Manager selects jurisdiction and operating model.
Contract Studio loads approved clauses and mandatory parameters.
AI performs completeness, conflict and policy-mapping checks.
Finance validates accounting mappings; Risk validates limits and disclosures.
Shariah Secretariat prepares review pack; Shariah authority approves, rejects or returns.
Checker activates the product and pool using a future effective timestamp.
System seals the configuration version and publishes customer disclosures.
## 6.2 Daily bank-pool processing
Import end-of-day balances, asset income, expenses, provisions and transfers.
Validate control totals, duplicates, value dates, missing product/asset tags and closed periods.
Compute daily funds and weighted balances by product/class.
Reconcile assets, sources, pool equity and suspense.
AI identifies unusual yield, cross-pool leakage or allocation drift.
Maker resolves exceptions; checker signs the daily close.
## 6.3 Period profit distribution
Freeze period inputs and configuration versions.
Determine gross pool income and permitted direct expenses.
Calculate distributable profit and reserve appropriations where enabled.
Apply customer weightages and calculate weighted participation.
Allocate profit, compute Mudarib share or Wakalah fee and handle rounding.
Run tolerance, fairness, negative-yield and prior-period comparison tests.
Finance checker and Shariah reviewer approve; post journals and issue statements.
## 6.4 Mudarabah/Musharakah investment cycle
Investor completes KYC, suitability and disclosures; signs contract.
Subscription is received and units/capital account created.
Capital is deployed only to eligible assets/projects.
Valuations and cash flows update NAV/capital accounts.
Profit follows approved PSR; genuine Musharakah loss follows capital ratio.
Any manager negligence allegation opens a controlled investigation case.
Exit/redemption settles subject to valuation, liquidity and contract terms.
## 6.5 Community savings circle
Organizer selects Qard-based or approved Wakalah operating model.
Members accept rules, contribution schedule, payout order/draw method and hardship policy.
System verifies identities and payment mandates; no interest-based uplift is configured.
Contributions are collected and reconciled; arrears trigger respectful reminders.
Eligibility gate confirms required funds and approvals before payout.
Members receive transparent ledger, receipts and schedule changes.
Final reconciliation, surplus/shortfall treatment and closure are approved.
# 7. Profit, Loss and Allocation Engine
| ENGINE PRINCIPLE  Every calculation run is deterministic and reproducible. Inputs, configuration version, formulas, overrides, approvers and generated journals are hashed and retained. AI can explain or challenge a run, but the signed result comes from the rules engine. |
## 7.1 Core calculation objects
| Object | Definition / formula |
| Daily funds | Closing balance or configured daily-average method after eligible adjustments. |
| Weighted funds | Daily funds × approved product/class weightage. |
| Participation ratio | Participant weighted funds ÷ total weighted funds. |
| Gross pool income | Eligible realized/accrued income assigned to the pool for the period. |
| Direct pool expenses | Only approved expenses directly attributable under the applicable rule pack. |
| Distributable profit | Gross income - direct expenses - provisions/write-offs ± reversals - purification ± approved reserve movements. |
| Investor profit | Profit share based on PSR and/or weighted participation as defined by the contract. |
| Mudarib share | Distributable profit × approved Mudarib PSR; never a share of capital. |
| Musharakah loss | Verified loss allocated according to capital contribution ratio, subject to misconduct findings. |
| Community payout | Scheduled eligible contributions available for the designated recipient, less only approved transparent fees. |
## 7.2 Worked bank-pool example
| Input | Value |
| Gross pool income | PKR 12,000,000 |
| Approved direct expenses and provisions | PKR 1,000,000 |
| Distributable profit before reserves | PKR 11,000,000 |
| Customer A weighted funds | PKR 60,000,000 |
| Customer B weighted funds | PKR 40,000,000 |
| Total weighted funds | PKR 100,000,000 |
| Customer A allocation | PKR 6,600,000 |
| Customer B allocation | PKR 4,400,000 |
The example is illustrative only. The engine must apply the approved jurisdiction pack, contractual PSR, daily-fund method, reserve policy, taxation and rounding rules in force for that pool and period.
## 7.3 Rounding, corrections and restatements
Calculate at high precision; round only at configured posting/output stages.
Send residual rounding to a disclosed pool rounding account, never to an arbitrary participant.
No edit to a signed run. Corrections use reversal and rerun with linked reason, impact and approvals.
Back-dated transactions enter an adjustment period unless a formally approved restatement is opened.
# 8. Shariah Governance and Control Framework
| Control | System behavior |
| Rule hierarchy | Law/regulator → adopted Shariah standards → Shariah Board rulings → product contract → operating procedure. Conflicts block activation. |
| Decision register | Decision, scope, evidence, effective date, superseded version, conditions and approving scholars. |
| Pre-launch review | No product, pool or material parameter activates without documented Shariah approval. |
| Exception handling | Classify potential non-compliance, quarantine value, investigate, decide treatment and disclose. |
| Purification | Identify non-permissible income, prevent distribution, approve charity disposition and retain proof. |
| Related parties | Disclose, price-test, conflict declaration and elevated approval. |
| Shariah audit | Risk-based test plan, samples, findings, management responses, remediation and annual report. |
| Change governance | Impact assessment, regression simulation, approvals, notification and effective dating. |
Reference alignment: the platform is designed to support Pakistan SBP pool-management instructions and amendments, AAOIFI Governance Standard GS 1 (Revised 2024), and IFSB governance/risk principles. Each implementation still requires legal, accounting and qualified Shariah validation for the chosen jurisdiction.
# 9. AI Capabilities and Guardrails
| AI service | Business value | Human-control boundary |
| Shariah Policy Copilot | Retrieves approved internal rulings and standards; drafts comparison and evidence pack | Citations mandatory; cannot issue fatwa |
| Contract Analyzer | Extracts contract type, PSR, fees, loss clauses, dates and conflicts | Low confidence routes to human |
| Allocation Anomaly Detector | Flags yield spikes, weightage drift, cross-pool leakage, unusual reserves and favoritism | Advisory only; reason codes visible |
| Cash-flow & Liquidity Forecast | Forecasts withdrawals, contributions, payouts and asset maturities | Scenario ranges, no guaranteed outcome |
| Reconciliation Copilot | Matches bank/GL/core records and proposes resolutions | Cannot post or write off |
| Member Risk & Hardship | Predicts arrears and offers approved support paths | No discriminatory protected-trait inference |
| Disclosure Generator | Explains return and allocation in plain language and Urdu/Arabic/English | Uses signed run only |
| Audit Sampling | Risk-ranks pools, runs and transactions for review | Sampling logic logged and challengeable |
| Fraud & Collusion Graph | Detects duplicate identities, related accounts and suspicious payout patterns | KYC/AML team decides action |
| Scenario Simulator | Tests PSR, weightage, expense, reserve and liquidity changes before approval | Sandbox cannot alter production |
## AI governance requirements
Model inventory, owner, purpose, version, training/source provenance, validation and retirement.
Prompt/output logging with masking of sensitive data and configurable retention.
Accuracy, drift, bias, hallucination, override and false-positive metrics.
Role-based access to copilots; no broad retrieval across tenants.
Approved knowledge base only for Shariah answers, with paragraph-level citations.
Kill switch, safe fallback and manual operating procedure for each AI service.
# 10. Accounting and Journal Architecture
| Event | Illustrative debit | Illustrative credit |
| Participant subscription / contribution | Cash / settlement receivable | Participant capital, investment account or member payable |
| Eligible asset income accrual | Accrued income receivable | Pool income |
| Direct pool expense | Pool direct expense | Cash / payable |
| Profit allocation | Pool distributable profit / appropriation | Participant profit payable and manager share payable |
| Purification | Non-permissible income clearing | Charity payable |
| Payout / redemption | Participant/member payable | Cash |
| Provision / write-off | Pool impairment expense | Allowance / asset |
| Reversal / recovery | Allowance / cash/receivable | Pool recovery income or original pool adjustment |
| ACCOUNTING NOTE  Exact account classification and recognition must be configured by jurisdiction and approved accounting policy. Pool subledger entries reconcile to the enterprise GL; the platform never silently balances through suspense. |
# 11. Data Model
| Domain | Core entities |
| Foundation | Tenant, LegalEntity, JurisdictionRulePack, User, Role, ApprovalMatrix |
| Product & governance | Product, ContractTemplate, ShariahDecision, Pool, PoolVersion |
| Participation | Participant, Member, CapitalAccount, Subscription, ContributionSchedule, Asset |
| Assets & performance | AssetAssignment, IncomeEvent, ExpenseEvent, ProvisionEvent, Valuation, DailyBalance, WeightageBand |
| Allocation & finance | ProfitSharingRule, ReserveAccount, AllocationRun, AllocationLine, JournalBatch, Payment, Payout |
| Assurance & AI | ExceptionCase, PurificationCase, AuditTest, EvidenceObject, ModelVersion, AIRecommendation, Consent, Notification |
## Key integrity constraints
An asset has one effective pool assignment at a timestamp unless an approved participation structure explicitly permits sharing.
A signed allocation run references immutable pool, contract, rate, balance and rule-pack versions.
PSR totals must equal the configured whole; Musharakah loss ratios derive from capital ratios.
No contribution, payout, journal or exception may be physically deleted after posting; use reversal/state transition.
Every override requires reason, evidence, maker, checker and timestamp.
# 12. APIs and Integrations
| Integration | Pattern | Key exchanges |
| Core banking / LOS / LMS | REST, events, SFTP | Accounts, daily balances, financing assets, income, provisions |
| ERP / General ledger | API or files | Chart mapping, journal batches, posting status, trial balance |
| KYC/KYB/AML | API/webhook | Identity, screening, risk, ongoing alerts and case status |
| Banking/payment rails | API/ISO messages | Collections, mandates, payouts, returns and settlement |
| Market/valuation data | API | Prices, FX, benchmarks for disclosure/reference only |
| Digital signature / documents | API | Contracts, consent, disclosure receipt and evidence |
| Messaging | API | Email, SMS, WhatsApp/push templates and delivery status |
| BI / data lake | Events/CDC | Curated, masked analytical datasets |
| Regulator / auditor portal | Secure export/read-only | Returns, reconciliations, evidence bundles and samples |
## Representative API surface
POST /v1/pools and POST /v1/pools/{id}/versions
POST /v1/pools/{id}/assets:assign
POST /v1/imports/daily-balances
POST /v1/allocation-runs:simulate and :execute
POST /v1/allocation-runs/{id}:approve
POST /v1/community-circles/{id}/contributions
POST /v1/community-circles/{id}/payouts:release
POST /v1/shariah-exceptions
GET /v1/statements/{participantId}
GET /v1/audit/evidence-bundles/{period}
# 13. Dashboards, Reports and Notifications
| Audience | Dashboards/reports |
| Executive | AUM/funds, distributable profit, yield, liquidity, exceptions, growth, forecast and jurisdiction view |
| Pool manager | Asset mix, income, expenses, daily funds, weightages, pending items and close readiness |
| Finance | Reconciliations, journals, provisions, suspense, residuals, close and restatements |
| Shariah | Approval queue, exceptions, purification, contract coverage, review plan and finding age |
| Risk/compliance | Concentration, liquidity, AML/KYC, related parties, limits and breaches |
| Investor/depositor | Balance, profit, methodology, transactions, disclosures, tax/Zakat support and disputes |
| Community member | Contribution status, payout schedule, pool ledger, vote/consent, receipts and hardship request |
| Auditor/regulator | Signed runs, version history, reperformance inputs, exceptions, samples and evidence exports |
# 14. Security, Privacy and Non-Functional Requirements
| Area | Requirement / target |
| Availability | Target 99.9% monthly for production; graceful degradation for AI services. |
| Performance | P95 interactive APIs <2 sec; configurable batch SLA; million-account horizontal scaling. |
| Security | SSO/MFA, RBAC+ABAC, tenant isolation, encryption in transit/at rest, secrets vault, WAF and EDR. |
| Auditability | Append-only audit events; signed calculation manifests; tamper-evident evidence hashes. |
| Privacy | Purpose limitation, minimization, consent, residency, retention and data-subject workflows. |
| Resilience | Multi-zone deployment, encrypted backups, tested restore, RPO ≤15 min and RTO ≤4 hr target. |
| Accessibility | WCAG 2.2 AA target, keyboard access, contrast, screen-reader labels and localization. |
| Localization | Multi-currency, timezone, calendars, English/Urdu/Arabic; RTL-ready UI. |
| Observability | Metrics, traces, logs, job lineage, data-quality alerts and business control monitoring. |
# 15. Screen Inventory
| Foundation | Screens |
| 1 | Sign in & MFA |
| 2 | Tenant switcher |
| 3 | Executive command center |
| 4 | Notifications |
| 5 | User/role administration |
| 6 | Jurisdiction rule packs |
| 7 | Approval matrix |
| Product & pool | Screens |
| 1 | Product catalogue |
| 2 | Contract template editor |
| 3 | New pool wizard |
| 4 | Pool overview |
| 5 | Pool version comparison |
| 6 | Asset eligibility rules |
| 7 | Asset assignment |
| 8 | Weightage bands |
| 9 | PSR/fee setup |
| 10 | Reserve policy |
| Operations & finance | Screens |
| 1 | Daily operations cockpit |
| 2 | Balance import |
| 3 | Income/expense workbench |
| 4 | Reconciliation center |
| 5 | Allocation simulation |
| 6 | Allocation run detail |
| 7 | Approval ceremony |
| 8 | Journal batches |
| 9 | Period close |
| 10 | Restatement wizard |
| Shariah & risk | Screens |
| 1 | Shariah board workspace |
| 2 | Decision/fatwa register |
| 3 | Exception case |
| 4 | Purification ledger |
| 5 | Shariah audit plan |
| 6 | Risk dashboard |
| 7 | Limits & breaches |
| 8 | Related-party review |
| Investment & community | Screens |
| 1 | Investor onboarding |
| 2 | Investor portfolio |
| 3 | Subscription/redemption |
| 4 | Musharakah capital accounts |
| 5 | Community circle setup |
| 6 | Member roster |
| 7 | Contribution calendar |
| 8 | Rotation/draw room |
| 9 | Payout release |
| 10 | Hardship & arrears |
| AI & assurance | Screens |
| 1 | AI copilot |
| 2 | Anomaly queue |
| 3 | Scenario simulator |
| 4 | Liquidity forecast |
| 5 | Model governance |
| 6 | Auditor portal |
| 7 | Evidence bundle builder |
| Self-service | Screens |
| 1 | Depositor statement |
| 2 | Investor statement |
| 3 | Member mobile home |
| 4 | Contribution receipt |
| 5 | Vote/consent |
| 6 | Dispute/request center |
# 16. Business Rules and Acceptance Criteria
| Rule | Acceptance criterion |
| BR-001 | A pool cannot activate without an approved contract version, rule pack, accounting mapping and approval matrix. |
| BR-002 | Effective-dated weightages and PSRs cannot overlap for the same class. |
| BR-003 | A change affecting economics requires simulation and customer/regulatory notification workflow where applicable. |
| BR-004 | A signed allocation run is immutable; corrections require reversal and a linked rerun. |
| BR-005 | Non-permissible income is excluded from participant distributable profit and routed to controlled purification. |
| BR-006 | Musharakah financial loss allocation follows verified capital ratios unless an approved liability determination applies. |
| BR-007 | A community circle cannot calculate interest, late-interest or a time-based uplift. |
| BR-008 | No payout releases unless collections, beneficiary eligibility, KYC status and dual approval pass. |
| BR-009 | All AI recommendations display source, confidence, reason and human disposition. |
| BR-010 | Cross-tenant reads and model retrieval are denied and security tested. |
# 17. Delivery Roadmap
| Phase | Indicative focus | Exit outcome |
| 0 - Discovery & Shariah design | Jurisdiction, contracts, accounting, process mapping, data and control inventory | Signed solution blueprint and rule taxonomy |
| 1 - Foundation MVP | Tenant, product/pool studio, ledger, approvals, daily import, bank-pool allocation, statements | One pilot bank pool runs in parallel |
| 2 - Governance & AI | Shariah workspace, exceptions, purification, audit, anomaly and reconciliation copilots | Controlled AI and audit evidence live |
| 3 - Investment pools | Subscriptions, units/capital, valuation, Mudarabah/Musharakah allocation and investor portal | Pilot investment product live |
| 4 - Community circles | Members, contributions, rotation/draw, payouts, hardship and mobile experience | Pilot circle live |
| 5 - Scale & jurisdictions | Additional rule packs, integrations, HA/DR, multilingual and regulator packs | Commercial multi-tenant release |
# 18. Testing and Go-Live Gates
Formula unit tests with regulator-approved worked examples and edge cases.
Golden-dataset reperformance against independent spreadsheets/manual calculations.
Contract/rule conflict tests, negative-profit/loss tests, reserve cap and rounding tests.
Migration reconciliation: record counts, balances, capital, accrued income and historical statements.
RBAC, tenant isolation, penetration, API, privacy and disaster-recovery tests.
Shariah Board user acceptance and documented approval of configured products.
Finance parallel run for at least two representative periods before production cutover.
AI validation, hallucination/red-team tests, fallback and monitoring dashboards.
# 19. Implementation Decisions Required
| Decision | Recommended default |
| Initial jurisdiction | Pakistan/SBP rule pack, designed for later AAOIFI/IFSB-aligned packs |
| First pilot | Bank Mudarabah deposit pool with daily funds, weightages, expenses, provisions and distribution |
| Deployment | Cloud-native private tenant; data residency configurable |
| Ledger | Dedicated immutable subledger integrated with enterprise GL |
| AI hosting | Private enterprise model gateway with approved retrieval corpus and PII controls |
| Brand | Amanah Pool OS by Novu Labs; premium navy, emerald and gold UI |
| Governance | Named Shariah advisor/board, finance checker, risk reviewer and product owner before configuration |
# 20. Primary Reference Frameworks
State Bank of Pakistan: Instructions for Profit and Loss Distribution and Pool Management for Islamic Banking Institutions (2012), clarifications (2013), amendments (2024) and clarification (2025).
State Bank of Pakistan: Shariah Governance Framework and applicable Islamic banking circulars.
AAOIFI: Governance Standard GS 1 (Revised 2024) and other adopted Shariah, governance and accounting standards relevant to each product.
Islamic Financial Services Board: applicable governance, disclosure, risk management and PSIA principles.
Disclaimer: This blueprint is a technology and operating-model specification. It is not a fatwa, legal opinion, accounting opinion, investment recommendation or regulatory approval. Each production configuration requires validation and approval by appropriately qualified professionals and authorities.