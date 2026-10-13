ROOT = "backend/apps/"


def rd(p):
    return open(ROOT + p, encoding="utf-8").read()


def wr(p, s):
    open(ROOT + p, "w", encoding="utf-8").write(s)


def sub(s, old, new):
    assert old in s, old[:80]
    return s.replace(old, new, 1)


p = "participants/seed_ledger.py"
s = rd(p)
s = sub(s, '''    august = draft("2026-08-01", "2026-08-31", "2750000.00", "130000.00")
    call(checker, "post", f"{base}{august}/approve/")''', '''    august = draft("2026-08-01", "2026-08-31", "2750000.00", "130000.00")
    # The full ceremony: independent check, Shariah review, release by the authorized signatory.
    secretariat = User.objects.filter(tenant=tenant, role=UserRole.SHARIAH_SECRETARIAT).order_by("email").first()
    signatory = User.objects.filter(tenant=tenant, role=UserRole.AUTHORIZED_SIGNATORY).order_by("email").first()
    call(checker, "post", f"{base}{august}/check/")
    call(secretariat, "post", f"{base}{august}/shariah-sign-off/", {"note": "Reviewed for the demo data."})
    call(signatory, "post", f"{base}{august}/approve/")''')
wr(p, s)

# tests: a helper that drives a distribution through the ceremony
helper = '''"""Test helper: drives an investment distribution run through the approval ceremony (check, Shariah review, release)."""


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
'''
open(ROOT + "investments/ceremony_helpers.py", "w", encoding="utf-8").write(helper)
print("ok")
