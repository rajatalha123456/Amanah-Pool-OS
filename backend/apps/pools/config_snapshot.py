"""
Sealed pool configuration (BRD 6.1 step 7: "System seals the configuration version").

The snapshot is built only from the records that actually govern the pool: its contract and
Shariah decision, the approved profit-sharing ratio and weightage bands, reserve policies, the
jurisdiction rule pack, the approval-matrix rules and the account mapping. Nothing is defaulted
or invented - a missing item is recorded as null so the version shows exactly what was in force.
"""

from django.db.models import Q
from django.utils import timezone

from apps.accounting.chart import REQUIRED_BY_MODEL, ChartResolver
from apps.accounts.models import ApprovalMatrixRule
from apps.allocation.models import (
    PSRStatus,
    ProfitSharingRatio,
    ReservePolicy,
    WeightageBand,
    WeightageBandStatus,
)
from apps.products.models import JurisdictionRulePack
from apps.products.shariah import shariah_decision_for

from .version_diff import compute_snapshot_hash

RELEASE_ACTION_BY_MODEL = {
    "bank_pool": "allocation_release",
    "investment_pool": "distribution_approve",
    "community_circle": "payout_approve",
}


def _covering(queryset, day):
    return queryset.filter(effective_from__lte=day).filter(Q(effective_to__isnull=True) | Q(effective_to__gte=day))


def current_psr(pool, day=None):
    day = day or timezone.localdate()
    approved = ProfitSharingRatio._base_manager.filter(tenant_id=pool.tenant_id, pool=pool, status=PSRStatus.APPROVED)
    return _covering(approved, day).order_by("-effective_from").first() or approved.order_by("-effective_from").first()


def current_bands(pool, day=None):
    day = day or timezone.localdate()
    approved = WeightageBand._base_manager.filter(
        tenant_id=pool.tenant_id, pool=pool, status=WeightageBandStatus.APPROVED
    )
    covering = list(_covering(approved, day).order_by("participant_class"))
    return covering or list(approved.order_by("participant_class", "-effective_from"))


def bound_rule_pack(pool):
    """The pack bound to the pool, else the tenant's default active pack."""

    if pool.rule_pack_id and pool.rule_pack.is_active:
        return pool.rule_pack
    return (
        JurisdictionRulePack._base_manager.filter(tenant_id=pool.tenant_id, is_active=True, is_default=True)
        .order_by("-effective_date")
        .first()
    )


def build_pool_snapshot(pool, *, change_rationale="", effective_value_date=None):
    contract = pool.product.contract_template
    decision = contract.shariah_decision
    psr = current_psr(pool)
    bands = current_bands(pool)
    pack = bound_rule_pack(pool)
    model = pool.product.operating_model
    release_action = RELEASE_ACTION_BY_MODEL.get(model)
    chart = ChartResolver(pool.tenant_id, pool)

    snapshot = {
        "identity": {
            "legal_entity": pool.legal_entity.name if pool.legal_entity_id else None,
            "branch": pool.branch,
            "timezone": pool.timezone,
            "calendar": pool.calendar,
        },
        "participation": {
            "minimum_subscription": str(pool.product.minimum_subscription) if pool.product.minimum_subscription is not None else None,
            "subscription_cap": str(pool.product.subscription_cap) if pool.product.subscription_cap is not None else None,
            "minimum_tenure_days": pool.product.minimum_tenure_days,
            "required_kyc_tier": pool.product.required_kyc_tier,
            "max_participants": pool.product.max_participants,
        },
        "product": {
            "id": str(pool.product.id),
            "name": pool.product.name,
            "code": pool.product.code,
            "operating_model": model,
            "status": pool.product.status,
        },
        "contract_template": {
            "id": str(contract.id),
            "name": contract.name,
            "contract_type": contract.contract_type,
            "version": contract.version,
            "clauses": contract.clauses,
            "status": contract.status,
        },
        "psr": (
            {
                "id": str(psr.id),
                "investor_share_pct": float(psr.depositor_share),
                "manager_share_pct": float(psr.mudarib_share),
                "wakalah_fee_pct": float(psr.wakalah_fee_pct),
                "effective_from": psr.effective_from.isoformat(),
            }
            if psr
            else None
        ),
        "weightage_bands": [
            {
                "id": str(band.id),
                "code": band.participant_class,
                "name": band.participant_class,
                "weight": float(band.weightage),
                "effective_from": band.effective_from.isoformat(),
            }
            for band in bands
        ],
        "reserve_policy": {
            policy.reserve_type: {
                "id": str(policy.id),
                "rate_pct": float(policy.rate_percentage),
                "cap_pct": float(policy.cap_percentage),
                "active": policy.is_active,
            }
            for policy in ReservePolicy._base_manager.filter(tenant_id=pool.tenant_id, pool=pool)
        },
        "rule_pack": (
            {"id": str(pack.id), "code": pack.code, "name": pack.name, "version": pack.version} if pack else None
        ),
        "shariah_decision": (
            {
                "id": str(decision.id),
                "decision_code": decision.decision_code,
                "title": decision.title,
                "status": decision.status,
                "in_force": shariah_decision_for(pool) is not None,
                "approved_by": decision.approved_by.full_name if decision.approved_by else None,
            }
            if decision
            else None
        ),
        "approval_matrix": [
            {"action": rule.action, "role": rule.role, "max_amount": str(rule.max_amount) if rule.max_amount is not None else None}
            for rule in ApprovalMatrixRule.objects.filter(
                tenant_id=pool.tenant_id, action=release_action, is_active=True
            ).order_by("role")
        ]
        if release_action
        else [],
        "account_mapping": {
            key: {"name": mapped.gl_name, "code": mapped.gl_code}
            for key in REQUIRED_BY_MODEL.get(model, [])
            if (mapped := chart.mapping(key)) is not None
        },
        "governance": {
            "shariah_resolution_code": decision.decision_code if decision else None,
            "approving_scholar": decision.approved_by.full_name if decision and decision.approved_by else None,
            "effective_value_date": str(effective_value_date or pool.effective_date),
            "change_rationale": change_rationale,
        },
    }
    snapshot["config_hash"] = configuration_hash(snapshot)
    snapshot["snapshot_hash"] = compute_snapshot_hash(snapshot)
    return snapshot


def configuration_hash(snapshot):
    """Hash of the governing configuration only (not the rationale / dates), to detect real changes."""

    body = {k: v for k, v in snapshot.items() if k not in ("governance", "snapshot_hash", "config_hash")}
    return compute_snapshot_hash(body)
