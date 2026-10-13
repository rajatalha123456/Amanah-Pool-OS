"""Test helper: drives an investment distribution run through the approval ceremony (check, Shariah review, release)."""


def release_distribution(test, base, *, checker=None, shariah=None, signatory=None):
    """
    `base` is the run's detail URL ending in a slash. `test` needs authenticate(), checker, shariah, signatory.
    Returns the first non-200 response, or the release response.
    """
    test.authenticate(checker or test.checker)
    response = test.client.post(base + "check/")
    if response.status_code != 200:
        return response
    test.authenticate(shariah or test.shariah)
    response = test.client.post(base + "shariah-sign-off/", {"note": "Reviewed."}, format="json")
    if response.status_code != 200:
        return response
    test.authenticate(signatory or test.signatory)
    return test.client.post(base + "approve/")
