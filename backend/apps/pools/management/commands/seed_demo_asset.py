from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.core.context import set_current_tenant
from apps.pools.models import Asset, AssetAssignment, AssetStatus, AssetType, Pool
from apps.tenants.models import Tenant

DEMO_ASSETS = (
    ("MUR-2026-0091", AssetType.MURABAHAH, "Retail Murabahah financing facility", "5000000.00"),
    ("IJR-2026-0042", AssetType.IJARAH, "Equipment ijarah lease", "3200000.00"),
    ("DMM-2026-0017", AssetType.DIMINISHING_MUSHARAKAH, "Diminishing musharakah property share", "9100000.00"),
)


class Command(BaseCommand):
    help = (
        "Creates 2-3 demo Assets (available) and assigns one to the demo pool. "
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

        assets = []
        for reference_code, asset_type, description, face_value in DEMO_ASSETS:
            asset, created = Asset.objects.get_or_create(
                tenant=tenant,
                reference_code=reference_code,
                defaults={
                    "asset_type": asset_type,
                    "description": description,
                    "face_value": face_value,
                    "status": AssetStatus.AVAILABLE,
                },
            )
            assets.append(asset)
            self.stdout.write(
                self.style.SUCCESS(
                    f"Asset {'created' if created else 'exists'}: {asset.reference_code} ({asset.status})"
                )
            )

        first_asset = assets[0]
        if not first_asset.assignments.filter(unassigned_date__isnull=True).exists():
            AssetAssignment.objects.create(
                tenant=tenant,
                asset=first_asset,
                pool=pool,
                assigned_date=timezone.localdate(),
            )
            first_asset.status = AssetStatus.ASSIGNED
            first_asset.save(update_fields=["status"])
            self.stdout.write(
                self.style.SUCCESS(f"Assigned {first_asset.reference_code} to pool {pool.code}")
            )
        else:
            self.stdout.write(
                self.style.WARNING(f"{first_asset.reference_code} is already assigned; skipping.")
            )

        set_current_tenant(None)
