"""
BR-001: a pool cannot activate without an approved contract version, rule pack, accounting
mapping and approval matrix (plus the Shariah approval BRD Section 8 requires for any
product, pool or material parameter).
"""

from django.db.models import Q

from apps.accounting.chart import unmapped_accounts
from apps.accounts.approval_matrix import active_rules
from apps.allocation.models import PSRStatus, ProfitSharingRatio, WeightageBand, WeightageBandStatus
from apps.products.models import ContractTemplateStatus, ProductStatus
from apps.products.shariah import shariah_decision_for

from .config_snapshot import RELEASE_ACTION_BY_MODEL, bound_rule_pack


def _check(key, label, passed, detail=""):
    return {"key": key, "label": label, "passed": bool(passed), "detail": detail}


def _covers(queryset, day):
    return queryset.filter(effective_from__lte=day).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=day))


def activation_checks(pool):
    product = pool.product
    contract = product.contract_template
    model = product.operating_model
    decision = shariah_decision_for(pool)
    pack = bound_rule_pack(pool)
    day = pool.effective_date

    needs_economics = model in ("bank_pool", "investment_pool")
    psr_ok = (
        _covers(
            ProfitSharingRatio._base_manager.filter(tenant_id=pool.tenant_id, pool=pool, status=PSRStatus.APPROVED), day
        ).exists()
        if needs_economics
        else True
    )
    bands_ok = (
        _covers(
            WeightageBand._base_manager.filter(
                tenant_id=pool.tenant_id, pool=pool, status=WeightageBandStatus.APPROVED
            ),
            day,
        ).exists()
        if model == "bank_pool"
        else True
    )
    missing_accounts = unmapped_accounts(pool.tenant_id, pool)
    release_action = RELEASE_ACTION_BY_MODEL.get(model)
    matrix_rules = active_rules(pool.tenant_id, release_action) if release_action else []

    return [
        _check("product_approved", "Product is approved", product.status in (ProductStatus.APPROVED, ProductStatus.ACTIVE),
               f"Product status: {product.status}"),
        _check("contract_approved", "Contract template version is approved", contract.status == ContractTemplateStatus.APPROVED,
               f"{contract.name} v{contract.version}: {contract.status}"),
        _check("shariah_decision", "Approved Shariah decision in force for the contract", decision is not None,
               decision.decision_code if decision else "No approved, in-force Shariah decision is linked to the contract."),
        _check("rule_pack", "Jurisdiction rule pack bound or a default active pack exists", pack is not None,
               f"{pack.code} v{pack.version}" if pack else "No active rule pack for this tenant."),
        _check("psr_approved", "Approved profit-sharing ratio covers the effective date", psr_ok,
               "" if psr_ok else f"No approved PSR covers {day}."),
        _check("weightages_approved", "Approved weightage bands cover the effective date", bands_ok,
               "" if bands_ok else f"No approved weightage band covers {day}."),
        _check("accounting_mapping", "Accounting mapping is complete for this pool model", not missing_accounts,
               "" if not missing_accounts else "Unmapped accounts: " + ", ".join(missing_accounts)),
        _check("approval_matrix", "Approval matrix covers the release approval", bool(matrix_rules) or release_action is None,
               "" if matrix_rules or release_action is None else f"No active approval-matrix rule for '{release_action}'."),
    ]
