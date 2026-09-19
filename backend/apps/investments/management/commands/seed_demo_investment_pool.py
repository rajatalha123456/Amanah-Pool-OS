from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.core.context import set_current_tenant
from apps.investments.models import CapitalAccount, Subscription
from apps.pools.models import Pool, PoolStatus
from apps.products.models import (
    ContractTemplate,
    ContractTemplateStatus,
    ContractType,
    OperatingModel,
    Product,
    ProductStatus,
)
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = (
        "Creates a demo investment_pool Product + Pool, two CapitalAccounts, and "
        "processes one Subscription each (NAV=100.00, amount=50000 -> 500 units)."
    )

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            code="NOVU-DEMO",
            defaults={"name": "Novu Labs Demo", "data_residency": "PK"},
        )
        set_current_tenant(tenant)

        contract_template, _ = ContractTemplate.objects.get_or_create(
            name="Investment Pool Mudarabah Contract",
            version="1.0",
            defaults={
                "tenant": tenant,
                "contract_type": ContractType.MUDARABAH_UNRESTRICTED,
                "clauses": {"unit_basis": "NAV"},
                "status": ContractTemplateStatus.APPROVED,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"ContractTemplate: {contract_template.name} v{contract_template.version} ({contract_template.status})"
            )
        )

        product, _ = Product.objects.get_or_create(
            tenant=tenant,
            code="INV-2026-001",
            defaults={
                "name": "Amanah Investment Fund 2026",
                "operating_model": OperatingModel.INVESTMENT_POOL,
                "contract_template": contract_template,
                "status": ProductStatus.APPROVED,
                "base_currency": "PKR",
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Product: {product.name} ({product.code}, {product.status})"))

        pool, _ = Pool.objects.get_or_create(
            tenant=tenant,
            code="INV-2026-001-01",
            defaults={
                "name": "Amanah Investment Fund 2026 - Series 1",
                "product": product,
                "status": PoolStatus.OPEN,
                "effective_date": "2026-09-01",
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Pool: {pool.name} ({pool.code}, {pool.status})"))

        nav_per_unit = Decimal("100.00")
        amount = Decimal("50000.00")
        units_allotted = amount / nav_per_unit

        for i in range(1, 3):
            account, created = CapitalAccount.objects.get_or_create(
                tenant=tenant,
                investor_reference=f"INV-2026-{i:03d}",
                defaults={
                    "pool": pool,
                    "investor_name": f"Demo Investor {i}",
                },
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"CapitalAccount: {account.investor_reference} - {account.investor_name} "
                    f"({'created' if created else 'exists'})"
                )
            )

            if not account.subscriptions.exists():
                Subscription.objects.create(
                    tenant=tenant,
                    capital_account=account,
                    amount=amount,
                    nav_per_unit=nav_per_unit,
                    units_allotted=units_allotted,
                    transaction_date="2026-09-01",
                    status="processed",
                )
                account.units_held += units_allotted
                account.save(update_fields=["units_held", "updated_at"])
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Subscription processed: {amount} @ NAV {nav_per_unit} -> "
                        f"{units_allotted} units (units_held now {account.units_held})"
                    )
                )
            else:
                self.stdout.write(f"  Already has subscriptions, skipping (units_held={account.units_held})")

        set_current_tenant(None)
