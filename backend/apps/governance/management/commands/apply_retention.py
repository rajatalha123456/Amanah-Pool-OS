from django.core.management.base import BaseCommand

from apps.core.context import set_current_tenant
from apps.governance.retention import run_retention
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Applies approved retention policies. Dry run unless --apply is given; only read notifications are deleted."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Actually delete eligible notifications.")

    def handle(self, *args, **options):
        for tenant in Tenant.objects.all():
            set_current_tenant(tenant)
            for row in run_retention(tenant, apply=options["apply"]):
                self.stdout.write(f"{tenant.code}: {row}")
        set_current_tenant(None)
