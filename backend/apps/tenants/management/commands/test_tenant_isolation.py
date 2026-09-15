from django.core.management.base import BaseCommand

from apps.core.context import set_current_tenant
from apps.core.models import TenantIsolationTestRecord
from apps.tenants.models import LegalEntity, Tenant


class Command(BaseCommand):
    help = "Verifies TenantScopedManager isolates records per tenant context."

    def handle(self, *args, **options):
        tenant_a, _ = Tenant.objects.get_or_create(
            code="TENANT-A",
            defaults={"name": "Tenant A", "data_residency": "PK"},
        )
        tenant_b, _ = Tenant.objects.get_or_create(
            code="TENANT-B",
            defaults={"name": "Tenant B", "data_residency": "PK"},
        )

        LegalEntity.objects.get_or_create(
            tenant=tenant_a,
            name="Tenant A Legal Entity",
            defaults={"jurisdiction": "Pakistan"},
        )
        LegalEntity.objects.get_or_create(
            tenant=tenant_b,
            name="Tenant B Legal Entity",
            defaults={"jurisdiction": "Pakistan"},
        )

        TenantIsolationTestRecord.objects.get_or_create(
            tenant=tenant_a, label="Record belonging to Tenant A"
        )
        TenantIsolationTestRecord.objects.get_or_create(
            tenant=tenant_b, label="Record belonging to Tenant B"
        )

        self.stdout.write(self.style.SUCCESS("Setup complete: Tenant A and Tenant B each own one record.\n"))

        set_current_tenant(None)
        self.stdout.write("No tenant context set (TenantScopedManager should return nothing):")
        self.stdout.write(f"  TenantIsolationTestRecord.objects.all() -> {list(TenantIsolationTestRecord.objects.all())}")

        self.stdout.write("\nSimulating a request scoped to Tenant A:")
        set_current_tenant(tenant_a)
        visible = list(TenantIsolationTestRecord.objects.all())
        self.stdout.write(f"  TenantIsolationTestRecord.objects.all() -> {visible}")

        if any(record.tenant_id == tenant_b.id for record in visible):
            self.stdout.write(self.style.ERROR("  LEAK: Tenant B's record is visible while scoped to Tenant A"))
        elif len(visible) == 1 and visible[0].tenant_id == tenant_a.id:
            self.stdout.write(self.style.SUCCESS("  Confirmed: only Tenant A's record is visible"))
        else:
            self.stdout.write(self.style.ERROR("  Unexpected result"))

        self.stdout.write("\nSimulating a request scoped to Tenant B:")
        set_current_tenant(tenant_b)
        visible = list(TenantIsolationTestRecord.objects.all())
        self.stdout.write(f"  TenantIsolationTestRecord.objects.all() -> {visible}")

        if any(record.tenant_id == tenant_a.id for record in visible):
            self.stdout.write(self.style.ERROR("  LEAK: Tenant A's record is visible while scoped to Tenant B"))
        elif len(visible) == 1 and visible[0].tenant_id == tenant_b.id:
            self.stdout.write(self.style.SUCCESS("  Confirmed: only Tenant B's record is visible"))
        else:
            self.stdout.write(self.style.ERROR("  Unexpected result"))

        set_current_tenant(None)

        self.stdout.write(self.style.SUCCESS("\nIsolation check complete."))
