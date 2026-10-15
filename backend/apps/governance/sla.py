"""
Exception handling time limits (BRD 8). The BRD asks for an SLA but gives no figures, so the days below are DEFAULTS that
the Shariah Board and Risk must confirm; the API says so (`sla_basis`). Time is counted in calendar days from the day the
case was raised until it is resolved or dismissed.
"""

from datetime import timedelta

from django.utils import timezone

DEFAULT_SLA_DAYS = {"critical": 1, "high": 3, "medium": 7, "low": 14}
SLA_BASIS = "default, not yet confirmed by the Shariah Board and Risk"
OPEN_STATES = ("open", "investigating")


def sla_days(case):
    return DEFAULT_SLA_DAYS.get(case.severity, DEFAULT_SLA_DAYS["medium"])


def sla_due_on(case):
    return (case.created_at + timedelta(days=sla_days(case))).date()


def sla_breached(case, today=None):
    if case.status not in OPEN_STATES:
        return False
    return (today or timezone.localdate()) > sla_due_on(case)
