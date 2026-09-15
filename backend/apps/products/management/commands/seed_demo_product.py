from django.core.management.base import BaseCommand

from apps.accounts.models import User
from apps.core.context import set_current_tenant
from apps.products.models import (
    ContractTemplate,
    ContractTemplateStatus,
    ContractType,
    OperatingModel,
    Product,
    ProductStatus,
    ShariahDecision,
    ShariahDecisionStatus,
)
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Creates a fully-approved demo Product (with its ContractTemplate and ShariahDecision) under NOVU-DEMO."

    def handle(self, *args, **options):
        tenant, _ = Tenant.objects.get_or_create(
            code="NOVU-DEMO",
            defaults={"name": "Novu Labs Demo", "data_residency": "PK"},
        )
        set_current_tenant(tenant)

        approver = User.objects.filter(tenant=tenant, role="shariah_board").first()

        decision, _ = ShariahDecision.objects.get_or_create(
            decision_code="SBD-2026-044",
            defaults={
                "tenant": tenant,
                "title": "Retail Mudarabah Profit Sharing Ratio",
                "description": "Approved 70/30 depositor/mudarib profit sharing ratio.",
                "status": ShariahDecisionStatus.APPROVED,
                "effective_date": "2026-09-01",
                "approved_by": approver,
            },
        )
        self.stdout.write(self.style.SUCCESS(f"ShariahDecision: {decision.decision_code} ({decision.status})"))

        contract_template, _ = ContractTemplate.objects.get_or_create(
            name="Retail Mudarabah Contract",
            version="1.0",
            defaults={
                "tenant": tenant,
                "contract_type": ContractType.MUDARABAH_UNRESTRICTED,
                "clauses": {"profit_sharing_ratio": "70/30", "calculation_frequency": "daily"},
                "shariah_decision": decision,
                "status": ContractTemplateStatus.APPROVED,
            },
        )
        self.stdout.write(
            self.style.SUCCESS(f"ContractTemplate: {contract_template.name} v{contract_template.version} ({contract_template.status})")
        )

        product, _ = Product.objects.get_or_create(
            tenant=tenant,
            code="PL-2026-014",
            defaults={
                "name": "Retail Mudarabah Pool 2026",
                "operating_model": OperatingModel.BANK_POOL,
                "contract_template": contract_template,
                "status": ProductStatus.APPROVED,
                "base_currency": "PKR",
            },
        )
        self.stdout.write(self.style.SUCCESS(f"Product: {product.name} ({product.code}, {product.status})"))

        set_current_tenant(None)
