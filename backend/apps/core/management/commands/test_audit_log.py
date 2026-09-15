import uuid

from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.core.audit import log_action
from apps.core.models import AuditLog
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Creates a few AuditLog entries via log_action() and verifies immutability."

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            code="NOVU-DEMO",
            defaults={"name": "Novu Labs Demo", "data_residency": "PK"},
        )
        actor = User.objects.filter(tenant=tenant).first()

        entry1 = log_action(
            tenant=tenant,
            actor=actor,
            action="create",
            model_name="Pool",
            object_id=str(uuid.uuid4()),
            changes={"name": {"before": None, "after": "Retail Mudarabah Pool 2026"}},
            reason="Initial pool creation",
        )
        self.stdout.write(self.style.SUCCESS(f"Created entry 1: {entry1.id} ({entry1.action} {entry1.model_name})"))

        entry2 = log_action(
            tenant=tenant,
            actor=actor,
            action="approve",
            model_name="AllocationRun",
            object_id=str(uuid.uuid4()),
            changes={"status": {"before": "pending", "after": "approved"}},
            reason="Variance within 0.02% tolerance",
        )
        self.stdout.write(self.style.SUCCESS(f"Created entry 2: {entry2.id} ({entry2.action} {entry2.model_name})"))

        entry3 = log_action(
            tenant=None,
            actor=None,
            action="delete",
            model_name="ExceptionCase",
            object_id=str(uuid.uuid4()),
            reason="Automated cleanup job",
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"Created entry 3 (system-level, no tenant/actor): {entry3.id} ({entry3.action} {entry3.model_name})"
            )
        )

        total = AuditLog.objects.count()
        self.stdout.write(f"\nTotal AuditLog entries in DB: {total}")

        self.stdout.write("\nAttempting to update entry 1 (should fail)...")
        entry1.reason = "Trying to sneak in a change"
        try:
            entry1.save()
        except ValueError as exc:
            self.stdout.write(self.style.SUCCESS(f"  Blocked as expected: {exc}"))
        else:
            self.stdout.write(self.style.ERROR("  UNEXPECTED: update succeeded, immutability is broken"))

        self.stdout.write("\nAttempting to delete entry 1 (should fail)...")
        try:
            entry1.delete()
        except ValueError as exc:
            self.stdout.write(self.style.SUCCESS(f"  Blocked as expected: {exc}"))
        else:
            self.stdout.write(self.style.ERROR("  UNEXPECTED: delete succeeded, immutability is broken"))
