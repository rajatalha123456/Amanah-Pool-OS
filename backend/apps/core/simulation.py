"""
Guard for the simulated bank / core-banking integrations (Raast, 1LINK, CBS SFTP).

These produce reference numbers and balances that look real but come from no bank. They are therefore available
in development and demo environments only: production refuses them unless ALLOW_SIMULATED_INTEGRATIONS is set
explicitly (and a real integration should replace them before then).
"""

from django.conf import settings

from .exceptions import ConflictError


def assert_simulation_allowed(what):
    if not getattr(settings, "ALLOW_SIMULATED_INTEGRATIONS", False):
        raise ConflictError(
            f"{what} is a simulation and is disabled in this environment; connect the real integration instead."
        )
