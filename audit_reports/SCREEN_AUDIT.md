# Screen Audit (BRD section 15, 58 screens)

## Method and evidence
- **Route / component**: `frontend/src/App.tsx` (routes), `frontend/src/layouts/navItems.ts` (menu by role), page tab lists.
- **Runtime rendering**: the role sweep (`frontend/e2e/role-sweep.spec.ts`) signs in as each of 13 demo users, opens every menu
  entry and clicks every tab (skipping action buttons), and fails on any refused (401/403) API call. Result: **13/13 passed**
  (`evidence/evidence_e2e_roles.txt`). This proves the screen and its tabs load for the roles that see them, without permission errors.
  It does not prove the content is correct.
- **Behaviour**: the Playwright smoke suite exercises specific flows (**29/30 passed**, 1 failed: see SCR-O6 below;
  `evidence/evidence_e2e_smoke.txt`). Create, approve and reject actions are otherwise verified through the API in the backend suite
  (444 passed), not through the browser.
- **Accessibility**: a probe on 8 screens (`evidence/a11y_probe.txt`) counted form controls with no associated label: allocation 3 of 5,
  circles 1 of 1, finance ledger 1 of 1. No WCAG audit was performed. There is no Arabic UI (English and Urdu with RTL only).
- **Responsiveness**: only the public website has a phone-width test (E2E "the website works on a phone"). The application screens
  were not tested at phone width.

Status legend: **WORKING** = renders at runtime and its main actions are verified (E2E or API test); **RENDERS** = renders at runtime;
main actions verified only at API level or not at all; **PARTIAL** = part of the BRD screen is missing; **DEFECT** = verified defect;
**MISSING** = no screen.

## Foundation
| ID | Screen | Route / component | API | Status | Gaps / evidence |
|---|---|---|---|---|---|
| SCR-F1 | Sign in & MFA | `/login`, `/verify-mfa` - `pages/auth/SignIn.tsx` | `auth/login`, `auth/mfa/*` | WORKING | E2E login on every test; MFA enforced only in production settings (`MFA_ENFORCED`); no SSO |
| SCR-F2 | Tenant switcher | `components/TenantSwitcher.tsx` in `TopBar` | `tenants/` | RENDERS | One tenant in demo data; switching not exercised |
| SCR-F3 | Executive command center | `/` - `CommandCenter.tsx` + `RoleDashboard` | `dashboard/home/` | WORKING | E2E "each audience gets its own dashboard"; no growth/forecast/jurisdiction view |
| SCR-F4 | Notifications | `/notifications` - `Notifications.tsx` | `notifications/` | WORKING | E2E bell; role sweep |
| SCR-F5 | User/role administration | `/administration` tab users - `UserAdministration.tsx` | `auth/users/` | RENDERS | Create user via API tests (accounts.tests) |
| SCR-F6 | Jurisdiction rule packs | `/administration` tab rule-packs, `/jurisdiction-rule-packs` - `administration/JurisdictionRulePacks.tsx` | `products/jurisdiction-rule-packs/`, `allocation/reserve-policies/` | DEFECT | Rule pack saved in place with no maker-checker (F-04). The reserve-policy form on this page writes balances directly (F-01). For the super admin the page hides reserve policies; staff reach it only through the `/jurisdiction-rule-packs` route, which is not in any menu |
| SCR-F7 | Approval matrix | `/governance-config` - `GovernanceConfig.tsx` | `accounting/approval-matrix/`, `governance/config-changes/` | WORKING | E2E "governance config shows the maker-checker queue" |

## Product & pool
| ID | Screen | Route / component | API | Status | Gaps / evidence |
|---|---|---|---|---|---|
| SCR-P1 | Product catalogue | `/products-pools` - `ProductCatalogue.tsx`, `NewProductModal.tsx` | `products/products/` | WORKING | E2E "a product states its eligible asset types and participation terms" |
| SCR-P2 | Contract template editor | `/contract-templates` - `ContractTemplateStudio.tsx` | `products/contract-templates/` | RENDERS | No mandatory-parameter check per contract type (R-048) |
| SCR-P3 | New pool wizard | `/pools/new` - `NewPoolWizard.tsx` | `pools/pools/` | WORKING | E2E six steps + identity |
| SCR-P4 | Pool overview | `/pools/:id` - `PoolDetail.tsx` (overview) | `pools/pools/{id}/`, activation readiness | WORKING | Freeze/unfreeze buttons verified at API level (pools.test_lifecycle) |
| SCR-P5 | Pool version comparison | `/pools/:id/versions` - PoolDetail "Version Diff Matrix" | `pools/pools/{id}/versions` | RENDERS | Diff content not asserted in E2E |
| SCR-P6 | Asset eligibility rules | product modal checkboxes (`eligible_asset_types`) | `products/products/` | PARTIAL | Only asset types per product; no sector, concentration, liquidity-buffer or ring-fencing configuration screen |
| SCR-P7 | Asset assignment | PoolDetail "Assets" - `AssignAssetModal.tsx`, `TransferAssetModal.tsx` | `pools/asset-assignments/` | RENDERS | Transfer has no valuation / approval step |
| SCR-P8 | Weightage bands | PoolDetail "Weightage & PSR" - `WeightageBandsSection.tsx` | `allocation/weightage-bands/` | DEFECT | Negative weightage accepted by the API (AT test_16); no maximum-change rule |
| SCR-P9 | PSR / fee setup | `PSRSection.tsx` | `allocation/psr-schedules/` | RENDERS | Approval and notice verified at API level |
| SCR-P10 | Reserve policy | no pool-level screen; form inside `JurisdictionRulePacks.tsx`; read-only summary in `RiskLimitDashboard.tsx` | `allocation/reserve-policies/` | DEFECT | No approval workflow; balance editable (F-01, runtime) |

## Operations & finance
| ID | Screen | Route / component | API | Status | Gaps / evidence |
|---|---|---|---|---|---|
| SCR-O1 | Daily operations cockpit | `/daily-operations` tab cockpit - `DailyOperationsCockpit.tsx` | several | WORKING | E2E finance maker dashboards |
| SCR-O2 | Balance import | tab balance-import | `pools/balance-imports/` | RENDERS | Import rules verified at API level (BalanceImportTests) |
| SCR-O3 | Income/expense workbench | tab income-expense; `/finance-ledger` tab - `IncomeExpenseWorkbench.tsx` | `accounting/income-expense-events/` | RENDERS | Post / approve verified at API level |
| SCR-O4 | Reconciliation center | tab reconciliation - `ReconciliationCenter.tsx` | `accounting/reconciliation-batches/` | RENDERS | No live bank/CBS feed (simulated, refused in production) |
| SCR-O5 | Allocation simulation | `/allocation-engine` - `AllocationSimulator.tsx` | `allocation/allocation-runs/simulate/` | DEFECT | Pool selector is inside the maker-only form; read-only roles get a pool picked by a name heuristic (`AllocationSimulator.tsx:52-65`) and cannot change it (F-10) |
| SCR-O6 | Allocation run detail | `/allocation-runs/:id` - `AllocationRunDetail.tsx` | `allocation/allocation-runs/{id}/` | DEFECT | E2E "allocation ceremony: a pending run waits for the independent checker" **failed**: the checker's run list showed "No allocation runs for this pool yet" because a new draft pool was auto-selected (screenshot `frontend/test-results/smoke-allocation-ceremony-*/test-failed-1.png`) |
| SCR-O7 | Approval ceremony | run detail ceremony stages | check / shariah-sign-off / approve | RENDERS | 4 stages verified at API level; investment-pool distributions have no Shariah stage (F-06) |
| SCR-O8 | Journal batches | `/finance-ledger` tab journal-batches - `JournalBatchReview.tsx` | `accounting/journal-batches/` | RENDERS | GL export is a CSV download with no export status |
| SCR-O9 | Period close | tab period-close - `PeriodCloseManager.tsx` | `pools/period-closes/` | WORKING | E2E period close gates and locked August record |
| SCR-O10 | Restatement wizard | `/allocation-runs/:id/restate` - `RestatementWizard.tsx` | `allocation-runs/{id}/restate/` | RENDERS | Flow verified at API level (RestatementTests) |

## Shariah & risk
| ID | Screen | Route / component | API | Status | Gaps / evidence |
|---|---|---|---|---|---|
| SCR-S1 | Shariah board workspace | `/shariah-governance` tab workspace | `governance/shariah-dashboard/` | RENDERS | |
| SCR-S2 | Decision / fatwa register | tab fatwa-register + quorum ceremony | `products/shariah-decisions/` | RENDERS | Quorum verified at API level (test_quorum) |
| SCR-S3 | Exception case | tab exception-cases, `/exceptions/:id` - `ExceptionCaseDetail.tsx` | `governance/exceptions/` | PARTIAL | No value-quarantine or disclosure step; no SLA |
| SCR-S4 | Purification ledger | tab purification-ledger - `PurificationLedger.tsx` | `governance/purification-entries/` | RENDERS | |
| SCR-S5 | Shariah audit plan | tab audit-plan - `governance/ShariahAuditPlan.tsx` | `governance/shariah-audit-plans/` | RENDERS | Annual report verified at API level |
| SCR-S6 | Risk dashboard | `/risk-compliance` tab risk-dashboard - `RiskLimitDashboard.tsx` | `pools/assets/concentration-risk/` | DEFECT | Limits and the "remediation filing within 90 days" text are hard-coded and labelled as SBP statutory rules (`RiskLimitDashboard.tsx:401`, `pools/concentration_engine.py:21-27`); not from a rule pack and not verified (F-07) |
| SCR-S7 | Limits & breaches | same page, obligor/sector tabs | same | DEFECT | Same hard-coded limits; no breach workflow (record, owner, remediation) |
| SCR-S8 | Related-party review | tab related-party - `RelatedPartyReview.tsx` | `governance/related-party-transactions/` | RENDERS | Workflow verified at API level |

## Investment & community
| ID | Screen | Route / component | API | Status | Gaps / evidence |
|---|---|---|---|---|---|
| SCR-I1 | Investor onboarding | `/investments` tab onboarding | `investments/investor-profiles/`, disclosures | WORKING | E2E "investment onboarding spec comes from recorded terms" |
| SCR-I2 | Investor portfolio | tab dashboard / accounts | `investments/capital-accounts/` | RENDERS | |
| SCR-I3 | Subscription / redemption | tab orders | subscriptions / redemptions | WORKING | E2E investor redemption request |
| SCR-I4 | Musharakah capital accounts | tab venture-view, `/investments/capital-accounts/:id` | capital accounts | RENDERS | |
| SCR-C1 | Community circle setup | `/community-circles` tab setup | `circles/rules/` | WORKING | E2E circle tabs render real data |
| SCR-C2 | Member roster | tab roster | `circles/circle-members/` | RENDERS | |
| SCR-C3 | Contribution calendar | tab calendar | `circles/contributions/` | RENDERS | |
| SCR-C4 | Rotation / draw room | tab draw - `components/circles/DrawRoomConsole.tsx` | `circle-members/execute-provably-fair-draw/` | DEFECT | The console's "provably fair" draw commits and reveals in one request, so the seed commitment is never published before the client seed (`circles/rotation.py:111-114`); the turn-swap form is pre-filled with an invented reason ("Urgent family medical emergency advancement", `DrawRoomConsole.tsx:47-49`) |
| SCR-C5 | Payout release | tab payout | `circles/payouts/` | WORKING | E2E payout ceremony shows first cycle settled |
| SCR-C6 | Hardship & arrears | tab arrears | `circles/arrears-records/` | RENDERS | |

## AI & assurance
| ID | Screen | Route / component | API | Status | Gaps / evidence |
|---|---|---|---|---|---|
| SCR-A1 | AI copilot | `/ai-analytics` tab ask - `ShariahCopilot.tsx` | `ai/shariah-copilot/*` | BLOCKED | Copilot service not running: documents call returns 503 (role matrix). Graceful message only |
| SCR-A2 | Anomaly queue | tab anomalies - `governance/AIAnomalyQueue.tsx` | `governance/exceptions/` | RENDERS | |
| SCR-A3 | Scenario simulator | `/allocation-engine` tab scenarios - `ScenarioSimulator.tsx` | simulate | RENDERS | |
| SCR-A4 | Liquidity forecast | PoolDetail - `pool-detail/LiquidityForecastSection.tsx` | `pools/pools/{id}/liquidity-forecast/` | RENDERS | Forecast verified at API level |
| SCR-A5 | Model governance | tab models - `ModelGovernance.tsx` | `ai/models/`, recommendations | RENDERS | |
| SCR-A6 | Auditor portal | `/reports` - `AuditorPortal.tsx` | audit log, sampling | WORKING | E2E auditor builds period report, verifies chain |
| SCR-A7 | Evidence bundle builder | `/reports` tab evidence-bundle | `core/evidence-bundle/*` | WORKING | Same E2E |

## Self-service
| ID | Screen | Route / component | API | Status | Gaps / evidence |
|---|---|---|---|---|---|
| SCR-SS1 | Depositor statement | `/statements/:id`, portal - `StatementView.tsx` | `my-statements/` | WORKING | E2E investor portal |
| SCR-SS2 | Investor statement | portal, capital account detail | capital accounts | WORKING | E2E investor with capital account |
| SCR-SS3 | Member mobile home | `/circles/members/:id`, portal "My savings circles" | `my-circles/` | WORKING | E2E member signs in, sees own circle |
| SCR-SS4 | Contribution receipt | `/circles/contributions/:id/receipt` | contributions | WORKING | E2E member ledger and receipt |
| SCR-SS5 | Vote / consent | portal `CircleVoting.tsx`, consents | `cast-vote/`, `consents/` | WORKING | E2E member votes; consent download |
| SCR-SS6 | Dispute / request center | portal `MyRequests.tsx`, staff `DisputeCenter.tsx` | `governance/support-requests/` | WORKING | E2E member raises a request |

## Totals (58 screens)

| Status | Count |
|---|---|
| WORKING | 21 |
| RENDERS | 26 |
| PARTIAL | 2 |
| DEFECT | 8 |
| BLOCKED | 1 |
| MISSING | 0 |

No BRD screen is entirely absent. 47 of 58 render without permission errors and have no verified defect. 21 also have browser-verified behaviour.

## Cross-cutting UI findings
1. Header badges "LIVE CONTROLS" (pulsing green dot) and "AI COPILOT" appear on every page whatever the state (`components/PageHeaderBadges.tsx`). The modal behind them reads real data. The pulse suggests a live status that is not measured. P3.
2. Demo users carry realistic personal names (for example the checker shown as "Amina Malik (Demo Checker)"). They are synthetic, but they read as real people. P3.
3. Form labels are not linked to their inputs on several screens (accessibility probe). P2.
