"""
Exception handling time limits (BRD 8). The BRD asks for an SLA but gives no figures, so the days below are DEFAULTS that
the Shariah Board and Risk must confirm; the API says so (`sla_basis`). A rule pack can set its own days in
`rules_config["exception_sla_days"]` (approved through the rule-pack maker-checker), and those then apply. Time is counted in calendar days from the day the
case was raised until it is resolved or dismissed.
"""

from datetime import timedelta

from django.utils import timezone

DEFAULT_SLA_DAYS = {"critical": 1, "high": 3, "medium": 7, "low": 14}
SLA_BASIS = "default, not yet confirmed by the Shariah Board and Risk"
OPEN_STATES = ("open", "investigating")


def _configured(case):
    """`exception_sla_days` of the pool's rule pack (or the tenant's default pack), e.g. {"critical": 1, "high": 2}."""
    from apps.products.models import JurisdictionRulePack

    pack = getattr(case.pool, "rule_pack", None) if case.pool_id else None
    if pack is None:
        pack = JurisdictionRulePack._base_manager.filter(tenant_id=case.tenant_id, is_active=True, is_default=True).first()
    config = (pack.rules_config or {}).get("exception_sla_days") if pack else None
    return config if isinstance(config, dict) else {}


def sla_days(case):
    configured = _configured(case).get(case.severity)
    if isinstance(configured, int) and configured > 0:
        return configured
    return DEFAULT_SLA_DAYS.get(case.severity, DEFAULT_SLA_DAYS["medium"])


def sla_basis_for(case):
    return "rule pack" if isinstance(_configured(case).get(case.severity), int) else SLA_BASIS


def sla_due_on(case):
    return (case.created_at + timedelta(days=sla_days(case))).date()


def sla_breached(case, today=None):
    if case.status not in OPEN_STATES:
        return False
    return (today or timezone.localdate()) > sla_due_on(case)
