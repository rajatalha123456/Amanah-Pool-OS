from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError

from apps.core.context import set_current_tenant
from apps.pools.models import BalanceImportBatch, BalanceImportBatchStatus, DailyBalance, DailyBalanceStatus, Pool
from apps.tenants.models import Tenant

# BRD Allocation Simulator example values.
DEMO_RECORDS = (
    ("savings_tier_a", "60000000.00"),
    ("term_tier_b", "25000000.00"),
    ("institutional", "8000000.00"),
)
CONTROL_TOTAL_EXPECTED = Decimal("93000000.00")


class Command(BaseCommand):
    help = (
        "Creates demo DailyBalance records and a balanced BalanceImportBatch for the "
        "demo pool, matching the BRD Allocation Simulator example (60M/25M/8M = 93M). "
        "Run `python manage.py seed_demo_pool` first if the pool doesn't exist yet."
    )

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            code="NOVU-DEMO",
            defaults={"name": "Novu Labs Demo", "data_residency": "PK"},
        )
        set_current_tenant(tenant)

        try:
            pool = Pool.objects.get(tenant=tenant, code="PL-2026-014-01")
        except Pool.DoesNotExist as exc:
            set_current_tenant(None)
            raise CommandError(
                "No demo pool found. Run `python manage.py seed_demo_pool` first."
            ) from exc

        value_date = pool.effective_date
        control_total_actual = Decimal("0.00")
        created_count = 0

        for participant_class, balance_amount in DEMO_RECORDS:
            balance, created = DailyBalance.objects.get_or_create(
                tenant=tenant,
                pool=pool,
                participant_class=participant_class,
                value_date=value_date,
                defaults={
                    "balance_amount": Decimal(balance_amount),
                    "status": DailyBalanceStatus.VALIDATED,
                },
            )
            control_total_actual += balance.balance_amount
            if created:
                created_count += 1
            self.stdout.write(
                self.style.SUCCESS(
                    f"DailyBalance {'created' if created else 'exists'}: "
                    f"{balance.participant_class} = {balance.balance_amount} @ {balance.value_date}"
                )
            )

        batch, batch_created = BalanceImportBatch.objects.get_or_create(
            tenant=tenant,
            pool=pool,
            value_date=value_date,
            defaults={
                "total_records": len(DEMO_RECORDS),
                "matched_records": len(DEMO_RECORDS),
                "exception_count": 0,
                "control_total_expected": CONTROL_TOTAL_EXPECTED,
                "control_total_actual": control_total_actual,
                "status": BalanceImportBatchStatus.BALANCED,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"BalanceImportBatch {'created' if batch_created else 'exists'}: "
                f"{batch.control_total_actual} ({batch.status})"
            )
        )

        set_current_tenant(None)
