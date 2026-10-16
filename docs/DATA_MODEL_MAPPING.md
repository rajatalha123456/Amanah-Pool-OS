# BRD Section 11 entities and where they live

The BRD data model is logical. This table names the model (Django app `backend/apps/<app>/models.py`) that holds each
entity, so an auditor or a new developer can find it. Where one BRD entity is split or named differently, the reason is
given.

| BRD domain | BRD entity | Model(s) | Note |
|---|---|---|---|
| Foundation | Tenant | `tenants.Tenant` | |
| | LegalEntity | `tenants.LegalEntity` | jurisdiction, base currency, timezone |
| | JurisdictionRulePack | `products.JurisdictionRulePack`, `RulePackRevision` | every approved change is a sealed revision |
| | User | `accounts.User` | |
| | Role | `accounts.UserRole` (choices on the user) | one role per login, by design (segregation of duties) |
| | ApprovalMatrix | `accounts.ApprovalMatrixRule` | |
| Product & governance | Product | `products.Product` | |
| | ContractTemplate | `products.ContractTemplate` | mandatory parameters per contract type |
| | ShariahDecision | `products.ShariahDecision`, `ShariahQuorumVote` | votes per review round |
| | Pool | `pools.Pool` | |
| | PoolVersion | `pools.PoolVersion` | sealed configuration snapshot |
| Participation | Participant | `participants.Participant`, `ParticipantAccount` | individuals (KYC) and companies (KYB) |
| | Member | `circles.CircleMember` | a member of a community circle |
| | CapitalAccount | `investments.CapitalAccount`, `UnitMovement` | |
| | Subscription | `investments.Subscription`, `Redemption` | |
| | ContributionSchedule | `circles.CircleRules` (amount, cycle, first due date), `Contribution` | the schedule is part of the accepted rules |
| | Asset | `pools.Asset` | obligor, sector, related party, rating |
| Assets & performance | AssetAssignment | `pools.AssetAssignment`, `AssetTransferRequest` | |
| | IncomeEvent / ExpenseEvent | `accounting.IncomeExpenseEvent` (`event_type`) | one model, two types |
| | ProvisionEvent | `pools.AssetProvisionEntry` | provision, release, write-off, recovery |
| | Valuation | `investments.NAVSnapshot`; valuation on `AssetTransferRequest` | |
| | DailyBalance | `pools.DailyBalance`, `BalanceImportBatch`, `DailyClose` | |
| | WeightageBand | `allocation.WeightageBand` | |
| Allocation & finance | ProfitSharingRule | `allocation.ProfitSharingRatio` | |
| | ReserveAccount | `allocation.ReservePolicy` (`current_balance`) | |
| | AllocationRun / AllocationLine | `allocation.AllocationRun`, `AllocationLine`; `investments.InvestmentDistributionRun`, `InvestmentDistributionLine` | |
| | JournalBatch | `accounting.JournalBatch`, `JournalEntry`, `GLExport` | |
| | Payment | `allocation.PayoutBatchRecord` (depositor profit payments); `circles.Payout` | a payment to a depositor is a line of a payout batch |
| | Payout | `circles.Payout` | |
| Assurance & AI | ExceptionCase | `governance.ExceptionCase` | |
| | PurificationCase | `governance.PurificationEntry` | |
| | AuditTest | `governance.ShariahAuditPlan`, `ShariahAuditFinding` | |
| | EvidenceObject | `core.AuditLog` (hash-chained), evidence bundles (`core/evidence_bundle_engine.py`), `AllocationRun.evidence_hash` | evidence is produced from recorded data, not stored as free files |
| | ModelVersion | `ai_agents.AIModelRegistry` (version, validation, retirement) | one row per model in use |
| | AIRecommendation | `ai_agents.AIRecommendation` | |
| | Consent | `participants.Consent`, `investments.DisclosureAcknowledgement`, `circles.RulesAcceptance` | |
| | Notification | `notifications.Notification` | |
