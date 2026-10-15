# Har screen ki tafseel (menu ke mutabiq)

Menu mein sirf wohi items dikhte hain jo aapke role ke liye hain (`frontend/src/layouts/navItems.ts`). Server har cheez dobara check karta hai, isliye address bar mein type karne se bhi koi role dusre role ki cheez nahi kar sakta. Tarteeb ke liye `FROM_SCRATCH_WORKFLOW.md` dekhein; yeh file batati hai har screen **kya hai**.

Note: yeh reference menu aur tab-naamon se banai gayi hai. Har field ki line-by-line tafseel jab aap screen par chalte hain tab confirm karein; jahan farq mile, batayein.

| Menu | Kaun dekhta hai | Maqsad |
|---|---|---|
| Command Center | saare tenant staff | Aaj ka jaiza: pools, pending kaam, alerts |
| Products & Pools | saare tenant staff | Product catalogue, naya product, naya pool (wizard), pool detail |
| Participants | PM, Maker, Checker, Risk, Auditor | Depositors, accounts, KYC, login linking |
| Daily Operations | + Authorized Signatory | Roz ka kaam (7 tabs) |
| Allocation Engine | operations + Shariah + Signatory | Nafa taqseem: simulator aur runs |
| Investments | operations + Shariah + Signatory | Investment (NAV) pool ka poora nizam |
| Community Circles | operations + Shariah | Committee / rotating savings |
| Shariah Governance | Shariah, Risk, Auditor, PM, Pool Mgr, Signatory | Fatwa, quorum, exceptions, purification |
| Risk & Compliance | operations roles | Asset registry, provisions, exceptions, related-party, risk |
| Finance & Ledger | Maker, Checker, Signatory, Risk, Auditor, Pool Mgr | Journal, GL hand-over, suspense |
| AI & Analytics | Shariah, PM, Risk | Copilot, model governance, anomaly queue |
| Reports | Auditor, Risk, PM, Checker, Board | Auditor portal: trail, evidence |
| Governance Config | Risk, Maker, Checker, PM, Auditor | Approval matrix, account mapping, reserve, rule packs |
| Administration | sirf Superadmin | Users, tenants, audit log |

## Participants
Table: reference, naam, class, accounts, KYC badge, tax status, Login, Action.
- **New participant** (Pool Manager / Maker): reference, naam, class (weightage band se milni chahiye), CNIC/NTN, IBAN, bank, tax status.
- **Add account** (har row): pool, account number (tenant mein unique), opened date.
- **Link login** (sirf Pool Manager): Investor-role user ki email; ek login = ek participant.
- **Verify / Reject** (sirf Risk): KYC faisla. Verify ke baghair balance import nahi.

## Daily Operations (tabs)
1. **Operations Cockpit**: aaj kya baaki hai (imports, closes, runs).
2. **Balance Import**: pool, value date, control total, account-wise balances (CSV/entry). Total na milne par rukta hai.
3. **Income & Expense**: events record (Maker), post (Checker). Posted events hi nafe mein aate hain.
4. **Reconciliation**: bank aur system ka milan; mismatches exceptions banate hain.
5. **Daily Close**: Maker prepare, Checker sign. Signed close ke baghair run nahi.
6. **Period Close & Locking**: mahina band; band period mein tabdeeli nahi.
7. **Payout Clearing Rails (Raast / 1LINK)**: payout batch, gates, authorize, simulate dispatch, ISO pacs.008 download, contra GL.

## Allocation Engine
- **Allocation Simulator**: pool aur date daalein, hisab dekhein (kuch save nahi hota). Real run isi screen/Run Detail se banta hai.
- **Scenario Comparison**: do scenarios ka muqabla (PSR/expense/income farq).
- **Run Detail**: lines, gates, stages (Maker → Checker → Shariah → Signatory), Hiba simulator, restatement, statements.

## Investments (8 tabs)
Pool Dashboard · Investor Onboarding · Capital Accounts · Venture View · Subscription & Redemption · NAV Management · Profit Distribution (4-stage ceremony, signed daily close chahiye) · Model. (Khali system se is poore flow ka end-to-end verification baaki hai.)

## Community Circles (10 tabs)
Circle Setup · Member Roster · Contribution Calendar · Rotation/Draw Room · Rules, Draw & Closure · Payout Release Ceremony · Member Mobile Experience · Hardship & Arrears · Proposals & Voting · Syndicate & Collusion Graph. (Circle roster mein "link login" ka UI abhi nahi; backend maujood hai.)

## Shariah Governance (6 tabs)
Board Workspace · Multi-Mufti Quorum & Fatwa Seal (har member ka vote, quorum progress) · Fatwa Register (list + **Review & sign**) · Exception Cases (quarantine, Board faisla, disclosure) · Purification Ledger · Shariah Audit Plan.

## Risk & Compliance (6 tabs)
Asset Registry (new asset, valuation, transfer requests) · Provisions & Write-offs · Exception Queue · Related-Party · Risk Dashboard (limits, concentration) · Dispute & Request Center.

## Finance & Ledger (4 tabs)
Journal Batches · Income & Expense · GL Hand-over & Trial Balance (export → confirm → TB) · Suspense (named items, ageing, period-close gate).

## AI & Analytics (4 tabs)
Ask (Shariah copilot, citations ke saath) · Documents · Model Governance (kill switch, registry) · AI Anomaly Queue. AI sirf mashwara deta hai; koi faisla/approval nahi.

## Governance Config
Approval Matrix (kaun kis limit tak final release de) · Account Mappings (logical account → GL code) · Reserve Policy · Jurisdiction Rule Packs (`/jurisdiction-rule-packs`). Har tabdeeli *proposal* hoti hai; doosra banda approve karta hai.

## Administration (Superadmin)
Security & Audit Log · Multi-Tenant Configuration · User Administration (naya user, password ek baar) · Jurisdiction & Rule Packs · Website Enquiries.

## Investor / Member
Home par **Investor Portal**: sirf apne accounts, statements (`my-statements`), consent. Circle member ke liye Member Mobile Home.
