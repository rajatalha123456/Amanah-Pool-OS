import secrets
import string

from django.core.management.base import BaseCommand

from apps.accounts.models import User, UserRole
from apps.tenants.models import Tenant

TEST_EMAIL = "pool.manager@novulabsdemo.test"


def generate_password(length=14):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "Creates a test user (role=pool_manager) under a tenant, for manual auth testing."

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            code="NOVU-DEMO",
            defaults={"name": "Novu Labs Demo", "data_residency": "PK"},
        )

        password = generate_password()

        user, created = User.objects.get_or_create(
            email=TEST_EMAIL,
            defaults={
                "full_name": "Test Pool Manager",
                "role": UserRole.POOL_MANAGER,
                "tenant": tenant,
            },
        )
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(f"Test user {'created' if created else 'reset'}."))
        self.stdout.write(f"  Tenant:   {tenant.name} ({tenant.code})")
        self.stdout.write(f"  Email:    {TEST_EMAIL}")
        self.stdout.write(f"  Password: {password}")
