"""Test helper: drives an allocation run through the full approval ceremony (UI Catalogue screen 14)."""

from django.urls import reverse


def complete_ceremony(test, run_id):
    """
    Independent check (Finance Checker) -> Shariah review (when the pool requires it) ->
    final release (Authorized Signatory). Returns the first non-200 response, or the release
    response. `test` needs: client, authenticate(), checker, signatory and, for bank pools,
    secretariat.
    """

    base = reverse("allocation-run-detail", args=[run_id])

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
