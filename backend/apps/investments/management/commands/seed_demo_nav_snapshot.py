from datetime import date
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.core.context import set_current_tenant
from apps.investments.models import NAVSnapshot, NAVSnapshotStatus
from apps.investments.nav_engine import calculate_nav
from apps.pools.models import Pool
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = (
        "Creates a published NAVSnapshot for the seed_demo_investment_pool pool, "
        "baselined so nav_per_unit comes out to 100.00 given its existing units. "
        "Run `python manage.py seed_demo_investment_pool` first if the pool doesn't exist yet."
    )

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            code="NOVU-DEMO",
            defaults={"name": "Novu Labs Demo", "data_residency": "PK"},
        )
        set_current_tenant(tenant)

        try:
            pool = Pool.objects.get(tenant=tenant, code="INV-2026-001-01")
        except Pool.DoesNotExist as exc:
            set_current_tenant(None)
            raise CommandError(
                "No demo investment pool found. Run `python manage.py seed_demo_investment_pool` first."
            ) from exc

        valuation_date = date(2026, 9, 1)

        existing = NAVSnapshot.objects.filter(
            pool=pool, valuation_date=valuation_date, status=NAVSnapshotStatus.PUBLISHED
        ).first()
        if existing:
            self.stdout.write(
                f"Published NAVSnapshot for {valuation_date} already exists "
                f"(nav_per_unit={existing.nav_per_unit}), skipping."
            )
            set_current_tenant(None)
            return

        # Baseline: keep nav_per_unit at exactly 100.00 given the pool's current
        # units_held, so total_pool_value = total_units_outstanding * 100.
        result = calculate_nav(pool, total_pool_value=Decimal("0"))
        total_units_outstanding = result["total_units_outstanding"]
        total_pool_value = total_units_outstanding * Decimal("100.00")

        result = calculate_nav(pool, total_pool_value)

        snapshot = NAVSnapshot.objects.create(
            tenant=tenant,
            pool=pool,
            valuation_date=valuation_date,
            total_pool_value=total_pool_value,
            total_units_outstanding=result["total_units_outstanding"],
            nav_per_unit=result["nav_per_unit"],
            status=NAVSnapshotStatus.PUBLISHED,
            published_at=timezone.now(),
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"NAVSnapshot published: pool={pool.code}, valuation_date={valuation_date}, "
                f"total_pool_value={snapshot.total_pool_value}, "
                f"total_units_outstanding={snapshot.total_units_outstanding}, "
                f"nav_per_unit={snapshot.nav_per_unit}"
            )
        )

        set_current_tenant(None)
