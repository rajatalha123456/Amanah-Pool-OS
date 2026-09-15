from django.core.management.base import BaseCommand, CommandError

from apps.core.context import set_current_tenant
from apps.pools.models import Pool, PoolStatus
from apps.products.models import Product, ProductStatus
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = (
        "Creates a demo Pool (status=draft) from an approved demo Product. "
        "Run `python manage.py seed_demo_product` first if the product doesn't exist yet."
    )

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            code="NOVU-DEMO",
            defaults={"name": "Novu Labs Demo", "data_residency": "PK"},
        )
        set_current_tenant(tenant)

        try:
            product = Product.objects.get(tenant=tenant, code="PL-2026-014")
        except Product.DoesNotExist as exc:
            set_current_tenant(None)
            raise CommandError(
                "No demo product found. Run `python manage.py seed_demo_product` first."
            ) from exc

        if product.status != ProductStatus.APPROVED:
            self.stdout.write(
                self.style.WARNING(
                    f"Note: demo product status is '{product.status}', not 'approved'. "
                    "The pool's submit-for-approval step will fail until the product is approved."
                )
            )

        pool, created = Pool.objects.get_or_create(
            tenant=tenant,
            code="PL-2026-014-01",
            defaults={
                "name": "Retail Mudarabah Pool 2026 - Series 1",
                "product": product,
                "status": PoolStatus.DRAFT,
                "effective_date": "2026-09-01",
            },
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Pool {'created' if created else 'exists'}: {pool.name} ({pool.code}, {pool.status})"
            )
        )

        set_current_tenant(None)
