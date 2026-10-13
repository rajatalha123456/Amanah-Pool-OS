ROOT = "backend/apps/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new):
    assert old in s, old[:90]
    return s.replace(old, new, 1)


# --- the Shariah-review requirement is fixed on the run when it is created (F-09) ---------------
s = rd("allocation/models.py")
s = sub(s, "    @property\n    def shariah_review_required(self) -> bool:", '''    # Fixed when the run is created, so changing the setting later cannot remove a stage from a run in progress.
    # NULL only on runs that predate this field; those keep the live rule.
    shariah_review_enforced = models.BooleanField(null=True, blank=True, default=None)

    @staticmethod
    def shariah_review_rule_for(pool) -> bool:
        return (
            pool.product.operating_model == "bank_pool"
            and settings.ALLOCATION_SHARIAH_REVIEW_REQUIRED_FOR_BANK_POOL
        )

    @property
    def shariah_review_required(self) -> bool:''')
s = sub(s, '''        return (
            self.pool.product.operating_model == "bank_pool"
            and settings.ALLOCATION_SHARIAH_REVIEW_REQUIRED_FOR_BANK_POOL
        )


class AllocationLine''', '''        if self.shariah_review_enforced is not None:
            return self.shariah_review_enforced
        return self.shariah_review_rule_for(self.pool)


class AllocationLine''')
wr("allocation/models.py", s)

s = rd("allocation/views.py")
s = sub(s, "            status=AllocationRunStatus.SIMULATED,\n            created_by=user,\n            **extra,",
        "            status=AllocationRunStatus.SIMULATED,\n            created_by=user,\n            shariah_review_enforced=AllocationRun.shariah_review_rule_for(pool),\n            **extra,")
# exception gate at final release
s = sub(s, '''        assert_may_approve(request.user, run.tenant_id, "allocation_release", run.distributable_amount)
''', '''        assert_may_approve(request.user, run.tenant_id, "allocation_release", run.distributable_amount)
        assert_no_open_serious_exception(run.pool, "an allocation run")
''')
s = sub(s, "from apps.pools.period_lock import assert_period_open\n",
        "from apps.pools.exception_gate import assert_no_open_serious_exception\nfrom apps.pools.period_lock import assert_period_open\n")
wr("allocation/views.py", s)

s = rd("investments/distribution_views.py")
s = sub(s, '''        assert_may_approve(request.user, run.tenant_id, "distribution_approve", run.distributable_amount)
''', '''        assert_may_approve(request.user, run.tenant_id, "distribution_approve", run.distributable_amount)
        assert_no_open_serious_exception(run.pool, "a profit distribution")
''')
s = sub(s, "from apps.pools.period_lock import assert_period_open\n",
        "from apps.pools.exception_gate import assert_no_open_serious_exception\nfrom apps.pools.period_lock import assert_period_open\n")
wr("investments/distribution_views.py", s)

open(ROOT + "pools/exception_gate.py", "w", encoding="utf-8").write('''"""
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
''')
print("ok")
