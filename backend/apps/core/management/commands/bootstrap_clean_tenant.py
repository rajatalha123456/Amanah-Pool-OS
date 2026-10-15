"""
A clean start: no demo data, only what a real installation needs to take its first step.

    python manage.py bootstrap_clean_tenant --flush --yes                 # empty the whole database, then start clean
    python manage.py bootstrap_clean_tenant --flush --yes --with-users    # ... and also create one login per role

Without --with-users only the platform administrator exists, and everything else is built through the screens, in
the order the business really works (see docs/FROM_SCRATCH_WORKFLOW.md). With --with-users the same 13 role logins as
the demo are created (still with an EMPTY system behind them), which saves the user-creation step when walking through.

This is for development and training. Like the demo seed it refuses to run outside DEBUG unless --allow-non-debug is
given; --flush deletes EVERY row of EVERY table, so it also needs --yes.
"""

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User, UserRole
from apps.ai_agents.models import AIModelRegistry
from apps.core.context import set_current_tenant
from apps.tenants.models import LegalEntity, Tenant

ROLE_LOGINS = [
    ("pm", "Product Manager", UserRole.PRODUCT_MANAGER),
    ("poolmanager", "Pool Manager", UserRole.POOL_MANAGER),
    ("maker", "Finance Maker", UserRole.FINANCE_MAKER),
    ("checker", "Finance Checker", UserRole.FINANCE_CHECKER),
    ("secretariat", "Shariah Secretariat", UserRole.SHARIAH_SECRETARIAT),
    ("board", "Shariah Board Member A", UserRole.SHARIAH_BOARD),
    ("board2", "Shariah Board Member B", UserRole.SHARIAH_BOARD),
    ("board3", "Shariah Board Member C", UserRole.SHARIAH_BOARD),
    ("risk", "Risk and Compliance", UserRole.RISK_COMPLIANCE),
    ("signatory", "Authorized Signatory", UserRole.AUTHORIZED_SIGNATORY),
    ("auditor", "Auditor", UserRole.AUDITOR),
]


class Command(BaseCommand):
    help = "Starts a clean installation: one tenant and the platform administrator (optionally one login per role)."

    def add_arguments(self, parser):
        parser.add_argument("--tenant-code", default="NOVU-TEST")
        parser.add_argument("--tenant-name", default="Novu Labs Training")
        parser.add_argument("--domain", default="novutest.test", help="e-mail domain of the logins")
        parser.add_argument("--password", default="Amanah@2026!")
        parser.add_argument("--with-users", action="store_true", help="also create one login per role")
        parser.add_argument("--flush", action="store_true", help="first delete EVERY row of EVERY table")
        parser.add_argument("--yes", action="store_true", help="confirm --flush")
        parser.add_argument("--allow-non-debug", action="store_true")

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["allow_non_debug"]:
            raise CommandError("Refusing to run outside DEBUG (this is a development and training tool).")
        if options["flush"]:
            if not options["yes"]:
                raise CommandError("--flush deletes every row of every table. Add --yes to confirm.")
            self.stdout.write(self.style.WARNING("Deleting every row of every table..."))
            call_command("flush", interactive=False, verbosity=0)

        # The AI kill switch is explicit (a feature runs only while its registry row is active). The registry is global
        # and a migration creates it, but a flush removes it: put it back so the copilot and the detectors work.
        for name in ("shariah_copilot", "allocation_anomaly_detector", "reconciliation_copilot"):
            AIModelRegistry.objects.get_or_create(model_name=name, defaults={"version": "1.0", "status": "active"})

        tenant, _ = Tenant.objects.get_or_create(
            code=options["tenant_code"], defaults={"name": options["tenant_name"], "data_residency": "PK"}
        )
        set_current_tenant(tenant)
        LegalEntity.objects.get_or_create(
            tenant=tenant, name=f"{options['tenant_name']} Ltd",
            defaults={"jurisdiction": "Pakistan", "base_currency": "PKR", "timezone": "Asia/Karachi"},
        )

        domain, password = options["domain"], options["password"]
        logins = [("superadmin", "Platform Administrator", UserRole.PLATFORM_SUPER_ADMIN)]
        if options["with_users"]:
            logins += ROLE_LOGINS
        for local, full_name, role in logins:
            user, _ = User.objects.get_or_create(
                email=f"{local}@{domain}", defaults={"tenant": tenant, "full_name": full_name, "role": role}
            )
            user.tenant, user.full_name, user.role, user.is_active = tenant, full_name, role, True
            user.set_password(password)
            user.save()

        self.stdout.write(self.style.SUCCESS(f"Clean tenant ready: {tenant.name} ({tenant.code})"))
        self.stdout.write(f"  superadmin@{domain}   password: {password}")
        if options["with_users"]:
            self.stdout.write("  role logins created: " + ", ".join(f"{l}@{domain}" for l, _, _ in ROLE_LOGINS))
        else:
            self.stdout.write("  Create every other user in Administration > User Administration (the screen shows each password once).")
        set_current_tenant(None)
