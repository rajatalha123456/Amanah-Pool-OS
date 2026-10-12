"""
Investor disclosures and acknowledgement (BRD 6.4: KYC, suitability, disclosures, contract signature).

A pool's disclosure is built from the terms that actually govern it (contract, profit sharing, fees, exit
terms, reserves, Shariah decision) plus the risk warnings the publisher must write. It is sealed with a hash
and never edited. An investor (or staff recording evidence for them) acknowledges a specific version; a
subscription needs an acknowledgement of a disclosure whose terms still match the pool's current terms.
"""

import hashlib
import json
from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.pools.config_snapshot import build_pool_snapshot

from .models import DisclosureAcknowledgement, PoolDisclosure

METHODS = ("in_person", "otp", "e_sign", "portal")


def current_terms(pool):
    """The investor-facing terms, taken only from the records that govern the pool."""
    snap = build_pool_snapshot(pool)
    product = pool.product
    return {
        "product": snap["product"]["name"],
        "operating_model": snap["product"]["operating_model"],
        "contract": {
            "type": snap["contract_template"]["contract_type"],
            "name": snap["contract_template"]["name"],
            "version": snap["contract_template"]["version"],
        },
        "profit_sharing": snap["psr"],
        "reserve_policy": snap["reserve_policy"],
        "redemption": {
            "notice_days": product.redemption_notice_days,
            "gate_pct_per_30_days": f"{Decimal(str(product.redemption_gate_pct)):.2f}",
        },
        "shariah_decision": (
            {"code": snap["shariah_decision"]["decision_code"], "title": snap["shariah_decision"]["title"]}
            if snap["shariah_decision"] else None
        ),
        "jurisdiction_rule_pack": snap["rule_pack"],
        "base_currency": product.base_currency,
    }


def terms_hash(terms):
    return hashlib.sha256(json.dumps(terms, sort_keys=True, default=str).encode()).hexdigest()


def latest_disclosure(pool):
    """The latest disclosure investors can rely on: published (approved) ones only."""
    return PoolDisclosure.objects.filter(pool=pool, status="published").order_by("-version").first()


def _latest_any(pool):
    return PoolDisclosure.objects.filter(pool=pool).order_by("-version").first()


def publish_disclosure(*, pool, user, risk_warnings, fee_statement, summary=""):
    if pool.product.operating_model != "investment_pool":
        raise ValidationError({"pool": ["Disclosures apply to investment pools."]})
    if not risk_warnings.strip() or not fee_statement.strip():
        raise ValidationError("Risk warnings and the fee statement are both required.")
    terms = current_terms(pool)
    if terms["profit_sharing"] is None:
        raise ValidationError("The pool has no approved profit-sharing ratio yet; there is nothing to disclose.")
    previous = _latest_any(pool)
    if previous and previous.terms_hash == terms_hash(terms) and previous.risk_warnings == risk_warnings \
            and previous.fee_statement == fee_statement:
        raise ValidationError("The latest disclosure already states these terms; nothing has changed.")
    # Prepared here, but investors only see and acknowledge it once a different person approves it.
    return PoolDisclosure.objects.create(
        tenant=pool.tenant, pool=pool, version=(previous.version if previous else 0) + 1, summary=summary,
        terms=terms, terms_hash=terms_hash(terms), risk_warnings=risk_warnings, fee_statement=fee_statement,
        published_by=user, status="pending_review",
    )


def approve_disclosure(disclosure, user):
    if disclosure.status != "pending_review":
        raise ValidationError("Only a disclosure that is pending review can be approved.")
    if disclosure.published_by_id and disclosure.published_by_id == user.id:
        raise ValidationError("A different person than the preparer must approve the disclosure.")
    if disclosure.terms_hash != terms_hash(current_terms(disclosure.pool)):
        raise ValidationError("The pool's terms changed after this disclosure was prepared; prepare it again.")
    # The disclosure itself is immutable, so the status moves with a direct update.
    PoolDisclosure.objects.filter(pk=disclosure.pk).update(status="published", approved_by=user, approved_at=timezone.now())
    disclosure.refresh_from_db()
    return disclosure


def acknowledge(*, account, disclosure, method, user, evidence_reference="", risk_acknowledged=False):
    if disclosure.pool_id != account.pool_id:
        raise ValidationError("This disclosure belongs to a different pool.")
    if disclosure.status != "published":
        raise ValidationError("This disclosure has not been approved yet.")
    if method not in METHODS:
        raise ValidationError({"method": [f"Must be one of: {', '.join(METHODS)}."]})
    if not risk_acknowledged:
        raise ValidationError({"risk_acknowledged": ["The risk warnings must be explicitly acknowledged."]})
    if method in ("otp", "e_sign") and not evidence_reference.strip():
        raise ValidationError({"evidence_reference": ["An OTP / e-signature reference is required."]})
    if disclosure.id != getattr(latest_disclosure(account.pool), "id", None):
        raise ValidationError("A newer disclosure has been published; acknowledge the latest version.")
    obj, created = DisclosureAcknowledgement.objects.get_or_create(
        tenant=account.tenant, capital_account=account, disclosure=disclosure,
        defaults={"method": method, "evidence_reference": evidence_reference, "recorded_by": user,
                  "acknowledged_at": timezone.now(), "by_investor": method == "portal"},
    )
    if not created:
        raise ValidationError("This disclosure has already been acknowledged for the account.")
    return obj


def assert_subscription_allowed(account):
    """A subscription needs the account to have acknowledged a disclosure that still matches current terms."""
    pool = account.pool
    disclosure = latest_disclosure(pool)
    if disclosure is None:
        raise ValidationError("No investor disclosure has been published for this pool.")
    if disclosure.terms_hash != terms_hash(current_terms(pool)):
        raise ValidationError(
            "The pool's terms have changed since the last disclosure; publish a new disclosure first."
        )
    if not DisclosureAcknowledgement.objects.filter(capital_account=account, disclosure=disclosure).exists():
        raise ValidationError(
            f"The investor has not acknowledged disclosure v{disclosure.version}; record the acknowledgement first."
        )


def ensure_acknowledged(account, user=None):
    """Convenience for seeding and tests: make sure the account has acknowledged a disclosure matching current terms."""
    pool = account.pool
    terms = current_terms(pool)
    disclosure = latest_disclosure(pool)
    if disclosure is None or disclosure.terms_hash != terms_hash(terms):
        disclosure = PoolDisclosure.objects.create(
            tenant=pool.tenant, pool=pool, version=(disclosure.version if disclosure else 0) + 1, terms=terms,
            terms_hash=terms_hash(terms), risk_warnings="Capital is at risk; returns are not guaranteed.",
            fee_statement="Fees are limited to the profit-sharing terms stated above.", published_by=user,
            status="published", approved_at=timezone.now(),
        )
    if not DisclosureAcknowledgement.objects.filter(capital_account=account, disclosure=disclosure).exists():
        acknowledge(account=account, disclosure=disclosure, method="in_person", user=user, risk_acknowledged=True)
    return disclosure
