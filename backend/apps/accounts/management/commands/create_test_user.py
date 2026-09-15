import secrets
import string

from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User, UserRole
from apps.tenants.models import Tenant


def generate_password(length=14):
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


class Command(BaseCommand):
    help = "Creates a test user under a tenant, for manual auth/permissions testing."

    def add_arguments(self, parser):
        parser.add_argument(
            "--role",
            default=UserRole.POOL_MANAGER,
            choices=[choice.value for choice in UserRole],
            help="Role to assign to the test user (default: pool_manager).",
        )
        parser.add_argument(
            "--email",
            default=None,
            help="Email for the test user (default: derived from the role).",
        )

    def handle(self, *args, **options):
        role = options["role"]
        email = options["email"] or f"{role.replace('_', '.')}@novulabsdemo.test"

        try:
            role_label = UserRole(role).label
        except ValueError as exc:
            raise CommandError(f"Unknown role: {role}") from exc

        tenant, _ = Tenant.objects.get_or_create(
            code="NOVU-DEMO",
            defaults={"name": "Novu Labs Demo", "data_residency": "PK"},
        )

        password = generate_password()

        user, created = User.objects.get_or_create(
            email=email,
            defaults={
                "full_name": f"Test {role_label}",
                "role": role,
                "tenant": tenant,
            },
        )
        user.role = role
        user.set_password(password)
        user.save()

        self.stdout.write(self.style.SUCCESS(f"Test user {'created' if created else 'reset'}."))
        self.stdout.write(f"  Tenant:   {tenant.name} ({tenant.code})")
        self.stdout.write(f"  Role:     {role}")
        self.stdout.write(f"  Email:    {email}")
        self.stdout.write(f"  Password: {password}")
