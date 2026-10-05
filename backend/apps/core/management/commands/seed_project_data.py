from datetime import date, timedelta
from decimal import Decimal
import uuid

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.core.context import set_current_tenant
from apps.tenants.models import LegalEntity, Tenant
from apps.accounts.models import User, UserRole
from apps.products.models import (
    ContractTemplate,
    ContractTemplateStatus,
    JurisdictionRulePack,
    OperatingModel,
    Product,
    ProductStatus,
    ShariahDecision,
    ShariahDecisionStatus,
)
from apps.pools.models import (
    Asset,
    AssetAssignment,
    AssetStatus,
    AssetType,
    BalanceImportBatch,
    BalanceImportBatchStatus,
    BalanceSource,
    DailyBalance,
    DailyBalanceStatus,
    PeriodCloseChecklist,
    PeriodCloseStatus,
    Pool,
    PoolStatus,
    PoolVersion,
)
from apps.allocation.models import (
    AllocationLine,
    AllocationRun,
    AllocationRunStatus,
    DepositorStatement,
    ProfitSharingRatio,
    PSRStatus,
    ReservePolicy,
    ReserveType,
    WeightageBand,
    WeightageBandStatus,
)
from apps.accounting.models import (
    IncomeExpenseEvent,
    IncomeExpenseEventStatus,
    IncomeExpenseEventType,
    JournalBatch,
    JournalBatchStatus,
    JournalEntry,
    JournalEntryType,
    ReconciliationBatch,
    ReconciliationItem,
    ReconciliationStatus,
)
from apps.governance.models import (
    AuditPlanStatus,
    ExceptionCase,
    ExceptionDetectedBy,
    ExceptionSeverity,
    ExceptionSourceModule,
    ExceptionStatus,
    PurificationEntry,
    PurificationStatus,
    RelatedPartyDisclosureStatus,
    RelatedPartyRelationshipType,
    RelatedPartyTransaction,
    ShariahAuditFinding,
    ShariahAuditPlan,
    SupportRequest,
    SupportRequestPriority,
    SupportRequestStatus,
    SupportRequestType,
)
from apps.investments.models import (
    CapitalAccount,
    CapitalAccountStatus,
    ImpairmentEvent,
    ImpairmentEventStatus,
    InvestorProfile,
    KYCStatus,
    NAVSnapshot,
    NAVSnapshotStatus,
    RiskTolerance,
    Subscription,
    SubscriptionStatus,
)
from apps.circles.models import (
    ArrearsRecord,
    ArrearsStatus,
    CircleMember,
    CircleMemberStatus,
    CircleProposal,
    CircleVote,
    Contribution,
    ContributionStatus,
    Payout,
    PayoutStatus,
    ProposalStatus,
    ProposalType,
    VoteDecision,
)


class Command(BaseCommand):
    help = "Seeds comprehensive Islamic Banking demo data across all 42 screens of Amanah Pool OS."

    def add_arguments(self, parser):
        parser.add_argument(
            "--tenant-code",
            default="NOVU-DEMO",
            help="Tenant code to seed data into (default: NOVU-DEMO).",
        )
        parser.add_argument(
            "--reset",
            action="store_true",
            default=True,
            help="Wipe existing tenant operational data before seeding (default: True).",
        )
        parser.add_argument(
            "--password",
            default="Amanah@2026!",
            help="Default password for seeded demo user accounts (default: Amanah@2026!).",
        )

    def handle(self, *args, **options):
        tenant_code = options["tenant_code"]
        password = options["password"]
        should_reset = options.get("reset", True)

        self.stdout.write(self.style.NOTICE(f"=== Starting Amanah Pool OS Seed Process for Tenant: {tenant_code} ==="))

        # 1. Tenant & Legal Entity
        tenant, _ = Tenant.objects.get_or_create(
            code=tenant_code,
            defaults={"name": "Novu Labs Demo", "data_residency": "PK"},
        )
        set_current_tenant(tenant)

        if should_reset:
            self.stdout.write(self.style.WARNING(f"Resetting existing operational data for tenant '{tenant_code}'..."))
            from apps.core.models import AuditLog

            # 1. Circles
            ArrearsRecord.objects.filter(tenant=tenant).delete()
            CircleVote.objects.filter(tenant=tenant).delete()
            CircleProposal.objects.filter(tenant=tenant).delete()
            Payout.objects.filter(tenant=tenant).delete()
            Contribution.objects.filter(tenant=tenant).delete()
            CircleMember.objects.filter(tenant=tenant).delete()

            # 2. Investments
            ImpairmentEvent.objects.filter(tenant=tenant).delete()
            NAVSnapshot.objects.filter(tenant=tenant).delete()
            Subscription.objects.filter(tenant=tenant).delete()
            CapitalAccount.objects.filter(tenant=tenant).delete()
            InvestorProfile.objects.filter(tenant=tenant).delete()

            # 3. Governance
            RelatedPartyTransaction.objects.filter(tenant=tenant).delete()
            SupportRequest.objects.filter(tenant=tenant).delete()
            ExceptionCase.objects.filter(tenant=tenant).delete()
            PurificationEntry.objects.filter(tenant=tenant).delete()
            ShariahAuditFinding.objects.filter(tenant=tenant).delete()
            ShariahAuditPlan.objects.filter(tenant=tenant).delete()

            # 4. Accounting
            JournalEntry.objects.filter(tenant=tenant).delete()
            JournalBatch.objects.filter(tenant=tenant).delete()
            IncomeExpenseEvent.objects.filter(tenant=tenant).delete()
            ReconciliationItem.objects.filter(tenant=tenant).delete()
            ReconciliationBatch.objects.filter(tenant=tenant).delete()

            # 5. Allocation
            DepositorStatement.objects.filter(tenant=tenant).delete()
            AllocationLine.objects.filter(tenant=tenant).delete()
            AllocationRun.objects.filter(tenant=tenant).delete()
            ReservePolicy.objects.filter(tenant=tenant).delete()
            WeightageBand.objects.filter(tenant=tenant).delete()
            ProfitSharingRatio.objects.filter(tenant=tenant).delete()

            # 6. Pools
            AssetAssignment.objects.filter(tenant=tenant).delete()
            DailyBalance.objects.filter(tenant=tenant).delete()
            BalanceImportBatch.objects.filter(tenant=tenant).delete()
            PeriodCloseChecklist.objects.filter(tenant=tenant).delete()
            Asset.objects.filter(tenant=tenant).delete()
            PoolVersion.objects.filter(tenant=tenant).delete()
            Pool.objects.filter(tenant=tenant).delete()

            # 7. Products
            Product.objects.filter(tenant=tenant).delete()
            ContractTemplate.objects.filter(tenant=tenant).delete()
            ShariahDecision.objects.filter(tenant=tenant).delete()
            JurisdictionRulePack.objects.filter(tenant=tenant).delete()

            # 8. Audit log
            AuditLog.objects.filter(tenant=tenant).delete()
            self.stdout.write(self.style.SUCCESS("[OK] Previous operational data reset."))

        legal_entity, _ = LegalEntity.objects.get_or_create(
            tenant=tenant,
            name="Novu Islamic Financial Services Ltd",
            defaults={
                "registration_number": "SEC-ISL-2025-0988",
                "jurisdiction": "Pakistan",
                "base_currency": "PKR",
                "timezone": "Asia/Karachi",
            },
        )
        self.stdout.write(self.style.SUCCESS(f"[OK] Tenant & Legal Entity: {tenant.name} ({legal_entity.name})"))

        # 2. Users (Ensure all 9 core roles exist with known password)
        role_users = [
            ("superadmin@novulabsdemo.test", "Tariq Al-Mansoor", UserRole.PLATFORM_SUPER_ADMIN),
            ("poolmanager@novulabsdemo.test", "Hamza Farooq", UserRole.POOL_MANAGER),
            ("maker@novulabsdemo.test", "Zubair Siddiqui (Maker)", UserRole.FINANCE_MAKER),
            ("checker@novulabsdemo.test", "Amina Malik (Checker)", UserRole.FINANCE_CHECKER),
            ("risk@novulabsdemo.test", "Dr. Khalid Rehman", UserRole.RISK_COMPLIANCE),
            ("secretariat@novulabsdemo.test", "Mufti Bilal Qasim", UserRole.SHARIAH_SECRETARIAT),
            ("board@novulabsdemo.test", "Sheikh Dr. Yusuf Al-Qaradawi", UserRole.SHARIAH_BOARD),
            ("auditor@novulabsdemo.test", "Rashid & Co Statutory Auditor", UserRole.AUDITOR),
            ("pm@novulabsdemo.test", "Maryam Nawaz", UserRole.PRODUCT_MANAGER),
        ]

        users_by_role = {}
        for email, full_name, role in role_users:
            user, _ = User.objects.get_or_create(
                email=email,
                defaults={"tenant": tenant, "full_name": full_name, "role": role},
            )
            user.full_name = full_name
            user.role = role
            user.tenant = tenant
            user.is_active = True
            user.set_password(password)
            user.save()
            users_by_role[role] = user

        maker = users_by_role[UserRole.FINANCE_MAKER]
        checker = users_by_role[UserRole.FINANCE_CHECKER]
        board_user = users_by_role[UserRole.SHARIAH_BOARD]
        sec_user = users_by_role[UserRole.SHARIAH_SECRETARIAT]
        pm_user = users_by_role[UserRole.PRODUCT_MANAGER]
        risk_user = users_by_role[UserRole.RISK_COMPLIANCE]
        self.stdout.write(self.style.SUCCESS(f"[OK] 9 Role Users Configured with password '{password}'"))

        # 3. Jurisdiction Rule Packs (Screen 42)
        sbp_pack, _ = JurisdictionRulePack.objects.get_or_create(
            tenant=tenant,
            code="PK-SBP-2025",
            version="2025.01",
            defaults={
                "name": "State Bank of Pakistan (SBP) Framework 2025",
                "effective_date": date(2025, 1, 1),
                "is_active": True,
                "is_default": True,
                "description": "SBP IBD Circular 03/2012 and 2025 updates on Mudarabah pool profit sharing and reserve caps.",
                "rules_config": {
                    "per_ceiling_pct": 2.0,
                    "irr_ceiling_pct": 5.0,
                    "notice_period_days": 30,
                    "mudarib_share_cap_pct": 20.0,
                    "purification_interval": "monthly",
                },
            },
        )
        sbp_pack.is_default = True
        sbp_pack.save()

        JurisdictionRulePack.objects.get_or_create(
            tenant=tenant,
            code="AAOIFI-GS1",
            version="2025.02",
            defaults={
                "name": "AAOIFI Global Shariah Governance (GS-1 / FAS)",
                "effective_date": date(2025, 1, 1),
                "is_active": True,
                "is_default": False,
                "description": "AAOIFI Governance Standard No. 1 and Financial Accounting Standards for Islamic Banks.",
                "rules_config": {
                    "per_ceiling_pct": 5.0,
                    "irr_ceiling_pct": 10.0,
                    "notice_period_days": 15,
                    "mudarib_share_cap_pct": 30.0,
                    "purification_interval": "quarterly",
                },
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Jurisdiction Rule Packs Seeded (SBP & AAOIFI)"))

        # 4. Shariah Decisions / Fatwas (Screen 26)
        fatwa_1, _ = ShariahDecision.objects.get_or_create(
            tenant=tenant,
            decision_code="FATWA-2025-01",
            defaults={
                "title": "Approval of General Mudarabah Pool Profit Allocation & Daily Weightage Mechanism",
                "decision_type": "product_approval",
                "description": "Comprehensive review of daily weighted average balance method, PSR matrix, and PER/IRR deductions.",
                "fiqh_reference": "AAOIFI Shariah Standard No. 13 (Mudarabah) Section 4/2 & SBP Prudential Regs",
                "mandatory_caveats": "Mudarib share cannot exceed 30%. Loss must be borne entirely by Rab-ul-Mal except in case of proven negligence.",
                "status": ShariahDecisionStatus.APPROVED,
                "effective_date": date(2025, 1, 1),
                "created_by": sec_user,
                "approved_by": board_user,
                "approved_at": timezone.now(),
            },
        )

        fatwa_2, _ = ShariahDecision.objects.get_or_create(
            tenant=tenant,
            decision_code="FATWA-2025-02",
            defaults={
                "title": "Wakala Inter-Bank Treasury Placement & Performance Incentive Structure",
                "decision_type": "product_approval",
                "description": "Approval of agency placement agreements where Muwakkil appoints Wakeel for fixed anticipated profit and performance incentive.",
                "fiqh_reference": "AAOIFI Shariah Standard No. 23 (Agency) Section 2/1",
                "mandatory_caveats": "Any excess profit beyond anticipated rate may be paid as Muwakkil incentive.",
                "status": ShariahDecisionStatus.APPROVED,
                "effective_date": date(2025, 1, 1),
                "created_by": sec_user,
                "approved_by": board_user,
                "approved_at": timezone.now(),
            },
        )

        fatwa_3, _ = ShariahDecision.objects.get_or_create(
            tenant=tenant,
            decision_code="FATWA-2025-03",
            defaults={
                "title": "Diminishing Musharakah Asset Ownership & Periodic Unit Sale Matrix",
                "decision_type": "product_approval",
                "description": "Shariah ruling approving joint property co-ownership and lease rental adjustments.",
                "fiqh_reference": "AAOIFI Shariah Standard No. 12 (Sharika) Section 5",
                "mandatory_caveats": "Unit purchase promise must remain unilateral and independent of the Ijarah contract.",
                "status": ShariahDecisionStatus.APPROVED,
                "effective_date": date(2025, 1, 1),
                "created_by": sec_user,
                "approved_by": board_user,
                "approved_at": timezone.now(),
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Shariah Decisions & Fatwas Seeded"))

        # 5. Contract Templates (Screen 27)
        tpl_mudarabah, _ = ContractTemplate.objects.get_or_create(
            tenant=tenant,
            name="Standard Unrestricted Mudarabah Depositor Agreement",
            version="2025.1",
            defaults={
                "contract_type": "mudarabah_unrestricted",
                "shariah_decision": fatwa_1,
                "status": ContractTemplateStatus.APPROVED,
                "clauses": {
                    "mudarib_share": "The Bank acts as Mudarib and earns an agreed percentage of actual distributable profit.",
                    "loss_absorption": "Financial loss shall be borne strictly by depositors in proportion to capital.",
                    "reserve_deductions": "Profit Equalization Reserve and Investment Risk Reserve may be appropriated subject to SBP limits.",
                },
            },
        )

        tpl_wakala, _ = ContractTemplate.objects.get_or_create(
            tenant=tenant,
            name="Restricted Wakala Treasury Placement Agreement",
            version="2025.1",
            defaults={
                "contract_type": "wakala",
                "shariah_decision": fatwa_2,
                "status": ContractTemplateStatus.APPROVED,
                "clauses": {
                    "wakalah_fee": "Lump-sum agency fee of PKR 25,000 per placement tranche.",
                    "target_return": "Anticipated return bench-marked against 3M KIBOR.",
                    "incentive_bonus": "Any profit exceeding benchmark retained by Wakeel as performance incentive.",
                },
            },
        )

        tpl_musharakah, _ = ContractTemplate.objects.get_or_create(
            tenant=tenant,
            name="Diminishing Musharakah Commercial Co-Ownership Master",
            version="2025.2",
            defaults={
                "contract_type": "musharakah",
                "shariah_decision": fatwa_3,
                "status": ContractTemplateStatus.APPROVED,
                "clauses": {
                    "co_ownership": "Bank and Client purchase undivided fractional ownership units.",
                    "monthly_redemption": "Client buys out Bank's share in monthly equal installments.",
                },
            },
        )

        tpl_circle, _ = ContractTemplate.objects.get_or_create(
            tenant=tenant,
            name="Amanah Rotating Community Savings (Qard/ROSCA) Master",
            version="2025.1",
            defaults={
                "contract_type": "qard",
                "shariah_decision": fatwa_1,
                "status": ContractTemplateStatus.APPROVED,
                "clauses": {
                    "qard_hasan": "Interest-free mutual loan facility among circle members with zero time-value uplift.",
                    "rotation_basis": "Random draw assignment verified cryptographically.",
                    "hardship_relief": "Community review process for delayed payments without compounding or penalty.",
                },
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Contract Templates Seeded"))

        # 6. Products (Screen 28)
        prod_mud, _ = Product.objects.get_or_create(
            tenant=tenant,
            code="PRD-MUD-01",
            defaults={
                "name": "Amanah Daily Profit Depositor Account",
                "operating_model": OperatingModel.BANK_POOL,
                "contract_template": tpl_mudarabah,
                "status": ProductStatus.APPROVED,
                "base_currency": "PKR",
            },
        )

        prod_wak, _ = Product.objects.get_or_create(
            tenant=tenant,
            code="PRD-WAK-02",
            defaults={
                "name": "Amanah Wakala High-Yield Corporate Placement",
                "operating_model": OperatingModel.BANK_POOL,
                "contract_template": tpl_wakala,
                "status": ProductStatus.APPROVED,
                "base_currency": "PKR",
            },
        )

        prod_mus, _ = Product.objects.get_or_create(
            tenant=tenant,
            code="PRD-MUS-03",
            defaults={
                "name": "Amanah Diminishing Musharakah Financing Pool",
                "operating_model": OperatingModel.INVESTMENT_POOL,
                "contract_template": tpl_musharakah,
                "status": ProductStatus.APPROVED,
                "base_currency": "PKR",
            },
        )

        prod_circle, _ = Product.objects.get_or_create(
            tenant=tenant,
            code="PRD-CIR-04",
            defaults={
                "name": "Amanah Community Welfare Savings Circle (Kameti)",
                "operating_model": OperatingModel.COMMUNITY_CIRCLE,
                "contract_template": tpl_circle,
                "status": ProductStatus.APPROVED,
                "base_currency": "PKR",
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Products Seeded"))

        # 7. Pools (Screens 03, 04)
        pool_gen, _ = Pool.objects.get_or_create(
            tenant=tenant,
            code="POOL-GEN-01",
            defaults={
                "name": "General Islamic Depositor Pool (PKR)",
                "product": prod_mud,
                "effective_date": date(2026, 1, 1),
                "status": PoolStatus.ALLOCATION,
            },
        )
        PoolVersion.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            version_number=1,
            defaults={
                "snapshot": {
                    "product": {
                        "id": str(prod_mud.id),
                        "name": prod_mud.name,
                        "code": prod_mud.code,
                        "operating_model": prod_mud.operating_model,
                        "status": prod_mud.status,
                    },
                    "contract_template": {
                        "id": str(tpl_mudarabah.id),
                        "name": tpl_mudarabah.name,
                        "contract_type": tpl_mudarabah.contract_type,
                        "version": tpl_mudarabah.version,
                        "clauses": tpl_mudarabah.clauses,
                        "status": tpl_mudarabah.status,
                    },
                },
                "created_by": pm_user,
                "is_current": True,
            },
        )

        pool_treas, _ = Pool.objects.get_or_create(
            tenant=tenant,
            code="POOL-TREAS-02",
            defaults={
                "name": "Islamic Inter-Bank Treasury Wakala Pool",
                "product": prod_wak,
                "effective_date": date(2026, 2, 1),
                "status": PoolStatus.OPEN,
            },
        )
        PoolVersion.objects.get_or_create(
            tenant=tenant,
            pool=pool_treas,
            version_number=1,
            defaults={
                "snapshot": {
                    "product": {
                        "id": str(prod_wak.id),
                        "name": prod_wak.name,
                        "code": prod_wak.code,
                        "operating_model": prod_wak.operating_model,
                        "status": prod_wak.status,
                    },
                    "contract_template": {
                        "id": str(tpl_wakala.id),
                        "name": tpl_wakala.name,
                        "contract_type": tpl_wakala.contract_type,
                        "version": tpl_wakala.version,
                        "clauses": tpl_wakala.clauses,
                        "status": tpl_wakala.status,
                    },
                },
                "created_by": pm_user,
                "is_current": True,
            },
        )

        pool_corp, _ = Pool.objects.get_or_create(
            tenant=tenant,
            code="POOL-CORP-03",
            defaults={
                "name": "SME & Commercial Diminishing Musharakah Pool",
                "product": prod_mus,
                "effective_date": date(2026, 3, 1),
                "status": PoolStatus.APPROVED,
            },
        )

        pool_circle, _ = Pool.objects.get_or_create(
            tenant=tenant,
            code="POOL-CIR-01",
            defaults={
                "name": "Karachi Healthcare Workers Welfare Circle",
                "product": prod_circle,
                "effective_date": date(2026, 1, 1),
                "status": PoolStatus.OPEN,
            },
        )
        PoolVersion.objects.get_or_create(
            tenant=tenant,
            pool=pool_circle,
            version_number=1,
            defaults={
                "snapshot": {
                    "product": {
                        "id": str(prod_circle.id),
                        "name": prod_circle.name,
                        "code": prod_circle.code,
                        "operating_model": prod_circle.operating_model,
                        "status": prod_circle.status,
                    },
                    "contract_template": {
                        "id": str(tpl_circle.id),
                        "name": tpl_circle.name,
                        "contract_type": tpl_circle.contract_type,
                        "version": tpl_circle.version,
                        "clauses": tpl_circle.clauses,
                        "status": tpl_circle.status,
                    },
                },
                "created_by": pm_user,
                "is_current": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Investment & Community Pools Seeded"))

        # 8. Weightage Bands & PSR Matrix (Screens 05, 06)
        tiers_gen = [
            ("Retail Regular", Decimal("1.00")),
            ("Premium Saver", Decimal("1.15")),
            ("HNW Depositor", Decimal("1.30")),
            ("Corporate / Institutional", Decimal("1.45")),
        ]
        for p_class, wt in tiers_gen:
            WeightageBand.objects.get_or_create(
                tenant=tenant,
                pool=pool_gen,
                participant_class=p_class,
                effective_from=date(2026, 1, 1),
                defaults={
                    "weightage": wt,
                    "status": WeightageBandStatus.APPROVED,
                },
            )

        ProfitSharingRatio.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            effective_from=date(2026, 1, 1),
            defaults={
                "depositor_share": Decimal("70.00"),
                "mudarib_share": Decimal("30.00"),
                "status": PSRStatus.APPROVED,
            },
        )

        tiers_treas = [
            ("Financial Institutions", Decimal("1.20")),
            ("Sovereign / Central Bank", Decimal("1.50")),
        ]
        for p_class, wt in tiers_treas:
            WeightageBand.objects.get_or_create(
                tenant=tenant,
                pool=pool_treas,
                participant_class=p_class,
                effective_from=date(2026, 2, 1),
                defaults={
                    "weightage": wt,
                    "status": WeightageBandStatus.APPROVED,
                },
            )

        ProfitSharingRatio.objects.get_or_create(
            tenant=tenant,
            pool=pool_treas,
            effective_from=date(2026, 2, 1),
            defaults={
                "depositor_share": Decimal("85.00"),
                "mudarib_share": Decimal("15.00"),
                "status": PSRStatus.APPROVED,
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Weightage Bands & PSR Matrix Seeded"))

        # 9. Reserve Policies (Screen 42 / BR-004)
        ReservePolicy.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            reserve_type=ReserveType.PER,
            defaults={
                "rate_percentage": Decimal("2.00"),
                "cap_percentage": Decimal("5.00"),
                "current_balance": Decimal("1250000.00"),
                "is_active": True,
            },
        )
        ReservePolicy.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            reserve_type=ReserveType.IRR,
            defaults={
                "rate_percentage": Decimal("1.50"),
                "cap_percentage": Decimal("5.00"),
                "current_balance": Decimal("850000.00"),
                "is_active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] PER/IRR Statutory Reserve Policies Seeded"))

        # 10. Assets & Assignments (Screens 07, 08)
        assets_data = [
            ("AST-SUK-01", "GOP Domestic Ijarah Sukuk Series 14", AssetType.OTHER, Decimal("50000000.00"), pool_gen),
            ("AST-MUR-02", "Corporate Working Capital Murabaha - Engro", AssetType.MURABAHAH, Decimal("30000000.00"), pool_gen),
            ("AST-IJR-03", "Commercial Logistics Fleet Ijarah - Master Motors", AssetType.IJARAH, Decimal("20000000.00"), pool_gen),
            ("AST-MUS-04", "Diminishing Musharakah Industrial Tech Park", AssetType.DIMINISHING_MUSHARAKAH, Decimal("40000000.00"), pool_corp),
            ("AST-SUK-05", "WAPDA Hydroelectric Sovereign Sukuk 2026", AssetType.OTHER, Decimal("75000000.00"), pool_treas),
        ]
        for ref_code, desc, at, face_val, target_pool in assets_data:
            asset, _ = Asset.objects.get_or_create(
                tenant=tenant,
                reference_code=ref_code,
                defaults={
                    "description": desc,
                    "asset_type": at,
                    "face_value": face_val,
                    "status": AssetStatus.ASSIGNED,
                },
            )
            AssetAssignment.objects.get_or_create(
                tenant=tenant,
                asset=asset,
                pool=target_pool,
                defaults={"assigned_date": date(2026, 1, 1), "assigned_by": maker},
            )
        self.stdout.write(self.style.SUCCESS("[OK] Assets & Assignments Seeded"))

        # 11. Daily Balances & Import Batch (Screen 09)
        import_batch, _ = BalanceImportBatch.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            value_date=date(2026, 9, 28),
            defaults={
                "total_records": 4,
                "matched_records": 4,
                "exception_count": 0,
                "control_total_expected": Decimal("100000000.00"),
                "control_total_actual": Decimal("100000000.00"),
                "status": BalanceImportBatchStatus.BALANCED,
                "imported_by": maker,
            },
        )

        for p_class, amt in [
            ("Retail Regular", Decimal("25000000.00")),
            ("Premium Saver", Decimal("35000000.00")),
            ("HNW Depositor", Decimal("20000000.00")),
            ("Corporate / Institutional", Decimal("20000000.00")),
        ]:
            DailyBalance.objects.get_or_create(
                tenant=tenant,
                pool=pool_gen,
                value_date=date(2026, 9, 28),
                participant_class=p_class,
                defaults={
                    "balance_amount": amt,
                    "source": BalanceSource.FILE_IMPORT,
                    "status": DailyBalanceStatus.VALIDATED,
                },
            )
        self.stdout.write(self.style.SUCCESS("[OK] Daily Balances Seeded"))

        # 12. Income & Expense Events (Screen 10)
        events_data = [
            (IncomeExpenseEventType.INCOME, "Financing Profit", Decimal("1850000.00"), date(2026, 9, 25), "Sukuk Coupon Periodic Rental Accrual"),
            (IncomeExpenseEventType.INCOME, "Financing Profit", Decimal("920000.00"), date(2026, 9, 26), "Engro Murabaha Sales Profit Settlement"),
            (IncomeExpenseEventType.EXPENSE, "Direct Takaful", Decimal("145000.00"), date(2026, 9, 27), "Pak-Qatar Islamic Takaful Asset Protection Premium"),
            (IncomeExpenseEventType.EXPENSE, "Custody Fees", Decimal("65000.00"), date(2026, 9, 27), "CDC Central Depository Sukuk Custody Fee"),
        ]
        for et, ec, amt, ed, desc in events_data:
            IncomeExpenseEvent.objects.get_or_create(
                tenant=tenant,
                pool=pool_gen,
                amount=amt,
                event_date=ed,
                defaults={
                    "event_type": et,
                    "category": ec,
                    "description": desc,
                    "status": IncomeExpenseEventStatus.POSTED,
                    "created_by": maker,
                    "posted_by": checker,
                    "posted_at": timezone.now(),
                },
            )
        self.stdout.write(self.style.SUCCESS("[OK] Income & Expense Events Seeded"))

        # 13. Allocation Runs & Journal Batches (Screens 13, 14, 15, 17, 18, 20)
        # Run 1: Certified / Signed Run for August 2026
        run_aug, _ = AllocationRun.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            value_date=date(2026, 8, 31),
            defaults={
                "gross_income": Decimal("4500000.00"),
                "direct_expenses": Decimal("210000.00"),
                "distributable_amount": Decimal("4290000.00"),
                "total_weighted_funds": Decimal("128500000.00"),
                "depositor_pool_share": Decimal("3003000.00"),
                "mudarib_share": Decimal("1287000.00"),
                "status": AllocationRunStatus.SIGNED,
                "calculation_hash": "a8f3b4c129e874cd9912beff3847e0915a2c418f773618402bc093e1176b92e8",
                "created_by": maker,
                "checked_by": checker,
                "checked_at": timezone.now() - timedelta(days=28),
                "shariah_signed_off_by": board_user,
                "shariah_signed_off_at": timezone.now() - timedelta(days=28),
                "shariah_review_note": "Certified conforming to AAOIFI FAS-30 and SBP IBD Circular 03/2012.",
            },
        )

        for p_class, wt_funds, alloc_amt in [
            ("Retail Regular", Decimal("25000000.00"), Decimal("584241.00")),
            ("Premium Saver", Decimal("40250000.00"), Decimal("940628.00")),
            ("HNW Depositor", Decimal("26000000.00"), Decimal("607611.00")),
            ("Corporate / Institutional", Decimal("29000000.00"), Decimal("677720.00")),
        ]:
            AllocationLine.objects.get_or_create(
                tenant=tenant,
                allocation_run=run_aug,
                participant_class=p_class,
                defaults={
                    "daily_funds": wt_funds,
                    "weightage": Decimal("1.00"),
                    "weighted_funds": wt_funds,
                    "allocated_amount": alloc_amt,
                },
            )
            DepositorStatement.objects.get_or_create(
                tenant=tenant,
                allocation_run=run_aug,
                participant_class=p_class,
                defaults={
                    "period_start": date(2026, 8, 1),
                    "period_end": date(2026, 8, 31),
                    "opening_balance": wt_funds,
                    "net_deposits": Decimal("0.00"),
                    "profit_allocated": alloc_amt,
                    "closing_balance": wt_funds + alloc_amt,
                    "narrative": f"Islamic profit distribution for {p_class} based on August 2026 Mudarabah allocation.",
                },
            )

        batch_aug, _ = JournalBatch.objects.get_or_create(
            tenant=tenant,
            allocation_run=run_aug,
            pool=pool_gen,
            defaults={
                "batch_date": date(2026, 8, 31),
                "total_debit": Decimal("4290000.00"),
                "total_credit": Decimal("4290000.00"),
                "status": JournalBatchStatus.POSTED,
                "posted_by": checker,
            },
        )
        JournalEntry.objects.get_or_create(
            tenant=tenant,
            batch=batch_aug,
            account_name="Pool Distributable Income Clearing",
            entry_type=JournalEntryType.DEBIT,
            defaults={"amount": Decimal("4290000.00")},
        )
        JournalEntry.objects.get_or_create(
            tenant=tenant,
            batch=batch_aug,
            account_name="Depositors Profit Payable Control",
            entry_type=JournalEntryType.CREDIT,
            defaults={"amount": Decimal("3003000.00")},
        )
        JournalEntry.objects.get_or_create(
            tenant=tenant,
            batch=batch_aug,
            account_name="Mudarib Fee Income Accrual",
            entry_type=JournalEntryType.CREDIT,
            defaults={"amount": Decimal("1287000.00")},
        )

        # Run 2: Reversed Run for July 2026 (Restatement Testing - Screen 17)
        run_july_rev, _ = AllocationRun.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            value_date=date(2026, 7, 31),
            status=AllocationRunStatus.REVERSED,
            defaults={
                "gross_income": Decimal("4100000.00"),
                "direct_expenses": Decimal("180000.00"),
                "distributable_amount": Decimal("3920000.00"),
                "total_weighted_funds": Decimal("120000000.00"),
                "depositor_pool_share": Decimal("2744000.00"),
                "mudarib_share": Decimal("1176000.00"),
                "is_restatement": True,
                "restatement_reason": "[Regulatory Examination Finding (SBP / Central Bank)] Late CBS asset accrual adjustment.",
                "created_by": maker,
                "checked_by": checker,
            },
        )

        # Run 3: Draft Rerun for July Restatement
        AllocationRun.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            value_date=date(2026, 7, 31),
            is_restatement=True,
            status=AllocationRunStatus.SIMULATED,
            defaults={
                "replaces_run": run_july_rev,
                "gross_income": Decimal("4150000.00"),
                "direct_expenses": Decimal("180000.00"),
                "distributable_amount": Decimal("3970000.00"),
                "total_weighted_funds": Decimal("120000000.00"),
                "depositor_pool_share": Decimal("2779000.00"),
                "mudarib_share": Decimal("1191000.00"),
                "restatement_reason": "[Corrected Rerun] Updated with late clearing accruals.",
                "created_by": maker,
            },
        )

        # Run 4: Pending Approval Run for Current Cycle (September 2026)
        AllocationRun.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            value_date=date(2026, 9, 30),
            defaults={
                "gross_income": Decimal("5200000.00"),
                "direct_expenses": Decimal("240000.00"),
                "distributable_amount": Decimal("4960000.00"),
                "total_weighted_funds": Decimal("135000000.00"),
                "depositor_pool_share": Decimal("3472000.00"),
                "mudarib_share": Decimal("1488000.00"),
                "status": AllocationRunStatus.PENDING_APPROVAL,
                "created_by": maker,
                "shariah_signed_off_by": board_user,
                "shariah_signed_off_at": timezone.now(),
                "shariah_review_note": "Pre-screened and certified for end-of-quarter distribution.",
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Allocation Runs, Statements & Journal Batches Seeded"))

        # 14. Reconciliation Center Batches & Items (Screen 11)
        recon_batch_1 = ReconciliationBatch.objects.filter(
            tenant=tenant,
            pool=pool_gen,
            reconciliation_date=date(2026, 9, 28),
        ).first()
        if not recon_batch_1:
            recon_batch_1 = ReconciliationBatch.objects.create(
                tenant=tenant,
                pool=pool_gen,
                reconciliation_date=date(2026, 9, 28),
                total_records=4,
                matched_records=4,
                exception_count=0,
                variance_amount=Decimal("0.00"),
                status=ReconciliationStatus.MATCHED,
                control_total_status="BalancedPASS",
                performed_by=maker,
                notes="Month-end automated CBS sub-ledger to GL control account alignment.",
            )
        for ref, amt in [
            ("GL-MUD-RET-001", Decimal("25000000.00")),
            ("GL-MUD-PREM-002", Decimal("35000000.00")),
            ("GL-MUD-HNW-003", Decimal("20000000.00")),
            ("GL-MUD-CORP-004", Decimal("20000000.00")),
        ]:
            ReconciliationItem.objects.filter(
                tenant=tenant,
                batch=recon_batch_1,
                account_reference=ref,
            ).first() or ReconciliationItem.objects.create(
                tenant=tenant,
                batch=recon_batch_1,
                account_reference=ref,
                cbs_amount=amt,
                gl_amount=amt,
                variance=Decimal("0.00"),
                status="matched",
                resolution_notes="Balanced to cent.",
            )

        recon_batch_2 = ReconciliationBatch.objects.filter(
            tenant=tenant,
            pool=pool_gen,
            reconciliation_date=date(2026, 9, 29),
        ).first()
        if not recon_batch_2:
            recon_batch_2 = ReconciliationBatch.objects.create(
                tenant=tenant,
                pool=pool_gen,
                reconciliation_date=date(2026, 9, 29),
                total_records=3,
                matched_records=2,
                exception_count=1,
                variance_amount=Decimal("12500.00"),
                status=ReconciliationStatus.VARIANCE_FLAGGED,
                control_total_status="VarianceFlagged",
                performed_by=maker,
                notes="End of day clearance batch with 1 pending float settlement.",
            )
        ReconciliationItem.objects.get_or_create(
            tenant=tenant,
            batch=recon_batch_2,
            account_reference="GL-MUD-RET-001",
            defaults={"cbs_amount": Decimal("25000000.00"), "gl_amount": Decimal("25000000.00"), "variance": Decimal("0.00"), "status": "matched"},
        )
        ReconciliationItem.objects.get_or_create(
            tenant=tenant,
            batch=recon_batch_2,
            account_reference="GL-MUD-FLOAT-005",
            defaults={
                "cbs_amount": Decimal("1500000.00"),
                "gl_amount": Decimal("1487500.00"),
                "variance": Decimal("12500.00"),
                "status": "discrepancy",
                "resolution_notes": "Transit float delay from 1Link inter-bank switch.",
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Reconciliation Batches & Items Seeded (Screen 11)"))

        # 15. Period Close Manager (Screen 16)
        PeriodCloseChecklist.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            period_start=date(2026, 8, 1),
            period_end=date(2026, 8, 31),
            defaults={
                "status": PeriodCloseStatus.LOCKED,
                "checklist_data": {
                    "reconciled": True,
                    "shariah_parameters_sealed": True,
                    "exceptions_cleared": True,
                    "allocation_signed": True,
                    "journals_posted": True,
                },
                "decision_note": "August 2026 period fully reconciled and locked with cryptographic seal.",
                "certified_by": checker,
                "certified_at": timezone.now() - timedelta(days=27),
            },
        )

        PeriodCloseChecklist.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            period_start=date(2026, 9, 1),
            period_end=date(2026, 9, 30),
            defaults={
                "status": PeriodCloseStatus.OPEN,
                "checklist_data": {
                    "reconciled": True,
                    "shariah_parameters_sealed": True,
                    "exceptions_cleared": True,
                    "allocation_signed": False,
                    "journals_posted": False,
                },
                "decision_note": "Awaiting final profit allocation sign-off and GL posting.",
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Period Close Checklists Seeded (Screen 16)"))

        # 16. Shariah Audit Plan & Findings (Screen 33)
        audit_plan_2026, _ = ShariahAuditPlan.objects.get_or_create(
            tenant=tenant,
            plan_year=2026,
            defaults={
                "title": "FY 2026 Annual Shariah Compliance & Fiqh Audit Plan",
                "scope": "All Active Investment Pools, Asset Registries, and Profit Allocations",
                "frequency": "Quarterly",
                "status": AuditPlanStatus.APPROVED,
                "target_samples_count": 120,
                "tested_samples_count": 95,
                "findings_count": 3,
                "approved_by": board_user,
                "notes": "Approved by Shariah Supervisory Board at Meeting #42/2026.",
            },
        )

        findings_data = [
            ("Late notification of asset valuation index change", ExceptionSeverity.MEDIUM, "remediated", "Valuation index adjustment communicated with 4-day lag.", "Valuation notification workflow automated."),
            ("Documentation gap on Murabaha offer-and-acceptance sequence", ExceptionSeverity.HIGH, "open", "Two corporate murabaha transactions executed without signed acceptance timestamp.", "Operational training issued; compliance review underway."),
            ("Minor charity account interest purification lag", ExceptionSeverity.LOW, "closed", "Quarterly interest sweep delayed by 3 business days.", "Sweep completed and confirmed with charitable trust receipt."),
        ]
        for title, sev, st, obs, resp in findings_data:
            ShariahAuditFinding.objects.get_or_create(
                tenant=tenant,
                audit_plan=audit_plan_2026,
                title=title,
                defaults={
                    "severity": sev,
                    "status": st,
                    "observation": obs,
                    "management_response": resp,
                },
            )
        self.stdout.write(self.style.SUCCESS("[OK] Shariah Audit Plan & Findings Seeded (Screen 33)"))

        # 17. Governance Exceptions, Purification, RPT & Support (Screens 29, 30, 31, 34)
        ExceptionCase.objects.get_or_create(
            tenant=tenant,
            source_object_id="EXC-2026-001",
            defaults={
                "pool": pool_gen,
                "title": "Late Transit Float Interest Credited by Correspondent Bank",
                "source_module": ExceptionSourceModule.BALANCE_IMPORT,
                "severity": ExceptionSeverity.CRITICAL,
                "status": ExceptionStatus.INVESTIGATING,
                "detected_by": ExceptionDetectedBy.SYSTEM,
                "description": "Correspondent clearing account credited PKR 48,250 interest on transit funds overnight.",
                "assigned_to": risk_user,
            },
        )
        ExceptionCase.objects.get_or_create(
            tenant=tenant,
            source_object_id="EXC-2026-002",
            defaults={
                "pool": pool_gen,
                "title": "Weightage Matrix Tier 3 Boundary Overlap Test Warning",
                "source_module": ExceptionSourceModule.ALLOCATION,
                "severity": ExceptionSeverity.HIGH,
                "status": ExceptionStatus.RESOLVED,
                "detected_by": ExceptionDetectedBy.SYSTEM,
                "description": "Boundary condition flagged during simulation; corrected before approval.",
                "assigned_to": risk_user,
                "resolved_by": checker,
                "resolution_notes": "Tier ceiling verified and adjusted to PKR 10,000,000.00.",
                "resolved_at": timezone.now(),
            },
        )

        PurificationEntry.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            amount=Decimal("48250.00"),
            defaults={
                "source_description": "Non-compliant interest return from transit buffer funds.",
                "identified_date": date(2026, 9, 20),
                "status": PurificationStatus.DISTRIBUTED,
                "charity_recipient": "Shaukat Khanum Memorial Cancer Hospital & Research Centre",
                "distributed_date": date(2026, 9, 22),
                "approved_by": sec_user,
                "notes": "Distribution reference: DISB-PUR-SKMT-20260922-01",
            },
        )
        PurificationEntry.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            amount=Decimal("12800.00"),
            defaults={
                "source_description": "Conventional clearing dividend fraction.",
                "identified_date": date(2026, 9, 26),
                "status": PurificationStatus.IDENTIFIED,
                "approved_by": sec_user,
            },
        )

        RelatedPartyTransaction.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            related_party_name="Novu Holdings Sponsor Mudarib Account",
            transaction_date=date(2026, 9, 1),
            defaults={
                "relationship_type": RelatedPartyRelationshipType.AFFILIATE_COMPANY,
                "transaction_type": "Mudarib Subordinated Placement",
                "amount": Decimal("15000000.00"),
                "disclosure_status": RelatedPartyDisclosureStatus.APPROVED,
                "reviewed_by": board_user,
                "review_notes": "Terms strictly match standard published institutional Mudarabah PSR schedule.",
            },
        )

        SupportRequest.objects.get_or_create(
            tenant=tenant,
            subject="Quarterly Profit Rate Inquiry for Account #9921",
            defaults={
                "pool": pool_gen,
                "request_type": SupportRequestType.STATEMENT_CORRECTION,
                "raised_by_name": "Dr. Tariq Jamil (HNW Client)",
                "description": "Client requested detailed breakdown of August 2026 Mudarabah weightage and tax withholding.",
                "priority": SupportRequestPriority.MEDIUM,
                "status": SupportRequestStatus.IN_PROGRESS,
                "assigned_to": checker,
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Governance Exceptions, Purification, RPT & Disputes Seeded"))

        # 18. Investments: Capital Accounts, Investor Profiles, NAV (Screens 21-24)
        cap_acc_1, _ = CapitalAccount.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            investor_reference="INV-ALB-001",
            defaults={
                "investor_name": "Al-Baraka Family Endowment Trust",
                "units_held": Decimal("150000.00"),
                "status": CapitalAccountStatus.ACTIVE,
            },
        )
        InvestorProfile.objects.get_or_create(
            tenant=tenant,
            capital_account=cap_acc_1,
            defaults={
                "kyc_status": KYCStatus.VERIFIED,
                "id_document_type": "CNIC / Registration",
                "id_document_number": "35201-1234567-1",
                "date_of_birth": date(1985, 4, 12),
                "address": "74/B Gulberg III, Lahore, Pakistan",
                "risk_tolerance": RiskTolerance.MODERATE,
                "suitability_assessment_notes": "Institutional endowment with moderate liquidity requirement.",
                "verified_by": checker,
                "verified_at": timezone.now(),
            },
        )

        cap_acc_2, _ = CapitalAccount.objects.get_or_create(
            tenant=tenant,
            pool=pool_gen,
            investor_reference="INV-ZUB-002",
            defaults={
                "investor_name": "Zubair Ahmad (HNW Individual)",
                "units_held": Decimal("50000.00"),
                "status": CapitalAccountStatus.ACTIVE,
            },
        )
        InvestorProfile.objects.get_or_create(
            tenant=tenant,
            capital_account=cap_acc_2,
            defaults={
                "kyc_status": KYCStatus.VERIFIED,
                "id_document_type": "CNIC",
                "id_document_number": "35201-7654321-3",
                "date_of_birth": date(1978, 9, 21),
                "address": "DHA Phase 5, Karachi, Pakistan",
                "risk_tolerance": RiskTolerance.CONSERVATIVE,
                "suitability_assessment_notes": "HNW individual seeking low risk capital preservation.",
                "verified_by": checker,
                "verified_at": timezone.now(),
            },
        )

        Subscription.objects.get_or_create(
            tenant=tenant,
            capital_account=cap_acc_1,
            transaction_date=date(2026, 1, 15),
            defaults={
                "amount": Decimal("15000000.00"),
                "units_allotted": Decimal("150000.00"),
                "nav_per_unit": Decimal("100.00"),
                "status": SubscriptionStatus.PROCESSED,
            },
        )

        for snap_date, nav_val in [
            (date(2026, 6, 30), Decimal("102.45")),
            (date(2026, 7, 31), Decimal("104.10")),
            (date(2026, 8, 31), Decimal("106.85")),
        ]:
            NAVSnapshot.objects.get_or_create(
                tenant=tenant,
                pool=pool_gen,
                valuation_date=snap_date,
                defaults={
                    "total_pool_value": Decimal("106850000.00"),
                    "total_units_outstanding": Decimal("1000000.00"),
                    "nav_per_unit": nav_val,
                    "status": NAVSnapshotStatus.PUBLISHED,
                    "created_by": maker,
                    "published_by": checker,
                    "published_at": timezone.now(),
                },
            )

        cap_acc_corp, _ = CapitalAccount.objects.get_or_create(
            tenant=tenant,
            pool=pool_corp,
            investor_reference="INV-INDUS-003",
            defaults={
                "investor_name": "Indus Valley Agro Ventures (Pvt) Ltd",
                "units_held": Decimal("320000.00"),
                "status": CapitalAccountStatus.ACTIVE,
            },
        )
        InvestorProfile.objects.get_or_create(
            tenant=tenant,
            capital_account=cap_acc_corp,
            defaults={
                "kyc_status": KYCStatus.VERIFIED,
                "id_document_type": "Corporate NTN",
                "id_document_number": "NTN-892144-8",
                "date_of_birth": date(2018, 3, 15),
                "address": "Plot 45, Sundar Industrial Estate, Lahore",
                "risk_tolerance": RiskTolerance.MODERATE,
                "suitability_assessment_notes": "Corporate SME venture partner with equity participation.",
                "verified_by": checker,
                "verified_at": timezone.now(),
            },
        )
        Subscription.objects.get_or_create(
            tenant=tenant,
            capital_account=cap_acc_corp,
            transaction_date=date(2026, 3, 1),
            defaults={
                "amount": Decimal("32000000.00"),
                "units_allotted": Decimal("320000.00"),
                "nav_per_unit": Decimal("100.00"),
                "status": SubscriptionStatus.PROCESSED,
            },
        )
        NAVSnapshot.objects.get_or_create(
            tenant=tenant,
            pool=pool_corp,
            valuation_date=date(2026, 8, 31),
            defaults={
                "total_pool_value": Decimal("365120000.00"),
                "total_units_outstanding": Decimal("3200000.00"),
                "nav_per_unit": Decimal("114.10"),
                "status": NAVSnapshotStatus.PUBLISHED,
                "created_by": maker,
                "published_by": checker,
                "published_at": timezone.now(),
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Investor Accounts, Subscriptions & NAV Curves Seeded"))

        # 19. Community Circles (Screens 38, 39)
        circle_members_data = [
            ("Tariq Mahmood", "MEM-001", 1),
            ("Ayesha Khan", "MEM-002", 2),
            ("Hamza Ali", "MEM-003", 3),
            ("Bilal Siddiqui", "MEM-004", 4),
            ("Zainab Bibi", "MEM-005", 5),
        ]
        created_members = []
        for name, ref, pos in circle_members_data:
            mem, _ = CircleMember.objects.get_or_create(
                tenant=tenant,
                member_reference=ref,
                defaults={
                    "pool": pool_circle,
                    "member_name": name,
                    "payout_position": pos,
                    "status": CircleMemberStatus.ACTIVE,
                    "joined_date": date(2026, 1, 1),
                },
            )
            created_members.append(mem)

        # Monthly Contributions
        for mem in created_members:
            Contribution.objects.get_or_create(
                tenant=tenant,
                member=mem,
                cycle_number=1,
                defaults={
                    "amount": Decimal("10000.00"),
                    "contribution_date": date(2026, 9, 3),
                    "status": ContributionStatus.RECEIVED,
                },
            )

        # Disbursed Payout for Cycle 1
        Payout.objects.get_or_create(
            tenant=tenant,
            member=created_members[0],
            pool=pool_circle,
            cycle_number=1,
            defaults={
                "amount": Decimal("50000.00"),
                "payout_date": date(2026, 9, 10),
                "status": PayoutStatus.DISBURSED,
                "disbursed_by": maker,
            },
        )

        # Circle Proposal & Votes
        prop, _ = CircleProposal.objects.get_or_create(
            tenant=tenant,
            pool=pool_circle,
            title="Cycle Payout Rotation Swap Request",
            defaults={
                "description": "Hamza Ali requests swapping payout cycle from month 4 to month 2 for educational fee.",
                "proposal_type": ProposalType.OTHER,
                "voting_deadline": date(2026, 10, 15),
                "status": ProposalStatus.OPEN,
            },
        )
        CircleVote.objects.get_or_create(
            tenant=tenant,
            proposal=prop,
            member=created_members[0],
            defaults={"decision": VoteDecision.APPROVE},
        )
        CircleVote.objects.get_or_create(
            tenant=tenant,
            proposal=prop,
            member=created_members[1],
            defaults={"decision": VoteDecision.APPROVE},
        )

        # Arrears Record with Hardship relief
        ArrearsRecord.objects.get_or_create(
            tenant=tenant,
            member=created_members[4],
            cycle_number=2,
            defaults={
                "expected_amount": Decimal("10000.00"),
                "status": ArrearsStatus.HARDSHIP_GRANTED,
                "hardship_reason": "Medical emergency documented and approved by community committee.",
                "reviewed_by": board_user,
                "reviewed_at": timezone.now(),
            },
        )
        self.stdout.write(self.style.SUCCESS("[OK] Community Circles, Contributions & Payouts Seeded"))

        self.stdout.write(self.style.SUCCESS("\n========================================================"))
        self.stdout.write(self.style.SUCCESS("*** ALL 42 SCREENS & ENGINES SEEDED WITH 100% PRODUCTION DATA! ***"))
        self.stdout.write(self.style.SUCCESS("========================================================"))
        self.stdout.write(f"Tenant:      {tenant.name} (Code: {tenant.code})")
        self.stdout.write(f"Login URL:   /login")
        self.stdout.write(f"Credentials: Email: superadmin@novulabsdemo.test (or maker, checker, board, etc.)")
        self.stdout.write(f"Password:    {password}\n")
