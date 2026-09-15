from django.core.management.base import BaseCommand, CommandError

from apps.allocation.models import PSRStatus, ProfitSharingRatio, WeightageBand, WeightageBandStatus
from apps.core.context import set_current_tenant
from apps.pools.models import Pool
from apps.tenants.models import Tenant

DEMO_WEIGHTAGE_BANDS = (
    ("savings_tier_a", "1.00"),
    ("term_tier_b", "1.20"),
    ("institutional", "1.25"),
)


class Command(BaseCommand):
    help = (
        "Creates demo WeightageBand and ProfitSharingRatio records (BRD example values) "
        "for the demo pool. Run `python manage.py seed_demo_pool` first if it doesn't exist yet."
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

        for participant_class, weightage in DEMO_WEIGHTAGE_BANDS:
            band, created = WeightageBand.objects.get_or_create(
                tenant=tenant,
                pool=pool,
                participant_class=participant_class,
                defaults={
                    "weightage": weightage,
                    "effective_from": pool.effective_date,
                    "status": WeightageBandStatus.APPROVED,
                },
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"WeightageBand {'created' if created else 'exists'}: "
                    f"{band.participant_class} = {band.weightage} ({band.status})"
                )
            )

        psr, created = ProfitSharingRatio.objects.get_or_create(
            tenant=tenant,
            pool=pool,
            effective_from=pool.effective_date,
            defaults={
                "depositor_share": "70.00",
                "mudarib_share": "30.00",
                "status": PSRStatus.APPROVED,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"ProfitSharingRatio {'created' if created else 'exists'}: "
                f"{psr.depositor_share}/{psr.mudarib_share} ({psr.status})"
            )
        )

        set_current_tenant(None)
