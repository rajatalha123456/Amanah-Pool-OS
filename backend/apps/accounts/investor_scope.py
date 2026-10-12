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
    ({"GET"}, API + r"participants/consents/(mine|my-data)/$"),
    ({"POST"}, API + r"participants/consents/" + UUID + r"/withdraw/$"),
    ({"GET"}, API + r"participants/my-tax-support/$"),
    ({"GET", "POST"}, API + r"governance/support-requests/$"),
    ({"GET"}, API + r"governance/support-requests/" + UUID + r"/$"),
    ({"GET"}, API + r"circles/circle-members/(my-circles|my-proposals)/$"),
    ({"POST"}, API + r"circles/circle-members/cast-vote/$"),
    ({"POST"}, API + r"circles/circle-members/accept-rules/$"),
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


# ---- Platform Super Admin (BRD section 3: "cannot view tenant financial data by default") ----------------------
# It provisions tenants, users and configuration only. Everything else is refused before the view runs, so a business
# endpoint that forgets to exclude the role can never expose pools, runs, participants, ledgers or members to it.
ADMIN_ALLOWED = [
    API + r"auth/",
    API + r"health/",
    API + r"notifications/",
    API + r"tenants/",
    API + r"demo-requests/",
    API + r"legal-entities/",
    API + r"products/jurisdiction-rule-packs/",
    API + r"core/audit-log/",
]
_ADMIN_COMPILED = [re.compile("^" + pattern.lstrip("^")) for pattern in ADMIN_ALLOWED]


def admin_may_call(path):
    return any(pattern.match(path) for pattern in _ADMIN_COMPILED)


def assert_admin_scope(user, request):
    if getattr(user, "role", None) != "platform_super_admin":
        return
    if not admin_may_call(request.path):
        raise PermissionDenied("The platform administrator role cannot access tenant business data.")
