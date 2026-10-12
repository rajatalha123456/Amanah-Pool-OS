"""
Deny-by-default for investors / members (BRD Section 3: members see only their own records).

An `investor_member` may only call the self-service endpoints listed here; every other API path is
refused before the view runs, so a staff endpoint that forgets an object-level filter can never leak
or change other people's data to an investor. The listed endpoints scope their querysets to the
caller's own participant record.
"""

import re

from rest_framework.exceptions import PermissionDenied

API = r"^/api/v1/"
UUID = r"[0-9a-fA-F-]{36}"

# (method set, path regex)
ALLOWED = [
    ({"GET"}, API + r"notifications/"),
    ({"POST"}, API + r"notifications/(" + UUID + r"/mark-read|mark-all-read)/$"),
    ({"GET"}, API + r"investments/capital-accounts/"),
    ({"POST"}, API + r"investments/capital-accounts/" + UUID + r"/redeem/$"),
    ({"GET"}, API + r"investments/(subscriptions|redemptions|distribution-runs|nav-snapshots)/"),
    ({"GET"}, API + r"investments/disclosures/"),
    ({"POST"}, API + r"investments/disclosures/" + UUID + r"/acknowledge/$"),
    ({"GET"}, API + r"allocation/allocation-runs/my-statements/$"),
]
_COMPILED = [(methods, re.compile(pattern)) for methods, pattern in ALLOWED]


def investor_may_call(method, path):
    method = method.upper()
    if method in ("HEAD", "OPTIONS"):
        method = "GET"
    return any(method in methods and pattern.match(path) for methods, pattern in _COMPILED)


def assert_investor_scope(user, request):
    if getattr(user, "role", None) != "investor_member":
        return
    if not investor_may_call(request.method, request.path):
        raise PermissionDenied("This area is not available to investors and members.")
