from django.core.management.base import BaseCommand

from apps.tenants.models import LegalEntity, Tenant


class Command(BaseCommand):
    help = "Creates a demo Tenant with a LegalEntity to verify the relationship."

    def handle(self, *args, **options):
        tenant, created = Tenant.objects.get_or_create(
            code="NOVU-DEMO",
            defaults={
                "name": "Novu Labs Demo",
                "data_residency": "PK",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f"Tenant {'created' if created else 'exists'}: {tenant.name} ({tenant.code})")
        )

        legal_entity, created = LegalEntity.objects.get_or_create(
            tenant=tenant,
            name="Novu Labs Demo Bank Ltd",
            defaults={
                "jurisdiction": "Pakistan",
                "base_currency": "PKR",
                "timezone": "Asia/Karachi",
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"LegalEntity {'created' if created else 'exists'}: {legal_entity.name}"
            )
        )

        self.stdout.write(self.style.SUCCESS(f"\nTenant: {tenant.name} (id={tenant.id})"))
        self.stdout.write("Legal entities:")
        for entity in tenant.legal_entities.all():
            self.stdout.write(
                f"  - {entity.name} | jurisdiction={entity.jurisdiction} | "
                f"currency={entity.base_currency} | tenant={entity.tenant.name}"
            )
