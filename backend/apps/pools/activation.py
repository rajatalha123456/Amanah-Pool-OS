"""
BR-001: a pool cannot activate without an approved contract version, rule pack, accounting
mapping and approval matrix (plus the Shariah approval BRD Section 8 requires for any
product, pool or material parameter).
"""

from decimal import Decimal

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


# Which contract types an operating model may run on (BRD section 2).
MODEL_CONTRACTS = {
    "bank_pool": ("mudarabah_unrestricted", "mudarabah_restricted", "wakalah"),
    "investment_pool": ("mudarabah_unrestricted", "mudarabah_restricted", "musharakah", "wakalah"),
    "community_circle": ("qard", "wakalah"),
}


def rule_conflicts(pool, contract, pack, day):
    """
    BRD section 8: law/regulator -> standards -> Board rulings -> contract -> procedure; "conflicts block activation".
    Returns plain-language conflicts between the contract, the pool's economics and the bound rule pack.
    """
    model = pool.product.operating_model
    conflicts = []
    allowed = MODEL_CONTRACTS.get(model)
    if allowed and contract.contract_type not in allowed:
        conflicts.append(f"A {contract.contract_type} contract cannot run a {model}.")
    rules = (pack.rules_config or {}) if pack else {}
    cap = rules.get("mudarib_share_cap_pct")
    if cap is not None and model in ("bank_pool", "investment_pool"):
        for psr in _covers(
            ProfitSharingRatio._base_manager.filter(tenant_id=pool.tenant_id, pool=pool, status=PSRStatus.APPROVED), day
        ):
            if psr.mudarib_share > Decimal(str(cap)):
                conflicts.append(f"The approved manager share {psr.mudarib_share}% exceeds the rule pack cap of {cap}%.")
    from apps.allocation.models import ReservePolicy

    for policy in ReservePolicy._base_manager.filter(tenant_id=pool.tenant_id, pool=pool, is_active=True):
        ceiling = rules.get(f"{policy.reserve_type}_ceiling_pct")
        if ceiling is not None and policy.cap_percentage > Decimal(str(ceiling)):
            conflicts.append(
                f"The {policy.reserve_type.upper()} cap {policy.cap_percentage}% exceeds the rule pack ceiling of {ceiling}%."
            )
    return conflicts


def activation_checks(pool):
    from apps.products.contract_rules import missing_parameters

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

    conflicts = rule_conflicts(pool, contract, pack, day)

    return [
        _check("product_approved", "Product is approved", product.status in (ProductStatus.APPROVED, ProductStatus.ACTIVE),
               f"Product status: {product.status}"),
        _check("contract_approved", "Contract template version is approved", contract.status == ContractTemplateStatus.APPROVED,
               f"{contract.name} v{contract.version}: {contract.status}"),
        _check("contract_parameters", "The contract states the mandatory parameters of its type", not missing_parameters(contract),
               "" if not missing_parameters(contract) else "Missing: " + ", ".join(missing_parameters(contract))),
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
        _check("no_rule_conflicts", "No conflict between the contract, the pool economics and the rule pack", not conflicts,
               "; ".join(conflicts)),
        _check("approval_matrix", "Approval matrix covers the release approval", bool(matrix_rules) or release_action is None,
               "" if matrix_rules or release_action is None else f"No active approval-matrix rule for '{release_action}'."),
    ]
