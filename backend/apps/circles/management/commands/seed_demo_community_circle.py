from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.circles.models import CircleMember, CircleMemberStatus, Contribution, ContributionStatus
from apps.circles.rotation import run_draw
from apps.core.context import set_current_tenant
from apps.pools.models import Pool, PoolStatus
from apps.products.models import (
    ContractTemplate,
    ContractTemplateStatus,
    ContractType,
    OperatingModel,
    Product,
    ProductStatus,
)
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = (
        "Creates a demo community_circle Product + Pool, 5 CircleMembers, runs a "
        "draw to assign their payout_position, then records each member's cycle 1 "
        "contribution."
    )

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            code="CIRCLE-DEMO",
            defaults={"name": "Community Circle Demo", "data_residency": "PK"},
        )
        set_current_tenant(tenant)

        contract_template, _ = ContractTemplate.objects.get_or_create(
            name="Community Circle Musharakah Contract",
            version="1.0",
            defaults={
                "tenant": tenant,
                "contract_type": ContractType.MUDARABAH_UNRESTRICTED,
                "clauses": {"rotation_basis": "random_draw"},
                "status": ContractTemplateStatus.APPROVED,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"ContractTemplate: {contract_template.name} v{contract_template.version} "
                f"({contract_template.status})"
            )
        )

        product, _ = Product.objects.get_or_create(
            tenant=tenant,
            code="CIRCLE-2026-001",
            defaults={
                "name": "Amanah Community Circle 2026",
                "operating_model": OperatingModel.COMMUNITY_CIRCLE,
                "contract_template": contract_template,
                "status": ProductStatus.APPROVED,
                "base_currency": "PKR",
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Product: {product.name} ({product.code}, {product.status})"))

        pool, _ = Pool.objects.get_or_create(
            tenant=tenant,
            code="CIRCLE-2026-001-01",
            defaults={
                "name": "Amanah Community Circle 2026 - Group 1",
                "product": product,
                "status": PoolStatus.OPEN,
                "effective_date": "2026-09-01",
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Pool: {pool.name} ({pool.code}, {pool.status})"))

        members = []
        for i in range(1, 6):
            member, created = CircleMember.objects.get_or_create(
                tenant=tenant,
                member_reference=f"CIRCLE-2026-{i:03d}",
                defaults={
                    "pool": pool,
                    "member_name": f"Demo Member {i}",
                    "joined_date": "2026-09-01",
                    "status": CircleMemberStatus.ACTIVE,
                },
            )
            members.append(member)
            self.stdout.write(
                self.style.SUCCESS(
                    f"CircleMember: {member.member_reference} - {member.member_name} "
                    f"({'created' if created else 'exists'}, payout_position={member.payout_position})"
                )
            )

        if any(member.payout_position is None for member in members):
            result = run_draw(pool)
            self.stdout.write(
                self.style.SUCCESS(f"Draw complete (seed={result['seed']}): {result['assignments']}")
            )
            for member in members:
                member.refresh_from_db()
        else:
            self.stdout.write("All members already have a payout_position, skipping draw.")

        assigned = sorted(
            (member.payout_position for member in members if member.payout_position is not None)
        )
        expected = list(range(1, len(members) + 1))
        if assigned == expected:
            self.stdout.write(self.style.SUCCESS(f"Verified positions assigned: {assigned}"))
        else:
            self.stdout.write(self.style.ERROR(f"Unexpected positions after draw: {assigned}"))

        contribution_amount = Decimal("1000.00")
        for member in members:
            if member.contributions.filter(cycle_number=1).exists():
                self.stdout.write(f"  {member.member_reference} already has a cycle 1 contribution, skipping")
                continue

            Contribution.objects.create(
                tenant=tenant,
                member=member,
                amount=contribution_amount,
                contribution_date="2026-09-05",
                cycle_number=1,
                status=ContributionStatus.RECEIVED,
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f"  Contribution recorded for {member.member_reference}: "
                    f"{contribution_amount} (cycle 1, received)"
                )
            )

        set_current_tenant(None)
