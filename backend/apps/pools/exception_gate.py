"""
Exceptions gate (BRD 8: a potential non-compliance is quarantined and decided before value moves). The daily and period
close already refuse to sign while a high or critical exception is open; the release of a profit run does the same.
"""

from rest_framework.exceptions import ValidationError


def assert_no_open_serious_exception(pool, what):
    from apps.governance.models import ExceptionCase, ExceptionSeverity, ExceptionStatus

    open_serious = ExceptionCase._base_manager.filter(
        tenant_id=pool.tenant_id, pool=pool,
        status__in=[ExceptionStatus.OPEN, ExceptionStatus.INVESTIGATING],
        severity__in=[ExceptionSeverity.HIGH, ExceptionSeverity.CRITICAL],
    ).count()
    if open_serious:
        raise ValidationError(
            f"Cannot release {what} for pool '{pool.code}': {open_serious} high or critical exception(s) are still "
            "open. Decide each one (Shariah Governance > Exception Cases) first."
        )
