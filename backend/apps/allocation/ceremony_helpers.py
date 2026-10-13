"""Test helper: drives an allocation run through the full approval ceremony (UI Catalogue screen 14)."""

from django.urls import reverse


def sign_run_days(run_id):
    """
    Test setup: the days of the run's period carry a signed daily close (the real workflow is exercised in
    pools/test_daily_close.py). Created directly so the fixtures stay about what they test.
    """
    from django.utils import timezone

    from apps.allocation.models import AllocationRun
    from apps.pools.daily_close import unsigned_balance_days
    from apps.pools.models import DailyClose, DailyCloseStatus

    run = AllocationRun._base_manager.get(pk=run_id)
    for day in unsigned_balance_days(run.pool, run.effective_period_start, run.value_date):
        DailyClose._base_manager.update_or_create(
            tenant=run.tenant, pool=run.pool, value_date=day,
            defaults={"status": DailyCloseStatus.SIGNED, "gates": [], "signed_at": timezone.now()},
        )


def complete_ceremony(test, run_id):
    """
    Independent check (Finance Checker) -> Shariah review (when the pool requires it) ->
    final release (Authorized Signatory). Returns the first non-200 response, or the release
    response. `test` needs: client, authenticate(), checker, signatory and, for bank pools,
    secretariat.
    """

    base = reverse("allocation-run-detail", args=[run_id])
    sign_run_days(run_id)

    test.authenticate(test.checker)
    response = test.client.post(base + "check/")
    if response.status_code != 200:
        return response

    if response.data["shariah_review_required"]:
        test.authenticate(test.secretariat)
        response = test.client.post(base + "shariah-sign-off/", {"note": "Reviewed."}, format="json")
        if response.status_code != 200:
            return response

    test.authenticate(test.signatory)
    return test.client.post(base + "approve/")
