# Amanah Pool OS - Full Audit Report

Date: 2026-10-11. Scope: whole repository (backend Django/DRF, frontend React/TS, seed data) against the BRD.

**How the findings were checked.** Code was read file by file. Every permission finding marked *confirmed* was reproduced with temporary API probes against a freshly seeded tenant (removed afterwards). They used the least-privileged role, `investor_member`, unless another role is named. Items marked *needs expert confirmation* are regulatory or Shariah interpretations that the code hard-codes and that a compliance or Shariah advisor must verify. The automated test suite (341 tests) passes, but it does not cover most of what is listed here.

Severity:
- **P0** is a security hole, lost financial control, or a false or defamatory statement presented as fact. Fix before anyone outside the team sees the system.
- **P1** is fake, hard-coded or misleading data shown as real, or a functional bug.
- **P2** is quality, consistency or minor.

---

## 1. P0 - Critical

### 1.1 Role checks missing on many write endpoints (confirmed)

Many viewsets fall back to `IsAuthenticated` for update, delete or custom actions, so any logged-in user of the tenant can change financial and governance data. An investor could:

| What an investor did | Endpoint | Result |
|---|---|---|
| Deleted an **approved** PSR and an approved weightage band | `DELETE allocation/psr-schedules/{id}`, `weightage-bands/{id}` | 204 |
| Changed a circle member's **IBAN** (payout diversion) | `PATCH circles/circle-members/{id}` | 200 |
| Swapped two members' payout turns | `POST circles/circle-members/swap-turns/{pool}` | 200 |
| Voted on a circle proposal **as another member** | `POST circles/circle-proposals/{id}/vote` | 201 |
| Locked, certified and auto-verified a period close, then deleted it | `POST period-close/{id}/lock`, `/certify`, `DELETE` | 200 / 204 |
| Approved and deleted a Shariah audit plan | `POST shariah-audit-plans/{id}/approve`, `DELETE` | 200 / 204 |
| Renamed or edited pools, products and Shariah-approved contract templates | `PATCH pools/{id}`, `products/{id}`, `contract-templates/{id}` | 200 |
| Deleted assets, asset assignments, related-party transactions, reconciliation batches | `DELETE ...` | 204 |
| Passed the permission check on asset transfer (introduced by me) | `POST asset-assignments/{id}/transfer` | 400 (validation only) |
| Ran the AI hardship and collusion engines | `ai/circles/{id}/predict-hardship`, `ai/fraud-collusion/detect` | 200 |

Other roles, also confirmed:
- A **pool manager** edited an approved PSR to 10/90 and an approved weightage band. Status stayed `approved`, there was no re-approval and no BR-003 notice, and the sealed pool version became stale.
- An **auditor** moved a capital account to another pool and renamed it. `pool` and `participant` are writable, and update falls back to `IsAuthenticated`.

Data exposure: an investor can list all users with emails and roles (`auth/users`), all circle members with IBAN and email, contributions, income/expense events, journal batches, exceptions, support requests, reconciliation and related-party data. Only `core/audit-log` returned 403.

Root causes:
- `ModelViewSet` without `http_method_names`.
- `get_permissions()` returns `[IsAuthenticated()]` as the default branch.
- Classes with `permission_classes = [IsAuthenticated]` and no per-action rules: `ReconciliationBatchViewSet`, `PeriodCloseChecklistViewSet`, `ShariahAuditPlanViewSet`, `ShariahAuditFindingViewSet`, `SupportRequestViewSet` (list), `CircleProposalViewSet`.
- Querysets not scoped by owner for investors.
- The frontend has no role-based route or menu guard: `ProtectedRoute` only checks login.

### 1.2 Period close can be unlocked or forged (confirmed)

Files: `backend/apps/pools/views.py` (`PeriodCloseChecklistViewSet`) and `backend/apps/pools/period_close_engine.py`.

- `status`, `certified_by`, `certified_at` and `checklist_data` are writable through PATCH or create. Any user can set a locked period back to `open`, which defeats `period_lock`, or create a period already "locked" or "certified".
- `perform_create` sets all five gates to `True` when no checklist is sent.
- `certify` and `lock` check no gate, no state and no role. `lock_ceremony` says it validates the gates, but it does not, and it does not require `certified`.
- Sign-off: anyone can sign as `shariah_reviewer` or `cfo_checker`, one user can sign all three roles, and certification happens without the pool-manager sign-off.
- Gate 1 is `... or True`. Gate 2 passes if the pool has any product. Gate 5 copies Gate 4 and never looks at journals.
- Signatory names fall back to "Authorized Official" and "Chief Compliance Officer", because `get_full_name()` is empty for this User model.
- The certificate text claims compliance with SBP Prudential Regulations and AAOIFI FAS-30. The provisional certificate uses any run, not a signed one.
- The same viewset is registered twice, as `period-close` and `period-closes`.

### 1.3 One person can approve a fatwa (Shariah quorum)

File: `backend/apps/products/views.py` `cast_quorum_vote` and `frontend/src/components/governance/ShariahQuorumCeremony.tsx`.

- One logged-in Shariah Board user types any `scholar_name`. Two "approve" rows under two names auto-approve the decision.
- The maker ≠ checker rule enforced in `approve` is skipped on this path, so the drafter can approve their own decision.
- `digital_signature_hash` is a SHA-256 of a string, not a signature.
- The UI pre-lists **real, named scholars** (Mufti Muhammad Taqi Usmani as Chairman, Mufti Najeeb Khan, Mufti Hassan Kaleem; presets also include Mufti Zubair Usmani and Dr. Imran Ashraf Usmani). It pre-fills an Arabic approval text in their name.
- The UI label says "SBP 2/3 Super-Majority", but the code requires exactly two approvals regardless of board size.
- An **approved** Shariah decision can still be edited, because `perform_update` has no status check. An approved fatwa can therefore be changed silently.

### 1.4 Fabricated accusations by the "AI fraud & collusion" engine

File: `backend/apps/ai_agents/services/collusion_detector.py`, shown in `FraudCollusionGraphView.tsx`.

- It invents CNIC prefixes, home addresses and bank branches from an MD5 hash of each member reference.
- It always marks the first three members as a "CRITICAL circular cross-guarantee ring". The system has no guarantee data.
- It groups members by the invented addresses as an "undisclosed related-party cluster" and recommends freezing their payouts.
- It writes an "SBP & FIA anti-money-laundering investigation dossier" that cites unverified references (BPRD Circular 04/2017, AAOIFI Std 57, Form AML-04).
- Any user can run it. This produces false, defamatory statements about real people.
- The "Place Risk Hold on Payout" button only shows `alert()`. Nothing is held or recorded.

### 1.5 Simulator writes fake balances into real ledger data

File: `backend/apps/pools/cbs_daemon.py`, endpoint `pools/balance-imports/cbs-sftp-daemon/`.

- The "SFTP daemon" is fully simulated: hard-coded balances of 25.0M, 40.25M, 26.0M and 29.0M, fake IBANs and branch codes.
- It still writes them as **real `DailyBalance` rows** (`source=API`, `status=VALIDATED`) for any pool without participant accounts. Those rows feed profit allocation.
- An invalid `value_date` gives a 500 error.

### 1.6 Circle contributions can be duplicated or negative, which inflates payouts (confirmed)

File: `backend/apps/circles/views.py` `record_contribution`.

- The same member and cycle can be recorded any number of times. The payout pre-flight sums every row, so the payout amount is inflated.
- A negative amount (−500) was accepted.
- There is no check against `CircleRules.contribution_amount`, member status or period lock. No bank evidence is recorded, yet the status is `RECEIVED`.
- The frontend records **every** contribution as cycle 1 (`CommunityCircles.tsx` lines 296 and 1078).
- The "Pay via Raast" mobile mock records a real PKR 50,000 contribution for whichever member is first in the list, after a *simulated* settlement. Fake IBANs are used and errors are swallowed.

### 1.7 Circle democracy is not bound to members

- A vote is not tied to the voter's identity. Staff, or anyone, can vote "as" any member. The frontend always votes as `members[0]`.
- There is no deadline check and no quorum. A proposal can be closed before its deadline, and one approve against zero rejects counts as approved.
- "Flag arrears" is offered only for the first member (`members.slice(0, 1)`).

### 1.8 Authentication

- `MFA_ENFORCED` defaults to `False`.
- **MFA bypass:** `MfaSetupView` returns the *existing* TOTP secret to anyone holding a pending token, even after MFA is enabled. Anyone who knows the password can obtain the second factor.
- There is no throttling or lockout on login or MFA verify, so the 6-digit code can be brute-forced. TOTP codes can be replayed.
- Refresh tokens are not rotated and there is no blacklist, so logout does not invalidate them.

### 1.9 Real public figures in seed data and UI

- Seed users are named "Sheikh Dr. Yusuf Al-Qaradawi" (Shariah Board) and "Maryam Nawaz" (product manager).
- The quorum UI lists real Pakistani scholars as board members who "vote".
- The concentration engine lists real companies (Engro, Master Motors, WAPDA, Government of Pakistan) with **invented credit ratings**.

---

## 2. P1 - Fake, hard-coded or misleading data shown as real

### 2.1 Dashboards

- **`InvestmentPools.tsx` dashboard**
  - Total funds is the sum of every subscription ever, across all pools, not net of redemptions. When there is no data it falls back to **PKR 18.42 billion**.
  - Period profit adds every allocation run, including simulated and unsigned runs. Without runs it shows funds × 0.01165.
  - Delta "+4.1%" and liquidity buffer "18.2%" are constants.
  - Per-pool funds are hard-coded by seed code: POOL-GEN-01 = 8.7B, POOL-CORP-03 = 3.2B, POOL-TREAS-02 = 5.58B, others = 24.8M, circles = 50,000.
  - Per-pool yields are hard-coded (11.82 / 14.10 / 12.45 / 10.50%).
  - "Shariah approvals pending" actually shows the open-exceptions count.
  - Reconciliation health is computed as `100 - n × 0.06`.
  - Venture view "Est. share of profit" uses a fixed 14.1% annual rate.
- **`ShariahGovernance.tsx` workspace:** the same hard-coded funds, yields, profit formula, "+4.1%" and "18.2%".
- **`DailyOperationsCockpit.tsx`:**
  - "Operational health" is 100% / 99.98% / `100 - n × 0.15`.
  - "Close readiness" means a pool has any balance import, not that its period is closed.
  - Tabs are switched by clicking DOM buttons found by text.
- **`CommandCenter.tsx`:**
  - Pools are classified as Mudarabah / Musharakah / Wakalah by name keywords, not by contract type.
  - The profit trend includes simulated and pending runs.
- **`JournalBatchReview.tsx`:** "MATCHED 100.00%" and "VARIANCE PKR 0.00" are constants.
- **`UserAdministration.tsx`:** "4-EYES PRINCIPLE enforced" and "MFA enforcement" are static claims. Sections 1.1 and 1.8 show they are not true.

### 2.2 Screens that claim facts never computed

- **Investment onboarding six-step "Specification"** (`InvestmentPools.tsx` lines 1047–1304). Almost every value is invented:
  - "Diminishing Musharakah" for every investment pool, contract archetype always "Unrestricted Mudarabah", PSR "70/30".
  - Yields "11.82%–14.10%", "10% incentive over 12% hurdle", "16:00 PKT NAV cut-off", "18.2% statutory liquidity reserve".
  - "SBD-2026-044 approved by Board", "AAOIFI verified semi-annual audit", "100% real-time AML screening via CBS".
  - "Disclosure complete & delivered to all account holders", "Fully operational & accepting capital".
  - The "AI configuration check" banner is static text.
- **Community circle setup six phases** (`CommunityCircles.tsx` lines 464–831):
  - Hard-coded tenant name, "FATWA-2025-01", PKR 10,000 per cycle, escrow IBAN, "Kafalah guarantee", "multi-sig", "4 of 5 quorum", "60-day pause".
  - "100% KYC verified" (never checked) and "Verified by Shariah Board".
  - These now contradict the real circle rules feature.
- **Contribution calendar:** fully static ("SEPTEMBER 2026", fixed DUE and PAID days).
- **Member mobile tab:** static PKR 50,000, "Position #1", "Next payout 12 Sep".
- **Roster control totals:** "100% / Balanced PASS" are constants.
- **"Verify & E-Sign KYC":** no e-signature exists. The verify call also overwrites the maker's suitability notes with the boilerplate "KYC verified in accordance with SBP AML/CFT guidelines".
- **`SecurityAuditLog.tsx` "Verify chain integrity":** only sets a local flag and never calls the backend, then shows "SHA-256 chain verified".
- **`MerkleChainVerifier.tsx`:** shows "100% cryptographic integrity verified" after every load, even when the backend returns `verified=false`.
- **`AiCopilotDrawer.tsx` "AI Shariah Copilot – Live Engine":** not AI. It gives canned keyword replies after a 600 ms timer, with invented references.
- **`AuditorPortal.tsx`:** a self-awarded badge "BRD Section 9 & 12 Compliant".

### 2.3 Backend "engines" producing invented output

- **`audit_sampler.py`**
  - Issues an "SBP compliance opinion" (CLEAN to ADVERSE), "AI Sampling Agent v2.4", "Operating Year 2026".
  - Claims "95% statistical confidence", but the scores are fixed constants.
  - Checks a non-existent field `restated_from`.
- **`hardship_predictor.py`**
  - Fixed points (12 / +35 / +40 / +15), yet the UI calls it "predictive machine learning".
  - Warning texts ("payment deceleration", "early position") do not depend on the actual cause.
- **`concentration_engine.py`**
  - Assets have no obligor, sector or rating data, so these are hard-coded or guessed from keywords.
  - "SBP PR R-1/R-6" limits are applied as a percentage of pool assets. *Needs expert confirmation:* prudential limits are normally measured against the bank's equity, and the regulation numbers and limits in the code are unverified.
  - The AAOIFI prohibited-sector check is hard-coded to pass.
  - The remediation memo invents steps such as "File Form BPRD-PR1" and "lock 100 bps".
  - The stress test is not meaningful, and its `credit_downgrade_shocks` parameter is unused.
- **`hiba_simulator.py`**
  - KIBOR fixed at 17.50% (the jurisdiction switcher says 18.50%). Uses a 30-day period and a default 25% hiba.
  - The Shariah checklist always passes. The memo claims Shariah Board certification.
  - The hiba is not recorded in the run's `config_snapshot`. A finance checker can apply a hiba and then check the same run.
  - The run still ties out, which I verified with a test.
- **`ReconciliationBatch` "auto-match"** sets matched = total and variance = 0 without matching anything. "Clear variance" needs no reason and no role.
- **`reconciliation.check_reconciliation`** compares cumulative depositor-payable credits (profit) with the latest daily balance (deposits). The percentage means nothing and creates junk exception cases after most runs.
- **`payout_clearing_engine.py`**
  - WHT is hard-coded at 15% for filers and 30% for non-filers. *Needs expert confirmation:* rates change with each Finance Act and should come from a dated table.
  - Zakat of 2.5% is taken from every profit payout. *Needs expert confirmation:* Pakistani Zakat is normally deducted from the balance on the 1st Ramadan valuation date.
  - Gate 3 only checks the rate it has just applied.
  - Clearing latencies and RRNs are random.
- **`banking_switch.py`** picks a random sending bank "for realism". The receipt is labelled as a simulation, which is fine, but callers record real business events on top of it.

### 2.4 Jurisdiction switcher and rule packs

- **`RegulatoryJurisdictionSwitcher.tsx`, shown as the tenant switcher:**
  - Four hard-coded jurisdictions with invented legal entities ("Amanah Islamic Bank PJSC – Dubai DIFC", "Al-Amanah Financial Services Ltd – Riyadh").
  - Their tenants (`DUBAI-DEMO`, `RIYADH-DEMO`) do not exist.
  - Benchmark rates and guardrails are hard-coded.
  - Switching writes another tenant code to local storage and reloads, after which every API call is rejected.
- **Rule packs:** `mudarib_share_cap_pct`, `per_ceiling_pct` and `irr_ceiling_pct` are stored and displayed but **enforced nowhere**. Only `notice_period_days` is used. The UI shows invented fallback values when they are missing, plus a "100% SBP / AAOIFI" stat.

### 2.5 Functional bugs

- The Shariah dashboard lists **approved** pools as "pending pool approvals". It should use `pending_approval`.
- Income-event `reclassify` and `scan-overhead-leakage` return **500** on posted events: the model's Django `ValidationError` is not converted. Both are also open to any user.
- Deleting a pool, product or template returns 500 (`ProtectedError`) instead of 403 or 405.
- Shariah audit plans and findings have no role checks and no audit log, approve has no state check, and `findings_count` is not reduced when a finding is deleted.
- Support requests: every user, including investors, sees every dispute in the tenant.
- `seed_project_data --reset` is `store_true` with `default=True`, so reset can never be turned off. The command runs in any environment and wipes the named tenant.
- Investor onboarding creates the account and the KYC profile in two separate calls. If the second fails, an orphan account is left.
- "+ New Subscription Order" and "+ New Redemption Order" always use the first account; the user cannot choose.
- The frontend lets `pool_manager` press **Subscribe**, but the backend allows only `finance_maker`.
- The redemption modal still says "Execute Redemption" although it now only creates a request.
- Impairment approval writes units down but posts no journal and does not update NAV.
- `PeriodCloseManager.tsx`:
  - The "automated" gates can be ticked by hand.
  - All sign-off buttons are shown to every role.
  - Defaults: fatwa reference "FATWA-2026-M09-001" and a lock note claiming "locked under SBP PR rules".
- `RiskLimitDashboard.tsx`:
  - The 15% single-obligor gauge is applied even when the top obligor is sovereign.
  - "Cash & sovereign buffer" is actually the sovereign-sector share.
  - "Reserve cushion" divides all pools' reserves by one pool's assets.
- `DrawRoomConsole.tsx` uses `Math.random()` as the "member" seed. The real member-supplied seed is in the new Rules/Draw tab.
- Hard-coded demo defaults remain in many forms (dates 2026-09-01, 2026-09-03, 2026-10-15, amounts 10,000 and 50,000), and default pools are picked by seed code.

---

## 3. P2 - Quality

- The frontend keeps tokens in `localStorage`, which XSS can read. There is no CSP.
- `alert()` and `console.error` are used instead of in-app errors in several places.
- The contract analyzer sends contract text as a "question" to the RAG endpoint, which leaves room for prompt injection. It trusts the model's own confidence score, and its fallback flags any use of the word "interest".
- Copy errors: "Enter the 6-digit code **sent to your device**" (TOTP is not sent), "Unrestricted Mudarabah" labels, and others.

---

## 4. Features not required by the BRD, as far as my BRD reading goes

These add risk because they present simulations or invented regulatory content as product features:
- The multi-country jurisdiction switcher (UAE / KSA / AAOIFI).
- The CBS SFTP daemon simulator.
- The Raast / 1LINK switch simulator, the pacs.008 XML and the clearing "edge-case injection".
- The fraud and collusion graph and the hardship "ML" forecaster.
- The SBP concentration cockpit and remediation memos.
- The Merkle "tamper simulation".
- The phone-frame mobile mock-ups.

Some could become real features, but today they are demos. Either label them as demos or remove them.

---

## 5. Correction to my earlier reports

My `docs/BRD_COVERAGE.md` and the progress figures (about 91% functionality, 71% production-ready) did not take this audit into account.

- BR-010 tenant isolation holds **between** tenants. Role-based access **inside** a tenant is broken (section 1.1).
- Several items I marked "Done" are undermined:
  - The maker-checker on PSR, weightage and approvals can be bypassed by editing approved records directly.
  - BR-008 payouts can be inflated through duplicate contributions.
  - The period lock can be undone.

My corrected estimate is about **75–78%** functional and about **45–50%** production-ready until sections 1 and 2 are fixed.

---

## 6. Recommended fix order

1. **Access control (1–2 days).**
   - Give every viewset explicit per-action roles and deny by default.
   - Remove delete, or set `http_method_names`.
   - Make approved PSR, weightage, product, template, Shariah decision and pool records immutable (changes go through versioning or ConfigChangeRequest).
   - Scope investor querysets.
   - Add a permission test matrix covering every endpoint and role.
2. **Period close (1 day).** Make status fields read-only, enforce state transitions, compute gates server-side, bind roles to sign-offs with separate users, and check gates on lock.
3. **Shariah quorum (1 day).** Bind each vote to a distinct logged-in Board user, apply the maker-checker rule, make the quorum size configurable, remove the real scholars' names, and make approved decisions immutable.
4. **Circles (1 day).**
   - Contributions unique per member and cycle, positive amount equal to the rule amount, and evidence recorded.
   - Cycle chosen by the user.
   - Votes bound to the member's user, with deadline and quorum enforced.
   - Remove the fake mobile "Pay" flow.
5. **Remove fabricated content (2–3 days).**
   - Collusion engine: remove it, or rebuild it on real data with "indicative only" wording.
   - CBS daemon must not write `DailyBalance`.
   - Hard-coded dashboard figures, the onboarding and setup spec panels, the calendar, the fake copilot drawer and the fake verify buttons: remove them, or wire them to real data.
   - Real people's names in seed data and UI.
6. **Auth (½ day).** MFA setup only before enrolment, throttling and lockout, refresh rotation and blacklist, MFA on by default outside development.
7. **Expert decisions.** WHT and Zakat treatment, concentration-limit basis, and enforcement of the rule-pack caps.

---

## 7. Fix tracker

### 2026-10-11 - all P0 items fixed

Verification: backend 357 tests pass and the frontend type-check is clean. The new regression suites are:
- `apps/core/test_access_control.py` replays the audit's probes with real JWTs.
- `apps/pools/test_period_close.py`
- `apps/products/test_quorum.py`
- `apps/ai_agents/test_collusion_indicators.py`
- The updated circle tests.

| Item | Status | What changed |
|---|---|---|
| 1.1 Role checks / data exposure | **Fixed** | Investors are refused every endpoint outside a self-service allow-list (`accounts/investor_scope.py`, enforced in JWT auth). Every write path has explicit roles. There is no hard delete on governed records. Approved PSR, weightage, pool, product, template, rule-pack, audit-plan and related-party records can no longer be edited in place (`EditableWhileDraftMixin`). A capital account's pool and owner are fixed once it exists. Model-guard errors now return 400 and protected deletes 409, not 500. The rule-pack permission referenced non-existent roles; that is corrected. Frontend: new investor portal page, role-filtered sidebar, route guard. |
| 1.2 Period close | **Fixed** | Status, gates and certification are read-only to clients, and no update or delete is possible. Gates are computed from records per pool model (no `or True`; the journal gate checks the run's balanced batch). Sign-offs are role-bound, need three different people with the pool manager first, and require a ruling reference from the Shariah reviewer. Lock needs certification, re-checks the gates, and only a finance checker or authorized signatory can do it. The certificate is now a factual internal record. The duplicate route is removed. Frontend gates are display-only. |
| 1.3 Shariah quorum | **Fixed** | A vote is the logged-in Board member's own, with the name taken from the login. One vote per member, reasons required, and the drafter cannot vote. Approval needs two thirds of the active board, and at least 2 members. Approved rulings cannot be edited or deleted. The real scholars' names are removed from the UI. |
| 1.4 Collusion engine | **Fixed** | Rebuilt on recorded data only: shared IBAN, shared e-mail, and overdue after payout. It shows indicators with a disclaimer; no invented identities, rings or AML dossier, and the fake "risk hold" is removed. Limited to Risk & Compliance and auditors. |
| 1.5 CBS simulator | **Fixed** | Preview only. It no longer writes DailyBalance rows, import batches or exception cases. |
| 1.6 Contributions | **Fixed** | One per member and cycle (DB constraint), amount must be positive and equal to the circle rules, the cycle must be in range, a bank/Raast reference is required, the period lock applies, and duplicate arrears are refused. Frontend: the user enters the cycle and reference; the fake mobile "Pay" flow is removed. |
| 1.7 Circle votes | **Fixed (staff-recorded)** | A vote is recorded by the organizer or compliance per selected member, with method and evidence. There is a deadline. Close requires the deadline to have passed or every member to have voted, and needs a >50% turnout. Members still have no logins of their own. |
| 1.8 Authentication | **Fixed** | The MFA secret is never re-issued after enrolment. Login and MFA are throttled (`AUTH_THROTTLE_RATE`). Refresh tokens rotate and are blacklisted, and there is a logout endpoint. MFA is on by default in production settings. |
| 1.9 Real people | **Fixed** | Seed users have invented demo names; each tenant has its own e-mail domain (seeding a second tenant no longer moves the first tenant's users); two more Board members were added so a quorum is possible. Real companies and invented ratings are removed from the concentration engine. The hard-coded "Chairman" name in the sidebar is replaced by the signed-in user. |

P1 items also fixed in this pass:
- The reconciliation check now compares the GL with the participant sub-ledger, so there are no more junk exceptions.
- Reconciliation "auto-match" now records real counts, and clearing a variance needs notes and a different person.
- The Shariah dashboard pending-approval queue is correct.
- The seed command's `--reset` can be turned off and is refused outside DEBUG.
- The prohibited-sector check now says "not assessed" instead of a hard-coded pass.

**Still open (P1/P2):**
- The hard-coded dashboard figures and the onboarding and setup "spec" panels.
- The static contribution calendar.
- The fake copilot drawer.
- The `SecurityAuditLog` and `MerkleChainVerifier` verify banners.
- The audit-sampler and hiba texts.
- The jurisdiction switcher.
- Rule-pack cap enforcement.
- WHT and Zakat treatment (needs an expert decision).
- The remaining items in section 2.


### 2026-10-12 - P1 pass (fake / hard-coded displays)

Verification: backend 362 tests pass and the frontend type-check is clean.

| Item | Status |
|---|---|
| Hard-coded funds / yield / "+4.1%" / "18.2%" / fake reconciliation rate on the Investments and Shariah dashboards | **Fixed.** New `GET /pools/pools/portfolio-summary/` computes funds (balances / published NAV / circle collections net of payouts), the latest *signed* profit and an annualised yield per pool; a figure that cannot be computed is null and shown as "-". Pools are no longer chosen by seed code. |
| Investment onboarding "specification" panels (6 steps) | **Fixed.** Rebuilt from the recorded terms (`disclosures/preview`), NAV, disclosure and exceptions; unknown values read "not recorded"; the static "AI configuration check" banner is gone. |
| Circle setup phases, contribution calendar, member "mobile" mock-ups, roster control totals | **Fixed.** Setup shows the published rules, members, collections and gaps; the calendar is now a real contribution ledger by cycle; the mock phones are replaced by links to each member's own view; control totals are real counts. Only real circle pools are listed. |
| Copilot drawer | **Fixed.** It now calls the Shariah Policy Copilot service with citations and a disclaimer, and reports an outage instead of inventing a reply. Restricted to the allowed roles. |
| "Verify chain" and Merkle banners | **Fixed.** Both call the backend verification and show a failure when tampering is detected. |
| Daily Operations "operational health" and Journal Batch control bar | **Fixed.** Replaced with counts computed from the data. |
| Jurisdiction switcher | **Fixed.** Removed (it sent users to tenants that do not exist); the top bar shows the user's own tenant. |
| Rule-pack caps | **Partly fixed.** A PSR above the pack's `mudarib_share_cap_pct` is refused. PER/IRR ceilings are not enforced yet because their basis (profit vs. funds) needs a decision. |
| Concentration engine and collusion indicators | Fixed in the P0 pass. |

**Still open:** the audit-sampler and Hiba memo wording, WHT and Zakat treatment (needs an expert), PER/IRR ceiling basis, and the P2 items.


### 2026-10-12 (later) - wording and reporting

- **Audit sampler:** no longer issues an "SBP compliance opinion", a "95% statistical confidence" claim or an "AI Sampling Agent v2.4" label. It is a rule-based ranking of items to inspect, stated as such in the API, the working note and the UI. The restatement check now uses the real fields.
- **Hiba simulator:** the memo is marked as a simulation draft, not a Board resolution; the always-true Shariah checklist entries were reworded to what the system actually does.
- **New - periodic pool report** (`GET /core/period-report/?start&end`, CSV via `export=csv`, "Period Report" tab in the auditor portal): one row per pool from recorded data only (closing funds, signed-run profit and shares, reserve transfers, subscriptions / redemptions, circle contributions and payouts, exceptions, non-permissible income, journal balance, period-close status). A figure with no source is blank, not zero. The report is sealed with a content hash and every run is audited. Roles: auditor, risk & compliance, pool manager, finance checker, Shariah Board / Secretariat. It is an internal management report, not a regulatory filing.

### 2026-10-12 (later) - end-to-end tests

`frontend/e2e/smoke.spec.ts` (Playwright, `npm run e2e`) drives the real UI against the real backend: 9 tests that all pass. They check that the dashboards and onboarding panels show recorded data and none of the old hard-coded text, the circle tabs, the investor-only portal (and the redirect away from staff pages), the maker-checker queue, the period report, the display-only period-close gates, an investor's own capital account with its acknowledged disclosure, and that a bank pool's yield is plausible. Screenshots of the screens found three real issues that the API tests had missed, all fixed:
- The demo bank pool showed a 50% annual yield because the seeded income was about four times too large; the seed now uses realistic income.
- The seeded disclosure was published before the profit-sharing ratio existed, so the demo investor appeared "not cleared"; it is now published after.
- The demo investor logins did not all have an account; the e2e covers the one that does.

Setup: start the backend (`migrate`, `seed_project_data`, `runserver`) and the frontend (`npm run dev`), then `npm run e2e`.

### 2026-10-12 (later) - screen-by-screen visual review

I looked at screenshots of 17 screens as different roles. Besides the three issues above, the review found and fixed:
- **Seed bypassed the period-close controls.** It wrote a LOCKED August period with all gates "true" directly. The seed now creates the periods empty and drives them through the real workflow (computed gates, three role sign-offs, lock by an authorized signatory); September stays open with its real gate results.
- **Governance Config showed "You do not have permission" to finance makers** because the approval-matrix list excluded them; makers can now read it.
- **Contradictory exception counts** ("0 open exceptions" next to "2 high / critical"): the high/critical count included resolved exceptions; it now counts open ones only. The Shariah "AI alerts" badge was relabelled to what it counts.
- **Command Center** classified pools into Mudarabah / Musharakah / Wakalah by their *names*; it now uses the contract type.
- **Daily Operations** showed funds from only one pool's last import (99.99M); it now uses the same portfolio summary as the other dashboards. Its "SFTP daemon active" banner now says it is a preview that writes nothing.
- Period Close page text no longer cites "SBP Prudential Regulations" or the "Resident Shariah Board Member / CFO"; it describes what the system does. Asset face values are formatted. "100% Balanced" static text removed.

E2E: 12 Playwright tests pass (run twice). Note that login is rate limited; for local E2E runs start the backend with `AUTH_THROTTLE_RATE=1000/min`.
